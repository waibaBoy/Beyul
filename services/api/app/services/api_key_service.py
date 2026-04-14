"""API key management for programmatic trading.

Keys are generated as sk_live_<random> format.
Only the hash is stored; the plaintext key is shown once at creation.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import api_keys

logger = logging.getLogger(__name__)

KEY_PREFIX_LENGTH = 8
VALID_PERMISSIONS = {"read", "trade", "admin"}


def _generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, key_prefix, key_hash)."""
    raw = secrets.token_urlsafe(32)
    full_key = f"sk_live_{raw}"
    prefix = full_key[:KEY_PREFIX_LENGTH + 8]  # "sk_live_" + 8 chars
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ApiKeyService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create_key(
        self,
        profile_id: UUID,
        label: str,
        permissions: list[str] | None = None,
    ) -> dict:
        perms = permissions or ["read", "trade"]
        for p in perms:
            if p not in VALID_PERMISSIONS:
                from app.core.exceptions import ConflictError
                raise ConflictError(f"Invalid permission: {p}")

        full_key, prefix, key_hash = _generate_api_key()

        if not self._session_factory:
            return {
                "id": str(UUID(int=0)),
                "label": label,
                "key": full_key,
                "key_prefix": prefix,
                "permissions": perms,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        async with self._session_factory() as session:
            result = await session.execute(
                insert(api_keys)
                .values(
                    profile_id=profile_id,
                    label=label,
                    key_hash=key_hash,
                    key_prefix=prefix,
                    permissions=perms,
                    is_active=True,
                )
                .returning(api_keys.c.id, api_keys.c.created_at)
            )
            row = result.one()
            await session.commit()
            return {
                "id": str(row.id),
                "label": label,
                "key": full_key,
                "key_prefix": prefix,
                "permissions": perms,
                "is_active": True,
                "created_at": row.created_at.isoformat(),
            }

    async def list_keys(self, profile_id: UUID) -> list[dict]:
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    api_keys.c.id,
                    api_keys.c.label,
                    api_keys.c.key_prefix,
                    api_keys.c.permissions,
                    api_keys.c.is_active,
                    api_keys.c.last_used_at,
                    api_keys.c.created_at,
                )
                .where(api_keys.c.profile_id == profile_id)
                .order_by(api_keys.c.created_at.desc())
            )
            return [
                {
                    "id": str(row.id),
                    "label": row.label,
                    "key_prefix": row.key_prefix,
                    "permissions": row.permissions,
                    "is_active": row.is_active,
                    "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
                    "created_at": row.created_at.isoformat(),
                }
                for row in result.fetchall()
            ]

    async def revoke_key(self, profile_id: UUID, key_id: UUID) -> bool:
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            result = await session.execute(
                update(api_keys)
                .where(api_keys.c.id == key_id, api_keys.c.profile_id == profile_id)
                .values(is_active=False, revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()
            return result.rowcount > 0

    async def validate_key(self, raw_key: str) -> dict | None:
        """Validate an API key and return the profile_id + permissions."""
        if not self._session_factory:
            return None

        key_hash = _hash_key(raw_key)
        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    api_keys.c.profile_id,
                    api_keys.c.permissions,
                    api_keys.c.is_active,
                    api_keys.c.expires_at,
                )
                .where(api_keys.c.key_hash == key_hash)
            )
            row = result.one_or_none()
            if not row:
                return None
            if not row.is_active:
                return None
            if row.expires_at and row.expires_at < datetime.now(timezone.utc):
                return None

            await session.execute(
                update(api_keys)
                .where(api_keys.c.key_hash == key_hash)
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await session.commit()

            return {
                "profile_id": row.profile_id,
                "permissions": row.permissions,
            }
