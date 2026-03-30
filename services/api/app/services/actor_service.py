from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select

from app.core.actor import CurrentActor
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.tables import profiles


@dataclass
class ActorProvisioningInput:
    user_id: UUID
    username: str
    display_name: str
    is_admin: bool


class ActorService:
    async def resolve_dev_actor(
        self,
        user_id: UUID | None,
        username: str | None,
        display_name: str | None,
        is_admin: bool | None,
    ) -> CurrentActor:
        if settings.repository_backend == "memory":
            return CurrentActor(
                id=user_id or UUID("00000000-0000-0000-0000-000000000001"),
                username=username or settings.dev_auth_username,
                display_name=display_name or settings.dev_auth_display_name,
                is_admin=settings.dev_auth_is_admin if is_admin is None else is_admin,
            )

        actor_input = ActorProvisioningInput(
            user_id=self._resolve_actor_id(user_id),
            username=username or settings.dev_auth_username,
            display_name=display_name or settings.dev_auth_display_name,
            is_admin=settings.dev_auth_is_admin if is_admin is None else is_admin,
        )
        return await self._provision_actor(actor_input)

    async def resolve_authenticated_actor(self, claims: dict) -> CurrentActor:
        subject = claims.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase token is missing the subject claim.",
            )

        try:
            user_id = UUID(subject)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase token subject is not a valid UUID.",
            ) from exc

        user_metadata = claims.get("user_metadata") or {}
        email = claims.get("email")
        phone = claims.get("phone")

        base_username = (
            user_metadata.get("username")
            or user_metadata.get("user_name")
            or user_metadata.get("preferred_username")
            or self._username_from_email(email)
            or self._username_from_phone(phone)
            or f"user_{str(user_id).split('-')[0]}"
        )
        base_display_name = (
            user_metadata.get("display_name")
            or user_metadata.get("full_name")
            or base_username
        )

        actor_input = ActorProvisioningInput(
            user_id=user_id,
            username=base_username,
            display_name=base_display_name,
            is_admin=self._is_admin_user(claims),
        )
        return await self._provision_actor(actor_input)

    async def _provision_actor(self, actor_input: ActorProvisioningInput) -> CurrentActor:
        username_candidates = self._candidate_usernames(actor_input)

        try:
            async with SessionLocal() as session:
                existing_result = await session.execute(
                    select(
                        profiles.c.id,
                        profiles.c.username,
                        profiles.c.display_name,
                        profiles.c.is_admin,
                    )
                    .where(profiles.c.id == actor_input.user_id)
                )
                existing_row = existing_result.first()
                if existing_row is not None:
                    existing = existing_row._mapping
                    actor_input = ActorProvisioningInput(
                        user_id=actor_input.user_id,
                        username=existing["username"] or actor_input.username,
                        display_name=existing["display_name"] or actor_input.display_name,
                        is_admin=actor_input.is_admin,
                    )
                    username_candidates = [actor_input.username]

                last_conflict_error: IntegrityError | None = None
                for candidate in username_candidates:
                    try:
                        result = await session.execute(
                            pg_insert(profiles)
                            .values(
                                id=actor_input.user_id,
                                username=candidate,
                                display_name=actor_input.display_name,
                                is_admin=actor_input.is_admin,
                            )
                            .on_conflict_do_update(
                                index_elements=[profiles.c.id],
                                set_={
                                    "username": candidate,
                                    "display_name": actor_input.display_name,
                                    "is_admin": actor_input.is_admin,
                                },
                            )
                            .returning(
                                profiles.c.id,
                                profiles.c.username,
                                profiles.c.display_name,
                                profiles.c.is_admin,
                            )
                        )
                        row = result.first()._mapping
                        await session.commit()
                        return CurrentActor(
                            id=row["id"],
                            username=row["username"],
                            display_name=row["display_name"],
                            is_admin=row["is_admin"],
                        )
                    except IntegrityError as exc:
                        await session.rollback()
                        last_conflict_error = exc
                        continue
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Could not provision the current actor profile. "
                    "Check that the username is unique and the Supabase auth user exists."
                ),
            ) from exc
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database error while provisioning current actor: {exc.__class__.__name__}",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Could not provision the current actor profile. "
                "A unique username could not be assigned."
            ),
        )

    def _resolve_actor_id(self, user_id: UUID | None) -> UUID:
        if user_id is not None:
            return user_id
        if settings.dev_auth_user_id:
            try:
                return UUID(settings.dev_auth_user_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="DEV_AUTH_USER_ID is not a valid UUID.",
                ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A real Supabase auth user UUID is required in postgres mode. "
                "Set DEV_AUTH_USER_ID in .env or send X-Satta-User-Id."
            ),
        )

    def _candidate_usernames(self, actor_input: ActorProvisioningInput) -> list[str]:
        normalized = self._normalize_username(actor_input.username)
        suffix = str(actor_input.user_id).split("-")[0]
        return [
            normalized,
            f"{normalized}_{suffix}",
            f"user_{suffix}",
        ]

    def _normalize_username(self, username: str) -> str:
        cleaned = "".join(char for char in username if char.isalnum() or char in {"_", "-"}).strip("_-")
        return cleaned or "user"

    def _username_from_email(self, email: str | None) -> str | None:
        if not email or "@" not in email:
            return None
        return email.split("@", 1)[0]

    def _username_from_phone(self, phone: str | None) -> str | None:
        if not phone:
            return None
        digits_only = "".join(char for char in phone if char.isdigit())
        return f"user_{digits_only[-8:]}" if digits_only else None

    def _is_admin_user(self, claims: dict) -> bool:
        if settings.admin_email:
            email = claims.get("email")
            if email and email.lower() == settings.admin_email.lower():
                return True
        app_metadata = claims.get("app_metadata") or {}
        return bool(app_metadata.get("is_admin"))
