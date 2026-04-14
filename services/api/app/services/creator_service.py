from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, text

from app.core.config import settings
from app.schemas.creator import (
    CreatorLeaderboardEntry,
    CreatorLeaderboardResponse,
    CreatorRewardTierResponse,
    CreatorStatsResponse,
    CreatorTiersResponse,
)

logger = logging.getLogger(__name__)

_FALLBACK_TIERS: list[dict[str, Any]] = [
    {"tier_code": "starter", "tier_label": "Starter", "min_volume_usd": "0", "fee_share_bps": 0, "badge_color": "#6b7280", "sort_order": 0},
    {"tier_code": "bronze", "tier_label": "Bronze", "min_volume_usd": "1000", "fee_share_bps": 1000, "badge_color": "#cd7f32", "sort_order": 1},
    {"tier_code": "silver", "tier_label": "Silver", "min_volume_usd": "10000", "fee_share_bps": 1500, "badge_color": "#c0c0c0", "sort_order": 2},
    {"tier_code": "gold", "tier_label": "Gold", "min_volume_usd": "50000", "fee_share_bps": 2500, "badge_color": "#f7b955", "sort_order": 3},
    {"tier_code": "platinum", "tier_label": "Platinum", "min_volume_usd": "250000", "fee_share_bps": 3500, "badge_color": "#e5e4e2", "sort_order": 4},
    {"tier_code": "diamond", "tier_label": "Diamond", "min_volume_usd": "1000000", "fee_share_bps": 5000, "badge_color": "#b9f2ff", "sort_order": 5},
]


def _tier_from_dict(d: dict[str, Any]) -> CreatorRewardTierResponse:
    return CreatorRewardTierResponse(
        tier_code=d["tier_code"],
        tier_label=d["tier_label"],
        min_volume_usd=str(d["min_volume_usd"]),
        fee_share_bps=int(d["fee_share_bps"]),
        badge_color=d["badge_color"],
        sort_order=int(d["sort_order"]),
    )


def _resolve_tier(tiers: list[dict[str, Any]], volume: Decimal) -> tuple[dict[str, Any], dict[str, Any] | None]:
    sorted_tiers = sorted(tiers, key=lambda t: Decimal(str(t["min_volume_usd"])))
    current = sorted_tiers[0]
    next_tier = None
    for i, tier in enumerate(sorted_tiers):
        if volume >= Decimal(str(tier["min_volume_usd"])):
            current = tier
            next_tier = sorted_tiers[i + 1] if i + 1 < len(sorted_tiers) else None
    return current, next_tier


class CreatorService:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def get_tiers(self) -> CreatorTiersResponse:
        tiers = await self._load_tiers()
        return CreatorTiersResponse(tiers=[_tier_from_dict(t) for t in tiers])

    async def get_creator_stats(self, profile_id: UUID, username: str | None, display_name: str | None) -> CreatorStatsResponse:
        tiers = await self._load_tiers()
        stats = await self._load_creator_stats(profile_id)

        volume = Decimal(str(stats.get("total_volume", 0)))
        current, next_tier = _resolve_tier(tiers, volume)

        volume_to_next = Decimal("0")
        progress_pct = 100.0
        if next_tier:
            next_min = Decimal(str(next_tier["min_volume_usd"]))
            current_min = Decimal(str(current["min_volume_usd"]))
            volume_to_next = max(next_min - volume, Decimal("0"))
            span = next_min - current_min
            if span > 0:
                progress_pct = float(min((volume - current_min) / span * 100, Decimal("100")))
            else:
                progress_pct = 100.0

        return CreatorStatsResponse(
            profile_id=str(profile_id),
            username=username,
            display_name=display_name,
            markets_created=int(stats.get("markets_created", 0)),
            markets_open=int(stats.get("markets_open", 0)),
            markets_settled=int(stats.get("markets_settled", 0)),
            total_volume=str(volume),
            total_trades=int(stats.get("total_trades", 0)),
            current_tier=_tier_from_dict(current),
            next_tier=_tier_from_dict(next_tier) if next_tier else None,
            volume_to_next_tier=str(volume_to_next),
            progress_pct=progress_pct,
        )

    async def get_leaderboard(self, limit: int = 20) -> CreatorLeaderboardResponse:
        tiers = await self._load_tiers()

        if settings.repository_backend != "postgres" or not self._session_factory:
            return CreatorLeaderboardResponse()

        async with self._session_factory() as session:
            result = await session.execute(text("""
                select
                    cs.profile_id,
                    p.username,
                    p.display_name,
                    cs.markets_created,
                    cs.total_volume,
                    cs.total_trades
                from public.creator_stats_v cs
                join public.profiles p on p.id = cs.profile_id
                where cs.total_volume > 0
                order by cs.total_volume desc
                limit :lim
            """), {"lim": limit})
            rows = result.fetchall()

        entries: list[CreatorLeaderboardEntry] = []
        for row in rows:
            volume = Decimal(str(row.total_volume))
            current, _ = _resolve_tier(tiers, volume)
            entries.append(CreatorLeaderboardEntry(
                profile_id=str(row.profile_id),
                username=row.username,
                display_name=row.display_name,
                markets_created=int(row.markets_created),
                total_volume=str(row.total_volume),
                total_trades=int(row.total_trades),
                tier_code=current["tier_code"],
                tier_label=current["tier_label"],
                badge_color=current["badge_color"],
            ))

        return CreatorLeaderboardResponse(entries=entries)

    async def _load_tiers(self) -> list[dict[str, Any]]:
        if settings.repository_backend != "postgres" or not self._session_factory:
            return _FALLBACK_TIERS

        try:
            async with self._session_factory() as session:
                result = await session.execute(text(
                    "select tier_code, tier_label, min_volume_usd, fee_share_bps, badge_color, sort_order "
                    "from public.creator_reward_tiers order by sort_order"
                ))
                rows = result.fetchall()
                if rows:
                    return [
                        {
                            "tier_code": r.tier_code,
                            "tier_label": r.tier_label,
                            "min_volume_usd": str(r.min_volume_usd),
                            "fee_share_bps": r.fee_share_bps,
                            "badge_color": r.badge_color,
                            "sort_order": r.sort_order,
                        }
                        for r in rows
                    ]
        except Exception:
            logger.debug("Failed to load tiers from DB, using fallback", exc_info=True)

        return _FALLBACK_TIERS

    async def _load_creator_stats(self, profile_id: UUID) -> dict[str, Any]:
        if settings.repository_backend != "postgres" or not self._session_factory:
            return {}

        try:
            async with self._session_factory() as session:
                result = await session.execute(text("""
                    select
                        markets_created,
                        markets_open,
                        markets_settled,
                        total_volume,
                        total_trades
                    from public.creator_stats_v
                    where profile_id = :pid
                """), {"pid": profile_id})
                row = result.fetchone()
                if row:
                    return {
                        "markets_created": row.markets_created,
                        "markets_open": row.markets_open,
                        "markets_settled": row.markets_settled,
                        "total_volume": row.total_volume,
                        "total_trades": row.total_trades,
                    }
        except Exception:
            logger.debug("Failed to load creator stats for %s", profile_id, exc_info=True)

        return {}
