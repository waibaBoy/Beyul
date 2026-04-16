"""Social features: follow/unfollow, trading profiles, activity feed."""

import logging
from uuid import UUID

from sqlalchemy import select, insert, delete, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import follows, profiles, trades, positions

logger = logging.getLogger(__name__)


class TradingProfile:
    __slots__ = (
        "profile_id", "username", "display_name",
        "total_positions", "realized_pnl", "total_trades", "total_volume",
        "follower_count", "following_count", "is_following",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for slot in self.__slots__:
            if not hasattr(self, slot):
                setattr(self, slot, None)

    def to_dict(self) -> dict:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class SocialService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def get_trading_profile(
        self, username: str, viewer_id: UUID | None = None
    ) -> TradingProfile:
        if not self._session_factory:
            return TradingProfile(username=username)

        async with self._session_factory() as session:
            session: AsyncSession

            profile_row = (
                await session.execute(
                    select(profiles.c.id, profiles.c.username, profiles.c.display_name)
                    .where(profiles.c.username == username)
                )
            ).one_or_none()
            if not profile_row:
                from app.core.exceptions import NotFoundError
                raise NotFoundError("Profile not found")

            pid = profile_row.id

            # Trading stats
            pos_stats = (
                await session.execute(
                    select(
                        func.count().label("total_positions"),
                        func.coalesce(func.sum(positions.c.realized_pnl), 0).label("realized_pnl"),
                    ).where(positions.c.profile_id == pid)
                )
            ).one()

            trade_stats = (
                await session.execute(
                    select(
                        func.count().label("total_trades"),
                        func.coalesce(func.sum(trades.c.gross_notional), 0).label("total_volume"),
                    ).where(
                        (trades.c.taker_profile_id == pid) | (trades.c.maker_profile_id == pid)
                    )
                )
            ).one()

            follower_count = (
                await session.execute(
                    select(func.count()).where(follows.c.following_id == pid)
                )
            ).scalar() or 0

            following_count = (
                await session.execute(
                    select(func.count()).where(follows.c.follower_id == pid)
                )
            ).scalar() or 0

            is_following = False
            if viewer_id and viewer_id != pid:
                existing = (
                    await session.execute(
                        select(follows.c.id).where(
                            and_(follows.c.follower_id == viewer_id, follows.c.following_id == pid)
                        )
                    )
                ).scalar_one_or_none()
                is_following = existing is not None

            return TradingProfile(
                profile_id=pid,
                username=profile_row.username,
                display_name=profile_row.display_name,
                total_positions=int(pos_stats.total_positions),
                realized_pnl=str(pos_stats.realized_pnl),
                total_trades=int(trade_stats.total_trades),
                total_volume=str(trade_stats.total_volume),
                follower_count=int(follower_count),
                following_count=int(following_count),
                is_following=is_following,
            )

    async def follow(self, follower_id: UUID, target_username: str) -> bool:
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            session: AsyncSession
            target = (
                await session.execute(
                    select(profiles.c.id).where(profiles.c.username == target_username)
                )
            ).scalar_one_or_none()
            if not target:
                from app.core.exceptions import NotFoundError
                raise NotFoundError("User not found")
            if target == follower_id:
                from app.core.exceptions import ConflictError
                raise ConflictError("Cannot follow yourself")

            await session.execute(
                text(
                    "INSERT INTO public.follows (follower_id, following_id) "
                    "VALUES (:follower_id, :following_id) ON CONFLICT DO NOTHING"
                ),
                {"follower_id": follower_id, "following_id": target},
            )
            await session.commit()
            return True

    async def unfollow(self, follower_id: UUID, target_username: str) -> bool:
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            session: AsyncSession
            target = (
                await session.execute(
                    select(profiles.c.id).where(profiles.c.username == target_username)
                )
            ).scalar_one_or_none()
            if not target:
                from app.core.exceptions import NotFoundError
                raise NotFoundError("User not found")

            await session.execute(
                delete(follows).where(
                    and_(follows.c.follower_id == follower_id, follows.c.following_id == target)
                )
            )
            await session.commit()
            return True

    async def get_followers(self, username: str, limit: int = 50) -> list[dict]:
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            session: AsyncSession
            target = (
                await session.execute(
                    select(profiles.c.id).where(profiles.c.username == username)
                )
            ).scalar_one_or_none()
            if not target:
                return []

            follower_profiles = profiles.alias("fp")
            rows = (
                await session.execute(
                    select(follower_profiles.c.username, follower_profiles.c.display_name, follows.c.created_at)
                    .select_from(follows.join(follower_profiles, follows.c.follower_id == follower_profiles.c.id))
                    .where(follows.c.following_id == target)
                    .order_by(follows.c.created_at.desc())
                    .limit(limit)
                )
            ).fetchall()

            return [
                {"username": r.username, "display_name": r.display_name, "followed_at": str(r.created_at)}
                for r in rows
            ]

    async def get_following(self, username: str, limit: int = 50) -> list[dict]:
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            session: AsyncSession
            source = (
                await session.execute(
                    select(profiles.c.id).where(profiles.c.username == username)
                )
            ).scalar_one_or_none()
            if not source:
                return []

            following_profiles = profiles.alias("fp")
            rows = (
                await session.execute(
                    select(following_profiles.c.username, following_profiles.c.display_name, follows.c.created_at)
                    .select_from(follows.join(following_profiles, follows.c.following_id == following_profiles.c.id))
                    .where(follows.c.follower_id == source)
                    .order_by(follows.c.created_at.desc())
                    .limit(limit)
                )
            ).fetchall()

            return [
                {"username": r.username, "display_name": r.display_name, "followed_at": str(r.created_at)}
                for r in rows
            ]

    async def get_pnl_leaderboard(self, limit: int = 25) -> list[dict]:
        """Global PnL leaderboard ranked by realized PnL (cached 60s)."""
        from app.services.cache_service import cache_get, cache_set

        cache_key = f"leaderboard:pnl:{limit}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            from sqlalchemy import desc

            result = await session.execute(
                select(
                    profiles.c.username,
                    profiles.c.display_name,
                    func.sum(positions.c.realized_pnl).label("total_pnl"),
                    func.count().label("position_count"),
                )
                .select_from(positions.join(profiles, positions.c.profile_id == profiles.c.id))
                .group_by(profiles.c.id, profiles.c.username, profiles.c.display_name)
                .order_by(desc("total_pnl"))
                .limit(limit)
            )
            rows = [
                {
                    "rank": i + 1,
                    "username": row.username,
                    "display_name": row.display_name,
                    "total_pnl": str(row.total_pnl),
                    "position_count": int(row.position_count),
                }
                for i, row in enumerate(result.fetchall())
            ]
            await cache_set(cache_key, rows, ttl_seconds=60)
            return rows
