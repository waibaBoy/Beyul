from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentActor, get_current_actor, get_notification_service
from app.schemas.notification import (
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationUnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    actor: CurrentActor = Depends(get_current_actor),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    return await service.list_notifications(
        actor.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    actor: CurrentActor = Depends(get_current_actor),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationUnreadCountResponse:
    return await service.get_unread_count(actor.id)


@router.post("/mark-read")
async def mark_notifications_read(
    payload: NotificationMarkReadRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    if not payload.mark_all and not payload.notification_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide notification_ids or set mark_all to true.",
        )
    updated = await service.mark_read(
        actor.id,
        notification_ids=payload.notification_ids if not payload.mark_all else None,
        mark_all=payload.mark_all,
    )
    return {"updated": updated}
