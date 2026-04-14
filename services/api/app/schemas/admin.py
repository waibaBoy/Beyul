from pydantic import BaseModel, Field

from app.schemas.market_request import MarketRequestResponse
from app.schemas.post import PostResponse


class ReviewQueueResponse(BaseModel):
    pending_posts: list[PostResponse] = Field(default_factory=list)
    pending_market_requests: list[MarketRequestResponse] = Field(default_factory=list)


class OracleLiveReadinessResponse(BaseModel):
    provider: str
    execution_mode: str
    network: str | None = None
    chain_id: int
    rpc_chain_id: int | None = None
    signer_address: str | None = None
    oracle_contract_address: str | None = None
    currency_address: str | None = None
    native_balance_wei: str | None = None
    token_balance_wei: str | None = None
    allowance_wei: str | None = None
    required_bond_wei: str
    reward_wei: str
    liveness_minutes: int
    approval_required: bool = False
    ready_for_live_submission: bool = False
    issues: list[str] = Field(default_factory=list)
    tx_preview: dict = Field(default_factory=dict)


class OracleApprovalRequest(BaseModel):
    amount_wei: str | None = None


class OracleApprovalResponse(BaseModel):
    provider: str
    execution_mode: str
    status: str
    chain_id: int
    signer_address: str | None = None
    spender_address: str | None = None
    currency_address: str | None = None
    amount_wei: str
    allowance_before_wei: str
    tx_hash: str | None = None
    submission_status: str
    nonce: int | None = None
    gas_limit: int | None = None
    gas_price_wei: str | None = None


class RollingUpDownRunRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval_minutes: int = 5
    lookahead_windows: int = 3
    auto_open_markets: bool = True
    request_settlement_for_due: bool = True
    finalize_due_markets: bool = False


class RollingUpDownRunResponse(BaseModel):
    symbol: str
    interval_minutes: int
    created_markets: list[str] = Field(default_factory=list)
    opened_markets: list[str] = Field(default_factory=list)
    skipped_existing_markets: list[str] = Field(default_factory=list)
    settlement_requested: list[str] = Field(default_factory=list)
    settlement_finalized: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SettlementQueueItemResponse(BaseModel):
    market_slug: str
    market_status: str
    trading_closes_at: str | None = None
    resolution_due_at: str | None = None
    current_resolution_status: str | None = None
    dispute_count: int = 0
    candidate_count: int = 0


class SettlementQueueResponse(BaseModel):
    pending: list[SettlementQueueItemResponse] = Field(default_factory=list)


class SettlementAutomationRunRequest(BaseModel):
    reconcile_due_markets: bool = True
    finalize_settled_markets: bool = True
    include_disputed: bool = False
    dry_run: bool = False


class SettlementAutomationRunResponse(BaseModel):
    processed_markets: list[str] = Field(default_factory=list)
    reconciled_markets: list[str] = Field(default_factory=list)
    finalized_markets: list[str] = Field(default_factory=list)
    skipped_markets: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
