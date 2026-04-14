from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MarketHistoryRangeKey = Literal["1M", "5M", "30M", "1H", "1D", "1W"]

MARKET_HISTORY_RANGE_WINDOWS: dict[MarketHistoryRangeKey, tuple[timedelta, int]] = {
    "1M": (timedelta(minutes=1), 5),
    "5M": (timedelta(minutes=5), 15),
    "30M": (timedelta(minutes=30), 60),
    "1H": (timedelta(hours=1), 300),
    "1D": (timedelta(days=1), 3600),
    "1W": (timedelta(weeks=1), 21600),
}


def resolve_market_history_range(range_key: str) -> tuple[MarketHistoryRangeKey, timedelta, int]:
    normalized = range_key.upper()
    if normalized not in MARKET_HISTORY_RANGE_WINDOWS:
        raise ValueError(f"Unsupported market history range: {range_key}")
    typed_range = normalized  # keep mypy happy after membership check
    lookback_window, interval_seconds = MARKET_HISTORY_RANGE_WINDOWS[typed_range]
    return typed_range, lookback_window, interval_seconds


class MarketOutcomeResponse(BaseModel):
    id: UUID
    code: str
    label: str
    outcome_index: int
    status: str
    settlement_value: str | None = None


class MarketSettlementSourceResponse(BaseModel):
    id: UUID
    code: str
    name: str
    resolution_mode: str
    base_url: str | None = None


class MarketContractTimesResponse(BaseModel):
    trading_opens_at: datetime | None = None
    trading_closes_at: datetime | None = None
    resolution_due_at: datetime | None = None
    dispute_window_ends_at: datetime | None = None
    activated_at: datetime | None = None
    cancelled_at: datetime | None = None
    settled_at: datetime | None = None


class MarketReferenceContextResponse(BaseModel):
    contract_type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    reference_label: str | None = None
    reference_source_label: str | None = None
    reference_asset: str | None = None
    reference_symbol: str | None = None
    reference_price: str | None = None
    price_to_beat: str | None = None
    reference_timestamp: datetime | None = None
    notes: str | None = None


class MarketResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    question: str
    description: str | None = None
    status: str
    market_access_mode: str
    rail_mode: str
    resolution_mode: str
    rules_text: str
    community_id: UUID | None = None
    community_slug: str | None = None
    community_name: str | None = None
    created_from_request_id: UUID | None = None
    creator_id: UUID
    settlement_source_id: UUID
    image_url: str | None = None
    settlement_reference_url: str | None = None
    settlement_reference_label: str | None = None
    settlement_source: MarketSettlementSourceResponse | None = None
    timing: MarketContractTimesResponse = Field(default_factory=MarketContractTimesResponse)
    reference_context: MarketReferenceContextResponse | None = None
    min_seed_amount: str
    min_liquidity_amount: str | None = None
    min_participants: int
    creator_fee_bps: int | None = None
    platform_fee_bps: int | None = None
    traded_volume: str = "0"
    total_volume: str = "0"
    last_price: str | None = None
    total_trades_count: int = 0
    created_at: datetime
    updated_at: datetime
    outcomes: list[MarketOutcomeResponse] = Field(default_factory=list)


class MarketQuoteResponse(BaseModel):
    outcome_id: UUID
    outcome_code: str
    outcome_label: str
    last_price: str | None = None
    best_bid: str | None = None
    best_ask: str | None = None
    traded_volume: str
    resting_bid_quantity: str
    resting_ask_quantity: str


class MarketDepthLevelResponse(BaseModel):
    price: str
    quantity: str
    order_count: int


class MarketOrderBookResponse(BaseModel):
    outcome_id: UUID
    outcome_label: str
    bids: list[MarketDepthLevelResponse]
    asks: list[MarketDepthLevelResponse]


class MarketTradeResponse(BaseModel):
    id: UUID
    outcome_id: UUID
    outcome_label: str
    price: str
    quantity: str
    gross_notional: str
    fee_amount: str = "0"
    executed_at: datetime


class MarketOrderResponse(BaseModel):
    id: UUID
    market_id: UUID
    outcome_id: UUID
    outcome_label: str
    side: str
    order_type: str
    status: str
    quantity: str
    price: str | None = None
    matched_quantity: str
    remaining_quantity: str
    max_total_cost: str | None = None
    source: str
    client_order_id: str | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class MarketTradingShellResponse(BaseModel):
    market: MarketResponse
    quotes: list[MarketQuoteResponse]
    order_books: list[MarketOrderBookResponse]
    recent_trades: list[MarketTradeResponse]


class MarketHolderEntryResponse(BaseModel):
    profile_id: UUID
    username: str | None = None
    display_name: str
    outcome_id: UUID
    outcome_label: str
    quantity: str
    average_entry_price: str | None = None
    realized_pnl: str = "0"
    unrealized_pnl: str = "0"


class MarketHolderGroupResponse(BaseModel):
    outcome_id: UUID
    outcome_label: str
    holders: list[MarketHolderEntryResponse] = Field(default_factory=list)


class MarketHoldersResponse(BaseModel):
    market_id: UUID
    market_slug: str
    groups: list[MarketHolderGroupResponse] = Field(default_factory=list)
    last_updated_at: datetime


class MarketHistoryBucketResponse(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    open_price: str | None = None
    high_price: str | None = None
    low_price: str | None = None
    close_price: str | None = None
    volume: str
    trade_count: int


class MarketHistoryResponse(BaseModel):
    market_id: UUID
    market_slug: str
    outcome_id: UUID
    outcome_label: str
    range_key: MarketHistoryRangeKey
    interval_seconds: int
    window_start: datetime
    window_end: datetime
    buckets: list[MarketHistoryBucketResponse]


class MarketResolutionCandidateResponse(BaseModel):
    id: UUID
    market_id: UUID
    proposed_outcome_id: UUID | None = None
    proposed_by: UUID | None = None
    settlement_source_id: UUID | None = None
    status: str
    source_reference_url: str | None = None
    source_reference_text: str | None = None
    payload: dict = Field(default_factory=dict)
    proposed_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None


class MarketDisputeEvidenceResponse(BaseModel):
    id: UUID
    dispute_id: UUID
    submitted_by: UUID
    evidence_type: str
    url: str | None = None
    description: str | None = None
    payload: dict = Field(default_factory=dict)
    created_at: datetime


class MarketResolutionEventResponse(BaseModel):
    id: str
    event_type: str
    title: str
    status: str
    occurred_at: datetime
    actor_id: UUID | None = None
    reference_id: str | None = None
    details: dict = Field(default_factory=dict)


class MarketDisputeResponse(BaseModel):
    id: UUID
    market_id: UUID
    resolution_id: UUID | None = None
    raised_by: UUID
    status: str
    title: str
    reason: str
    fee_amount: str = "0"
    opened_at: datetime
    closed_at: datetime | None = None
    reviewed_by: UUID | None = None
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    evidence: list[MarketDisputeEvidenceResponse] = Field(default_factory=list)


class MarketResolutionStateResponse(BaseModel):
    market_id: UUID
    market_slug: str
    current_resolution_id: UUID | None = None
    current_status: str | None = None
    current_payload: dict = Field(default_factory=dict)
    candidate_id: UUID | None = None
    winning_outcome_id: UUID | None = None
    source_reference_url: str | None = None
    finalizes_at: datetime | None = None
    resolved_at: datetime | None = None
    candidates: list[MarketResolutionCandidateResponse] = Field(default_factory=list)
    disputes: list[MarketDisputeResponse] = Field(default_factory=list)
    history: list[MarketResolutionEventResponse] = Field(default_factory=list)


class MarketDisputeCreateRequest(BaseModel):
    title: str
    reason: str


class MarketDisputeEvidenceCreateRequest(BaseModel):
    evidence_type: Literal["source_link", "archive_snapshot", "screenshot", "transaction", "market_rule", "commentary", "other"]
    url: str | None = None
    description: str | None = None
    payload: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evidence_shape(self) -> "MarketDisputeEvidenceCreateRequest":
        normalized_url = self.url.strip() if isinstance(self.url, str) else None
        normalized_description = self.description.strip() if isinstance(self.description, str) else None
        url_required_types = {"source_link", "archive_snapshot", "screenshot", "transaction"}
        if self.evidence_type in url_required_types and not normalized_url:
            raise ValueError(f"url is required for evidence_type={self.evidence_type}")
        if self.evidence_type in {"market_rule", "commentary"} and not normalized_description:
            raise ValueError(f"description is required for evidence_type={self.evidence_type}")
        self.url = normalized_url
        self.description = normalized_description
        return self


class MarketDisputeReviewRequest(BaseModel):
    status: Literal["under_review", "upheld", "dismissed", "withdrawn"]
    review_notes: str | None = None


class MarketOrderCreateRequest(BaseModel):
    outcome_id: UUID
    side: str
    order_type: str = "limit"
    quantity: Decimal
    price: Decimal | None = None
    client_order_id: str | None = None


class MarketStatusUpdateRequest(BaseModel):
    status: str
