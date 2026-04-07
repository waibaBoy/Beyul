from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.market import MarketOrderResponse, MarketTradeResponse


class PortfolioBalanceResponse(BaseModel):
    asset_code: str
    rail_mode: str
    account_code: str
    settled_balance: str
    reserved_balance: str
    available_balance: str


class PortfolioPositionResponse(BaseModel):
    market_id: UUID
    market_slug: str
    market_title: str
    market_status: str
    outcome_id: UUID
    outcome_label: str
    quantity: str
    average_entry_price: str | None = None
    net_cost: str
    realized_pnl: str
    unrealized_pnl: str
    last_trade_at: datetime | None = None


class PortfolioSummaryResponse(BaseModel):
    balances: list[PortfolioBalanceResponse] = Field(default_factory=list)
    positions: list[PortfolioPositionResponse] = Field(default_factory=list)
    open_orders: list[MarketOrderResponse] = Field(default_factory=list)
    recent_trades: list[MarketTradeResponse] = Field(default_factory=list)


class AdminFundBalanceRequest(BaseModel):
    profile_id: UUID
    asset_code: str
    rail_mode: str
    amount: Decimal
    description: str | None = None


class MarketSettlementRequestCreateRequest(BaseModel):
    source_reference_url: str | None = None
    notes: str | None = None


class MarketSettlementFinalizeRequest(BaseModel):
    winning_outcome_id: UUID
    source_reference_url: str | None = None
    notes: str | None = None
    candidate_id: UUID | None = None


class MarketResolutionResponse(BaseModel):
    id: UUID
    market_id: UUID
    winning_outcome_id: UUID | None = None
    candidate_id: UUID | None = None
    status: str = "finalized"
    resolution_mode: str
    settlement_source_id: UUID | None = None
    source_reference_url: str | None = None
    finalizes_at: datetime | None = None
    resolved_at: datetime
