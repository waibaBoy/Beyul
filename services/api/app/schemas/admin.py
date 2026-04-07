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
