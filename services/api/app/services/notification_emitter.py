"""
Fire-and-forget notification helpers called from route handlers
where both TradingService and NotificationService are available.
All methods swallow exceptions to never break the main request path.
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.schemas.market import MarketHoldersResponse
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def _collect_holder_profile_ids(holders: MarketHoldersResponse) -> list[UUID]:
    seen: set[UUID] = set()
    ids: list[UUID] = []
    for group in holders.groups:
        for h in group.holders:
            pid = h.profile_id if isinstance(h.profile_id, UUID) else UUID(str(h.profile_id))
            if pid not in seen:
                seen.add(pid)
                ids.append(pid)
    return ids


async def emit_market_status_change(
    notification_service: NotificationService,
    holders: MarketHoldersResponse | None,
    slug: str,
    new_status: str,
) -> None:
    kind_map = {
        "open": "market_opened",
        "settled": "market_settled",
        "cancelled": "market_cancelled",
        "disputed": "market_disputed",
    }
    kind = kind_map.get(new_status)
    if not kind or not holders:
        return

    title_map = {
        "market_opened": f"Market '{slug}' is now open for trading",
        "market_settled": f"Market '{slug}' has been settled",
        "market_cancelled": f"Market '{slug}' was cancelled",
        "market_disputed": f"Market '{slug}' is under dispute",
    }
    try:
        profile_ids = await _collect_holder_profile_ids(holders)
        if profile_ids:
            await notification_service.emit_to_many(
                profile_ids=profile_ids,
                kind=kind,
                title=title_map.get(kind, f"Market '{slug}' status changed"),
                market_slug=slug,
            )
    except Exception:
        logger.debug("Failed to emit market status notification for %s", slug, exc_info=True)


async def emit_settlement_finalized(
    notification_service: NotificationService,
    holders: MarketHoldersResponse | None,
    slug: str,
) -> None:
    if not holders:
        return
    try:
        profile_ids = await _collect_holder_profile_ids(holders)
        if profile_ids:
            await notification_service.emit_to_many(
                profile_ids=profile_ids,
                kind="settlement_finalized",
                title=f"Settlement finalized for '{slug}'",
                body="Market resolution is complete. Check your portfolio for payouts.",
                market_slug=slug,
            )
    except Exception:
        logger.debug("Failed to emit settlement notification for %s", slug, exc_info=True)
