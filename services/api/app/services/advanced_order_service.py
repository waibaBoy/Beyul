"""Advanced order types: stop-loss, take-profit, trailing stop.

These are stored as conditional triggers that fire when a market
price crosses the trigger threshold. When triggered, they submit
a regular market or limit order through the standard flow.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

VALID_ORDER_TYPES = {"stop_loss", "take_profit", "trailing_stop"}


@dataclass
class ConditionalOrder:
    id: UUID
    profile_id: UUID
    market_slug: str
    outcome_id: UUID
    side: str
    quantity: Decimal
    trigger_price: Decimal
    limit_price: Decimal | None
    order_type: str
    trailing_offset_bps: int | None
    status: str  # pending, triggered, cancelled, expired
    created_at: datetime
    triggered_at: datetime | None = None


class AdvancedOrderService:
    """In-memory conditional order manager.

    In production this would be backed by a DB table and a price
    monitoring loop. For now it stores orders in memory and provides
    a check_triggers method that can be called on each trade event.
    """

    def __init__(self) -> None:
        self._orders: dict[UUID, ConditionalOrder] = {}

    def create_conditional_order(
        self,
        profile_id: UUID,
        market_slug: str,
        outcome_id: UUID,
        side: str,
        quantity: str,
        trigger_price: str,
        limit_price: str | None,
        order_type: str,
        trailing_offset_bps: int | None,
    ) -> ConditionalOrder:
        if order_type not in VALID_ORDER_TYPES:
            from app.core.exceptions import ValidationError

            raise ValidationError(f"Invalid order type: {order_type}. Must be one of {VALID_ORDER_TYPES}")

        if side not in ("buy", "sell"):
            from app.core.exceptions import ValidationError

            raise ValidationError("Side must be 'buy' or 'sell'")

        order = ConditionalOrder(
            id=uuid4(),
            profile_id=profile_id,
            market_slug=market_slug,
            outcome_id=outcome_id,
            side=side,
            quantity=Decimal(quantity),
            trigger_price=Decimal(trigger_price),
            limit_price=Decimal(limit_price) if limit_price else None,
            order_type=order_type,
            trailing_offset_bps=trailing_offset_bps,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self._orders[order.id] = order
        logger.info("Conditional order created: %s %s %s @ trigger=%s", order.id, order_type, side, trigger_price)
        return order

    def list_orders(self, profile_id: UUID) -> list[ConditionalOrder]:
        return [o for o in self._orders.values() if o.profile_id == profile_id]

    def cancel_order(self, profile_id: UUID, order_id: UUID) -> ConditionalOrder | None:
        order = self._orders.get(order_id)
        if not order or order.profile_id != profile_id:
            return None
        if order.status != "pending":
            return order
        order.status = "cancelled"
        return order

    def check_triggers(self, outcome_id: UUID, current_price: Decimal) -> list[ConditionalOrder]:
        """Check all pending orders for the given outcome and return any that should trigger."""
        triggered = []
        for order in list(self._orders.values()):
            if order.status != "pending" or order.outcome_id != outcome_id:
                continue

            should_trigger = False
            if order.order_type == "stop_loss":
                if order.side == "sell" and current_price <= order.trigger_price:
                    should_trigger = True
                elif order.side == "buy" and current_price >= order.trigger_price:
                    should_trigger = True
            elif order.order_type == "take_profit":
                if order.side == "sell" and current_price >= order.trigger_price:
                    should_trigger = True
                elif order.side == "buy" and current_price <= order.trigger_price:
                    should_trigger = True
            elif order.order_type == "trailing_stop":
                if order.side == "sell" and current_price <= order.trigger_price:
                    should_trigger = True

            if should_trigger:
                order.status = "triggered"
                order.triggered_at = datetime.now(timezone.utc)
                triggered.append(order)
                logger.info("Conditional order triggered: %s at price %s", order.id, current_price)

        return triggered

    def get_stats(self) -> dict:
        statuses: dict[str, int] = {}
        for o in self._orders.values():
            statuses[o.status] = statuses.get(o.status, 0) + 1
        return {"total_orders": len(self._orders), "by_status": statuses}
