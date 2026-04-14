from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    amount: str
    rail: str = "crypto"
    asset_code: str = "USDC"
    wallet_address: str | None = None


class WithdrawalRequest(BaseModel):
    amount: str
    rail: str = "crypto"
    asset_code: str = "USDC"
    wallet_address: str | None = None


class TransferResponse(BaseModel):
    id: str
    direction: str
    rail: str
    asset_code: str
    amount: str
    fee_amount: str
    net_amount: str
    status: str
    wallet_address: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class TransferListResponse(BaseModel):
    transfers: list[TransferResponse] = Field(default_factory=list)
    count: int = 0
