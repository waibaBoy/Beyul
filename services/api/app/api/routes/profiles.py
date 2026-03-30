from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentActor, get_current_actor, get_profile_service
from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    actor: CurrentActor = Depends(get_current_actor),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return await service.get_my_profile(actor)


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return await service.update_my_profile(actor, payload)


@router.get("/{username}", response_model=ProfileResponse)
async def get_profile(
    username: str,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    try:
        return await service.get_profile(username)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


@router.get("/me/wallets", response_model=list[UserWalletResponse])
async def list_my_wallets(
    actor: CurrentActor = Depends(get_current_actor),
    service: ProfileService = Depends(get_profile_service),
) -> list[UserWalletResponse]:
    return await service.list_wallets(actor)


@router.post("/me/wallets", response_model=UserWalletResponse, status_code=status.HTTP_201_CREATED)
async def create_my_wallet(
    payload: WalletCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: ProfileService = Depends(get_profile_service),
) -> UserWalletResponse:
    try:
        return await service.create_wallet(actor=actor, payload=payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/me/wallets/{wallet_id}", response_model=UserWalletResponse)
async def update_my_wallet(
    wallet_id: UUID,
    payload: WalletUpdateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: ProfileService = Depends(get_profile_service),
) -> UserWalletResponse:
    try:
        return await service.update_wallet(actor, wallet_id, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")


@router.delete("/me/wallets/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_wallet(
    wallet_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    try:
        await service.delete_wallet(actor, wallet_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
