"""Market depth KPI tracking.

Computes real-time liquidity quality metrics per market:
- Bid-ask spread (best bid vs best ask)
- Book depth at various price levels
- Time-weighted spread (rolling average)
- Imbalance ratio (bid depth vs ask depth)
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import orders

logger = logging.getLogger(__name__)


class DepthSnapshot:
    __slots__ = (
        "market_id",
        "outcome_id",
        "best_bid",
        "best_ask",
        "spread",
        "spread_bps",
        "mid_price",
        "bid_depth_5pct",
        "ask_depth_5pct",
        "total_bid_depth",
        "total_ask_depth",
        "imbalance_ratio",
        "open_order_count",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> dict:
        return {slot: getattr(self, slot, None) for slot in self.__slots__}


class DepthKpiService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def get_depth_snapshot(
        self, market_id: UUID, outcome_id: UUID
    ) -> DepthSnapshot:
        """Compute real-time depth metrics from the live order book."""
        if not self._session_factory:
            return self._empty_snapshot(market_id, outcome_id)

        async with self._session_factory() as session:
            session: AsyncSession

            open_filter = and_(
                orders.c.market_id == market_id,
                orders.c.outcome_id == outcome_id,
                orders.c.status.in_(["open", "partially_filled"]),
                orders.c.price.isnot(None),
            )

            # Best bid/ask
            best_bid_q = await session.execute(
                select(func.max(orders.c.price)).where(
                    open_filter, orders.c.side == "buy"
                )
            )
            best_ask_q = await session.execute(
                select(func.min(orders.c.price)).where(
                    open_filter, orders.c.side == "sell"
                )
            )

            best_bid = best_bid_q.scalar()
            best_ask = best_ask_q.scalar()

            # Aggregate depths
            depth_q = await session.execute(
                select(
                    orders.c.side,
                    func.sum(orders.c.remaining_quantity).label("total_depth"),
                    func.count().label("order_count"),
                ).where(open_filter).group_by(orders.c.side)
            )
            depth_rows = {row.side: row for row in depth_q.all()}

            total_bid = Decimal(str(depth_rows.get("buy", type("", (), {"total_depth": 0})).total_depth or 0))
            total_ask = Decimal(str(depth_rows.get("sell", type("", (), {"total_depth": 0})).total_depth or 0))
            bid_count = getattr(depth_rows.get("buy"), "order_count", 0)
            ask_count = getattr(depth_rows.get("sell"), "order_count", 0)

            # Depth within 5% of mid
            bid_5pct = Decimal("0")
            ask_5pct = Decimal("0")
            mid = None
            spread = None
            spread_bps = None

            if best_bid is not None and best_ask is not None:
                bb = Decimal(str(best_bid))
                ba = Decimal(str(best_ask))
                mid = (bb + ba) / 2
                spread = ba - bb
                if mid > 0:
                    spread_bps = int((spread / mid) * 10000)

                # 5% band depth
                lower_5 = mid * Decimal("0.95")
                upper_5 = mid * Decimal("1.05")

                bid_5pct_q = await session.execute(
                    select(func.coalesce(func.sum(orders.c.remaining_quantity), 0)).where(
                        open_filter,
                        orders.c.side == "buy",
                        orders.c.price >= lower_5,
                    )
                )
                ask_5pct_q = await session.execute(
                    select(func.coalesce(func.sum(orders.c.remaining_quantity), 0)).where(
                        open_filter,
                        orders.c.side == "sell",
                        orders.c.price <= upper_5,
                    )
                )
                bid_5pct = Decimal(str(bid_5pct_q.scalar() or 0))
                ask_5pct = Decimal(str(ask_5pct_q.scalar() or 0))

            total_depth = total_bid + total_ask
            imbalance = (
                float(total_bid - total_ask) / float(total_depth) if total_depth > 0 else 0.0
            )

            return DepthSnapshot(
                market_id=market_id,
                outcome_id=outcome_id,
                best_bid=str(best_bid) if best_bid else None,
                best_ask=str(best_ask) if best_ask else None,
                spread=str(spread) if spread else None,
                spread_bps=spread_bps,
                mid_price=str(mid) if mid else None,
                bid_depth_5pct=str(bid_5pct),
                ask_depth_5pct=str(ask_5pct),
                total_bid_depth=str(total_bid),
                total_ask_depth=str(total_ask),
                imbalance_ratio=round(imbalance, 4),
                open_order_count=bid_count + ask_count,
            )

    async def get_market_depth_report(
        self, market_id: UUID, outcome_ids: list[UUID]
    ) -> list[dict]:
        """Get depth snapshots for all outcomes in a market."""
        results = []
        for oid in outcome_ids:
            snap = await self.get_depth_snapshot(market_id, oid)
            results.append(snap.to_dict())
        return results

    def _empty_snapshot(self, market_id: UUID, outcome_id: UUID) -> DepthSnapshot:
        return DepthSnapshot(
            market_id=market_id,
            outcome_id=outcome_id,
            best_bid=None,
            best_ask=None,
            spread=None,
            spread_bps=None,
            mid_price=None,
            bid_depth_5pct="0",
            ask_depth_5pct="0",
            total_bid_depth="0",
            total_ask_depth="0",
            imbalance_ratio=0.0,
            open_order_count=0,
        )
