from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentActor, get_current_actor, get_post_service
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.schemas.common import ReviewDecisionRequest
from app.schemas.post import PostResponse
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/{post_id}/approve", response_model=PostResponse)
async def approve_post(
    post_id: UUID,
    payload: ReviewDecisionRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: PostService = Depends(get_post_service),
) -> PostResponse:
    try:
        return await service.approve_post(actor, post_id, payload.review_notes)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{post_id}/reject", response_model=PostResponse)
async def reject_post(
    post_id: UUID,
    payload: ReviewDecisionRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: PostService = Depends(get_post_service),
) -> PostResponse:
    try:
        return await service.reject_post(actor, post_id, payload.review_notes)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
