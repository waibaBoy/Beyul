from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentActor, get_current_actor
from app.core.container import container
from app.schemas.common import MessageResponse
from app.schemas.push import (
    PushStatsResponse,
    PushSubscribeRequest,
    PushSubscribeResponse,
    PushUnsubscribeRequest,
)

router = APIRouter(prefix="/push", tags=["push-notifications"])


def _get_service():
    return container.push_notification_service


@router.post("/subscribe", response_model=PushSubscribeResponse)
async def subscribe(
    payload: PushSubscribeRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    result = await svc.register_subscription(
        profile_id=actor.id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
    )
    return PushSubscribeResponse(**result)


@router.post("/unsubscribe", response_model=MessageResponse)
async def unsubscribe(
    payload: PushUnsubscribeRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    await svc.unregister_subscription(actor.id, payload.endpoint)
    return MessageResponse(message="Unsubscribed from push notifications")


@router.get("/stats", response_model=PushStatsResponse)
async def push_stats(
    actor: CurrentActor = Depends(get_current_actor),
):
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    svc = _get_service()
    return PushStatsResponse(**svc.get_stats())
