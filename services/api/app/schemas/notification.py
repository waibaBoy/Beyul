from pydantic import BaseModel, Field


NOTIFICATION_KINDS = {
    "order_filled",
    "order_cancelled",
    "order_rejected",
    "market_opened",
    "market_settled",
    "market_cancelled",
    "market_disputed",
    "settlement_requested",
    "settlement_finalized",
    "price_alert",
    "system",
}


class NotificationResponse(BaseModel):
    id: str
    profile_id: str
    kind: str
    title: str
    body: str | None = None
    market_slug: str | None = None
    market_id: str | None = None
    order_id: str | None = None
    payload: dict = Field(default_factory=dict)
    is_read: bool = False
    created_at: str


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse] = Field(default_factory=list)
    total_count: int = 0
    unread_count: int = 0


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int = 0


class NotificationMarkReadRequest(BaseModel):
    notification_ids: list[str] = Field(default_factory=list, max_length=100)
    mark_all: bool = False
