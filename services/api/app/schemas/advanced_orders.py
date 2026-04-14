from uuid import UUID

from pydantic import BaseModel


class ConditionalOrderRequest(BaseModel):
    market_slug: str
    outcome_id: UUID
    side: str  # "buy" or "sell"
    quantity: str
    trigger_price: str
    limit_price: str | None = None
    order_type: str = "stop_loss"  # "stop_loss", "take_profit", "trailing_stop"
    trailing_offset_bps: int | None = None


class ConditionalOrderResponse(BaseModel):
    id: UUID
    market_slug: str
    outcome_id: UUID
    side: str
    quantity: str
    trigger_price: str
    limit_price: str | None = None
    order_type: str
    trailing_offset_bps: int | None = None
    status: str  # "pending", "triggered", "cancelled", "expired"
    created_at: str


class ConditionalOrderListResponse(BaseModel):
    orders: list[ConditionalOrderResponse]
    count: int
