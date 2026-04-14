from decimal import Decimal

from fastapi import APIRouter, Depends

from app.api.deps import CurrentActor, get_current_actor
from app.core.container import container
from app.schemas.transfer import (
    DepositRequest,
    TransferListResponse,
    TransferResponse,
    WithdrawalRequest,
)

router = APIRouter(prefix="/transfers", tags=["transfers"])


def _get_service():
    return container.transfer_service


@router.post("/deposit", response_model=TransferResponse)
async def create_deposit(
    payload: DepositRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    result = await svc.create_deposit(
        profile_id=actor.id,
        amount=Decimal(payload.amount),
        rail=payload.rail,
        asset_code=payload.asset_code,
        wallet_address=payload.wallet_address,
    )
    return TransferResponse(**result)


@router.post("/withdrawal", response_model=TransferResponse)
async def create_withdrawal(
    payload: WithdrawalRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    result = await svc.create_withdrawal(
        profile_id=actor.id,
        amount=Decimal(payload.amount),
        rail=payload.rail,
        asset_code=payload.asset_code,
        wallet_address=payload.wallet_address,
    )
    return TransferResponse(**result)


@router.get("/me", response_model=TransferListResponse)
async def list_my_transfers(
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    transfers = await svc.list_transfers(actor.id)
    return TransferListResponse(
        transfers=[TransferResponse(**t) for t in transfers],
        count=len(transfers),
    )
