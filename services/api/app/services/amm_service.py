"""Automated Market Maker (AMM) inventory service.

Provides liquidity on thin markets by placing resting orders
on both sides of the book. Uses a simplified constant-product
model adapted for prediction markets (prices bounded 0–1).

The AMM:
- Monitors markets with low depth or wide spreads
- Places symmetric bid/ask quotes around the current mid-price
- Adjusts inventory based on position exposure
- Respects configurable risk limits per market
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

logger = logging.getLogger(__name__)

ONE = Decimal("1")
ZERO = Decimal("0")
DEFAULT_SPREAD_BPS = 400  # 4% default spread for AMM quotes
DEFAULT_QUOTE_SIZE = Decimal("50")  # default quote quantity per side
MAX_INVENTORY_PER_MARKET = Decimal("500")  # max net position before pausing one side
MIN_PRICE = Decimal("0.02")
MAX_PRICE = Decimal("0.98")


@dataclass
class AmmQuote:
    bid_price: Decimal
    bid_quantity: Decimal
    ask_price: Decimal
    ask_quantity: Decimal
    mid_price: Decimal
    spread_bps: int


@dataclass
class AmmInventory:
    market_id: UUID
    outcome_id: UUID
    net_position: Decimal = ZERO
    total_bought: Decimal = ZERO
    total_sold: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    unrealized_pnl: Decimal = ZERO
    is_quoting: bool = True
    paused_reason: str | None = None


@dataclass
class AmmConfig:
    enabled: bool = False
    spread_bps: int = DEFAULT_SPREAD_BPS
    quote_size: Decimal = DEFAULT_QUOTE_SIZE
    max_inventory: Decimal = MAX_INVENTORY_PER_MARKET
    auto_quote_thin_markets: bool = True
    min_spread_threshold_bps: int = 1000  # quote if organic spread > 10%


class AmmService:
    def __init__(self, config: AmmConfig | None = None) -> None:
        self._config = config or AmmConfig()
        self._inventories: dict[str, AmmInventory] = {}

    @property
    def is_enabled(self) -> bool:
        return self._config.enabled

    def get_inventory(self, market_id: UUID, outcome_id: UUID) -> AmmInventory:
        key = f"{market_id}:{outcome_id}"
        if key not in self._inventories:
            self._inventories[key] = AmmInventory(
                market_id=market_id, outcome_id=outcome_id
            )
        return self._inventories[key]

    def compute_quotes(
        self,
        market_id: UUID,
        outcome_id: UUID,
        current_mid: Decimal | None,
        organic_spread_bps: int | None,
    ) -> AmmQuote | None:
        """Compute bid/ask quotes for a given market outcome.

        Returns None if quoting should be skipped (AMM disabled,
        organic spread is tight enough, or inventory limits hit).
        """
        if not self._config.enabled:
            return None

        if current_mid is None:
            current_mid = Decimal("0.50")

        if (
            organic_spread_bps is not None
            and organic_spread_bps <= self._config.min_spread_threshold_bps
            and not self._config.auto_quote_thin_markets
        ):
            return None

        inv = self.get_inventory(market_id, outcome_id)

        half_spread = (current_mid * Decimal(self._config.spread_bps) / Decimal("20000")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        bid_price = max(MIN_PRICE, (current_mid - half_spread).quantize(Decimal("0.0001")))
        ask_price = min(MAX_PRICE, (current_mid + half_spread).quantize(Decimal("0.0001")))

        bid_qty = self._config.quote_size
        ask_qty = self._config.quote_size

        # Skew sizing based on inventory exposure
        if inv.net_position > ZERO:
            # Long exposure — reduce bid size, increase ask size to unwind
            skew = min(inv.net_position / self._config.max_inventory, ONE)
            bid_qty = (bid_qty * (ONE - skew * Decimal("0.8"))).quantize(Decimal("1"))
            ask_qty = (ask_qty * (ONE + skew * Decimal("0.3"))).quantize(Decimal("1"))
        elif inv.net_position < ZERO:
            skew = min(abs(inv.net_position) / self._config.max_inventory, ONE)
            ask_qty = (ask_qty * (ONE - skew * Decimal("0.8"))).quantize(Decimal("1"))
            bid_qty = (bid_qty * (ONE + skew * Decimal("0.3"))).quantize(Decimal("1"))

        bid_qty = max(Decimal("1"), bid_qty)
        ask_qty = max(Decimal("1"), ask_qty)

        # Pause side if at inventory limit
        if inv.net_position >= self._config.max_inventory:
            bid_qty = ZERO
            inv.paused_reason = "max long inventory reached"
        elif inv.net_position <= -self._config.max_inventory:
            ask_qty = ZERO
            inv.paused_reason = "max short inventory reached"
        else:
            inv.paused_reason = None

        actual_spread = ask_price - bid_price
        actual_bps = int((actual_spread / current_mid) * 10000) if current_mid > 0 else 0

        return AmmQuote(
            bid_price=bid_price,
            bid_quantity=bid_qty,
            ask_price=ask_price,
            ask_quantity=ask_qty,
            mid_price=current_mid,
            spread_bps=actual_bps,
        )

    def record_fill(
        self,
        market_id: UUID,
        outcome_id: UUID,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        """Track an AMM fill to update inventory."""
        inv = self.get_inventory(market_id, outcome_id)
        if side == "buy":
            inv.net_position += quantity
            inv.total_bought += quantity
        else:
            inv.net_position -= quantity
            inv.total_sold += quantity
        logger.info(
            "AMM fill %s %s @ %s on %s/%s — net_pos=%s",
            side, quantity, price, market_id, outcome_id, inv.net_position,
        )

    def get_status(self) -> dict:
        return {
            "enabled": self._config.enabled,
            "spread_bps": self._config.spread_bps,
            "quote_size": str(self._config.quote_size),
            "max_inventory": str(self._config.max_inventory),
            "active_positions": len(self._inventories),
            "inventories": {
                k: {
                    "net_position": str(v.net_position),
                    "total_bought": str(v.total_bought),
                    "total_sold": str(v.total_sold),
                    "paused_reason": v.paused_reason,
                }
                for k, v in self._inventories.items()
            },
        }
