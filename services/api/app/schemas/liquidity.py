from uuid import UUID

from pydantic import BaseModel, Field


class FeePreviewRequest(BaseModel):
    market_id: UUID
    quantity: str
    price: str
    is_maker: bool = False


class FeePreviewResponse(BaseModel):
    gross_notional: str
    platform_fee: str
    creator_fee: str
    total_fee: str
    net_proceeds: str
    is_maker: bool


class DepthSnapshotResponse(BaseModel):
    market_id: UUID
    outcome_id: UUID
    best_bid: str | None = None
    best_ask: str | None = None
    spread: str | None = None
    spread_bps: int | None = None
    mid_price: str | None = None
    bid_depth_5pct: str = "0"
    ask_depth_5pct: str = "0"
    total_bid_depth: str = "0"
    total_ask_depth: str = "0"
    imbalance_ratio: float = 0.0
    open_order_count: int = 0


class MarketDepthReportResponse(BaseModel):
    market_id: UUID
    outcomes: list[DepthSnapshotResponse] = Field(default_factory=list)


class AmmQuoteResponse(BaseModel):
    bid_price: str
    bid_quantity: str
    ask_price: str
    ask_quantity: str
    mid_price: str
    spread_bps: int


class AmmStatusResponse(BaseModel):
    enabled: bool
    spread_bps: int
    quote_size: str
    max_inventory: str
    active_positions: int
    inventories: dict = Field(default_factory=dict)
