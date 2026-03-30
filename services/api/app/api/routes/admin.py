from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentActor, get_admin_service, get_current_actor
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.schemas.admin import ReviewQueueResponse
from app.schemas.common import ReviewDecisionRequest
from app.schemas.market import MarketResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    actor: CurrentActor = Depends(get_current_actor),
    service: AdminService = Depends(get_admin_service),
) -> ReviewQueueResponse:
    try:
        return await service.get_review_queue(actor)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/market-requests/{request_id}/publish", response_model=MarketResponse)
async def publish_market_request(
    request_id: UUID,
    payload: ReviewDecisionRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: AdminService = Depends(get_admin_service),
) -> MarketResponse:
    try:
        return await service.publish_market_request(actor, request_id, payload.review_notes)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
