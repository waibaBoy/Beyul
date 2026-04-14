"""Deposit and withdrawal request management.

Handles the lifecycle of transfer requests:
- Create deposit/withdrawal requests
- Process status transitions
- Fee calculation for withdrawals
- Wallet address validation (stub)
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, insert, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import transfer_requests

logger = logging.getLogger(__name__)

WITHDRAWAL_FEE_BPS = 50  # 0.5% withdrawal fee
MIN_WITHDRAWAL = Decimal("10")
MAX_WITHDRAWAL = Decimal("50000")
MIN_DEPOSIT = Decimal("1")


class TransferService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create_deposit(
        self,
        profile_id: UUID,
        amount: Decimal,
        rail: str,
        asset_code: str = "USDC",
        wallet_address: str | None = None,
    ) -> dict:
        if amount < MIN_DEPOSIT:
            from app.core.exceptions import ConflictError
            raise ConflictError(f"Minimum deposit is {MIN_DEPOSIT}")

        net_amount = amount  # No fee on deposits

        if not self._session_factory:
            return {
                "id": str(UUID(int=0)),
                "direction": "deposit",
                "rail": rail,
                "asset_code": asset_code,
                "amount": str(amount),
                "fee_amount": "0",
                "net_amount": str(net_amount),
                "status": "pending",
                "wallet_address": wallet_address,
            }

        async with self._session_factory() as session:
            result = await session.execute(
                insert(transfer_requests)
                .values(
                    profile_id=profile_id,
                    direction="deposit",
                    rail=rail,
                    asset_code=asset_code,
                    amount=amount,
                    fee_amount=Decimal("0"),
                    net_amount=net_amount,
                    status="pending",
                    wallet_address=wallet_address,
                    metadata={},
                )
                .returning(transfer_requests.c.id, transfer_requests.c.created_at)
            )
            row = result.one()
            await session.commit()
            return {
                "id": str(row.id),
                "direction": "deposit",
                "rail": rail,
                "asset_code": asset_code,
                "amount": str(amount),
                "fee_amount": "0",
                "net_amount": str(net_amount),
                "status": "pending",
                "wallet_address": wallet_address,
                "created_at": str(row.created_at),
            }

    async def create_withdrawal(
        self,
        profile_id: UUID,
        amount: Decimal,
        rail: str,
        asset_code: str = "USDC",
        wallet_address: str | None = None,
    ) -> dict:
        if amount < MIN_WITHDRAWAL:
            from app.core.exceptions import ConflictError
            raise ConflictError(f"Minimum withdrawal is {MIN_WITHDRAWAL}")
        if amount > MAX_WITHDRAWAL:
            from app.core.exceptions import ConflictError
            raise ConflictError(f"Maximum withdrawal is {MAX_WITHDRAWAL}")

        fee = (amount * Decimal(WITHDRAWAL_FEE_BPS) / Decimal("10000")).quantize(Decimal("0.00000001"))
        net_amount = amount - fee

        if not self._session_factory:
            return {
                "id": str(UUID(int=0)),
                "direction": "withdrawal",
                "rail": rail,
                "asset_code": asset_code,
                "amount": str(amount),
                "fee_amount": str(fee),
                "net_amount": str(net_amount),
                "status": "pending",
                "wallet_address": wallet_address,
            }

        async with self._session_factory() as session:
            result = await session.execute(
                insert(transfer_requests)
                .values(
                    profile_id=profile_id,
                    direction="withdrawal",
                    rail=rail,
                    asset_code=asset_code,
                    amount=amount,
                    fee_amount=fee,
                    net_amount=net_amount,
                    status="pending",
                    wallet_address=wallet_address,
                    metadata={},
                )
                .returning(transfer_requests.c.id, transfer_requests.c.created_at)
            )
            row = result.one()
            await session.commit()
            return {
                "id": str(row.id),
                "direction": "withdrawal",
                "rail": rail,
                "asset_code": asset_code,
                "amount": str(amount),
                "fee_amount": str(fee),
                "net_amount": str(net_amount),
                "status": "pending",
                "wallet_address": wallet_address,
                "created_at": str(row.created_at),
            }

    async def list_transfers(self, profile_id: UUID, limit: int = 50) -> list[dict]:
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            result = await session.execute(
                select(transfer_requests)
                .where(transfer_requests.c.profile_id == profile_id)
                .order_by(transfer_requests.c.created_at.desc())
                .limit(limit)
            )
            return [
                {
                    "id": str(row.id),
                    "direction": row.direction,
                    "rail": row.rail,
                    "asset_code": row.asset_code,
                    "amount": str(row.amount),
                    "fee_amount": str(row.fee_amount),
                    "net_amount": str(row.net_amount),
                    "status": row.status,
                    "wallet_address": row.wallet_address,
                    "created_at": str(row.created_at),
                    "completed_at": str(row.completed_at) if row.completed_at else None,
                }
                for row in result.fetchall()
            ]
