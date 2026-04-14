"""Fee calculation engine.

Computes platform and creator fees per trade based on:
- Market-level fee BPS config (platform_fee_bps, creator_fee_bps)
- Maker/taker role (makers pay 0%, takers pay full platform fee)
- Creator reward tier (creator fee share from creator_reward_tiers)
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import markets

logger = logging.getLogger(__name__)

PLATFORM_FEE_BPS_DEFAULT = 200  # 2%
CREATOR_FEE_BPS_DEFAULT = 0
ONE_BPS = Decimal("0.0001")


class FeeBreakdown:
    __slots__ = (
        "gross_notional",
        "platform_fee",
        "creator_fee",
        "total_fee",
        "net_proceeds",
        "is_maker",
    )

    def __init__(
        self,
        gross_notional: Decimal,
        platform_fee: Decimal,
        creator_fee: Decimal,
        is_maker: bool,
    ) -> None:
        self.gross_notional = gross_notional
        self.platform_fee = platform_fee
        self.creator_fee = creator_fee
        self.total_fee = platform_fee + creator_fee
        self.net_proceeds = gross_notional - self.total_fee
        self.is_maker = is_maker

    def to_dict(self) -> dict:
        return {
            "gross_notional": str(self.gross_notional),
            "platform_fee": str(self.platform_fee),
            "creator_fee": str(self.creator_fee),
            "total_fee": str(self.total_fee),
            "net_proceeds": str(self.net_proceeds),
            "is_maker": self.is_maker,
        }


def compute_fee(
    gross_notional: Decimal,
    platform_fee_bps: int,
    creator_fee_bps: int,
    is_maker: bool,
) -> FeeBreakdown:
    """Pure fee computation — no DB access.

    Makers pay zero fees (incentive to provide liquidity).
    Takers pay platform_fee_bps on gross_notional.
    Creator fee is a share of the platform fee, controlled by creator_fee_bps.
    """
    if is_maker:
        return FeeBreakdown(
            gross_notional=gross_notional,
            platform_fee=Decimal("0"),
            creator_fee=Decimal("0"),
            is_maker=True,
        )

    platform_fee = (gross_notional * Decimal(platform_fee_bps) * ONE_BPS).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )
    creator_fee = (gross_notional * Decimal(creator_fee_bps) * ONE_BPS).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )
    return FeeBreakdown(
        gross_notional=gross_notional,
        platform_fee=platform_fee,
        creator_fee=creator_fee,
        is_maker=False,
    )


class FeeService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def get_market_fee_config(self, market_id: UUID) -> tuple[int, int]:
        """Returns (platform_fee_bps, creator_fee_bps) for a market."""
        if not self._session_factory:
            return PLATFORM_FEE_BPS_DEFAULT, CREATOR_FEE_BPS_DEFAULT

        async with self._session_factory() as session:
            session: AsyncSession
            row = (
                await session.execute(
                    select(markets.c.platform_fee_bps, markets.c.creator_fee_bps).where(
                        markets.c.id == market_id
                    )
                )
            ).one_or_none()
            if not row:
                return PLATFORM_FEE_BPS_DEFAULT, CREATOR_FEE_BPS_DEFAULT
            return int(row.platform_fee_bps), int(row.creator_fee_bps)

    async def compute_trade_fees(
        self,
        market_id: UUID,
        gross_notional: Decimal,
        is_maker: bool,
    ) -> FeeBreakdown:
        platform_bps, creator_bps = await self.get_market_fee_config(market_id)
        return compute_fee(gross_notional, platform_bps, creator_bps, is_maker)

    async def preview_fee(
        self,
        market_id: UUID,
        quantity: Decimal,
        price: Decimal,
        is_maker: bool,
    ) -> FeeBreakdown:
        gross = (quantity * price).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        return await self.compute_trade_fees(market_id, gross, is_maker)
