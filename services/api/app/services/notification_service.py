from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.config import settings
from app.db.tables import notifications
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)

logger = logging.getLogger(__name__)


def _row_to_response(row: Any) -> NotificationResponse:
    return NotificationResponse(
        id=str(row.id),
        profile_id=str(row.profile_id),
        kind=row.kind,
        title=row.title,
        body=row.body,
        market_slug=row.market_slug,
        market_id=str(row.market_id) if row.market_id else None,
        order_id=str(row.order_id) if row.order_id else None,
        payload=row.payload or {},
        is_read=row.is_read,
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


class NotificationService:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def emit(
        self,
        *,
        profile_id: UUID,
        kind: str,
        title: str,
        body: str | None = None,
        market_slug: str | None = None,
        market_id: UUID | None = None,
        order_id: UUID | None = None,
        payload: dict | None = None,
    ) -> None:
        if settings.repository_backend != "postgres":
            logger.debug("Notification skipped (non-postgres backend): %s for %s", kind, profile_id)
            return
        now = datetime.now(UTC)
        try:
            async with self._session_factory() as session:
                await session.execute(
                    notifications.insert().values(
                        profile_id=profile_id,
                        kind=kind,
                        title=title,
                        body=body,
                        market_slug=market_slug,
                        market_id=market_id,
                        order_id=order_id,
                        payload=payload or {},
                        is_read=False,
                        created_at=now,
                    )
                )
                await session.commit()
        except Exception:
            logger.exception("Failed to emit notification kind=%s for profile_id=%s", kind, profile_id)

    async def emit_to_many(
        self,
        *,
        profile_ids: list[UUID],
        kind: str,
        title: str,
        body: str | None = None,
        market_slug: str | None = None,
        market_id: UUID | None = None,
        payload: dict | None = None,
    ) -> None:
        if settings.repository_backend != "postgres":
            return
        if not profile_ids:
            return
        now = datetime.now(UTC)
        rows = [
            {
                "profile_id": pid,
                "kind": kind,
                "title": title,
                "body": body,
                "market_slug": market_slug,
                "market_id": market_id,
                "payload": payload or {},
                "is_read": False,
                "created_at": now,
            }
            for pid in profile_ids
        ]
        try:
            async with self._session_factory() as session:
                await session.execute(notifications.insert(), rows)
                await session.commit()
        except Exception:
            logger.exception("Failed to emit batch notifications kind=%s to %d profiles", kind, len(profile_ids))

    async def list_notifications(
        self,
        profile_id: UUID,
        *,
        limit: int = 40,
        offset: int = 0,
        unread_only: bool = False,
    ) -> NotificationListResponse:
        if settings.repository_backend != "postgres":
            return NotificationListResponse()

        async with self._session_factory() as session:
            base = select(notifications).where(notifications.c.profile_id == profile_id)
            if unread_only:
                base = base.where(notifications.c.is_read == False)  # noqa: E712

            total_stmt = select(func.count()).select_from(base.subquery())
            total_count = (await session.execute(total_stmt)).scalar() or 0

            unread_stmt = select(func.count()).select_from(
                select(notifications)
                .where(notifications.c.profile_id == profile_id)
                .where(notifications.c.is_read == False)  # noqa: E712
                .subquery()
            )
            unread_count = (await session.execute(unread_stmt)).scalar() or 0

            items_stmt = base.order_by(notifications.c.created_at.desc()).limit(limit).offset(offset)
            rows = (await session.execute(items_stmt)).fetchall()

            return NotificationListResponse(
                items=[_row_to_response(r) for r in rows],
                total_count=total_count,
                unread_count=unread_count,
            )

    async def get_unread_count(self, profile_id: UUID) -> NotificationUnreadCountResponse:
        if settings.repository_backend != "postgres":
            return NotificationUnreadCountResponse()

        async with self._session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(notifications)
                .where(notifications.c.profile_id == profile_id)
                .where(notifications.c.is_read == False)  # noqa: E712
            )
            count = (await session.execute(stmt)).scalar() or 0
            return NotificationUnreadCountResponse(unread_count=count)

    async def mark_read(
        self,
        profile_id: UUID,
        *,
        notification_ids: list[str] | None = None,
        mark_all: bool = False,
    ) -> int:
        if settings.repository_backend != "postgres":
            return 0

        async with self._session_factory() as session:
            stmt = (
                update(notifications)
                .where(notifications.c.profile_id == profile_id)
                .where(notifications.c.is_read == False)  # noqa: E712
            )
            if not mark_all and notification_ids:
                parsed_ids = []
                for nid in notification_ids:
                    try:
                        parsed_ids.append(UUID(nid))
                    except ValueError:
                        continue
                if not parsed_ids:
                    return 0
                stmt = stmt.where(notifications.c.id.in_(parsed_ids))
            elif not mark_all:
                return 0

            stmt = stmt.values(is_read=True)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount  # type: ignore[return-value]
