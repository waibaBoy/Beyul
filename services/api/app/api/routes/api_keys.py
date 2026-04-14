from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentActor, get_current_actor
from app.core.container import container
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _get_service():
    return container.api_key_service


@router.post("", response_model=ApiKeyCreateResponse)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    result = await svc.create_key(
        profile_id=actor.id,
        label=payload.label,
        permissions=payload.permissions,
    )
    return ApiKeyCreateResponse(**result)


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    keys = await svc.list_keys(actor.id)
    return ApiKeyListResponse(
        keys=[ApiKeyResponse(**k) for k in keys],
        count=len(keys),
    )


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    revoked = await svc.revoke_key(actor.id, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return MessageResponse(message="API key revoked")
