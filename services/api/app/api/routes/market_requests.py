from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentActor, get_current_actor, get_market_request_service
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.schemas.common import ReviewDecisionRequest
from app.schemas.market_request import (
    MarketRequestAnswerResponse,
    MarketRequestAnswerUpsertRequest,
    MarketRequestCreateRequest,
    MarketRequestResponse,
    MarketRequestUpdateRequest,
)
from app.services.market_request_service import MarketRequestService

router = APIRouter(prefix="/market-requests", tags=["market-requests"])


@router.get("/me", response_model=list[MarketRequestResponse])
async def list_my_market_requests(
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> list[MarketRequestResponse]:
    return await service.list_my_requests(actor)


@router.post("", response_model=MarketRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_market_request(
    payload: MarketRequestCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestResponse:
    try:
        return await service.create_request(actor, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{request_id}", response_model=MarketRequestResponse)
async def get_market_request(
    request_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestResponse:
    try:
        return await service.get_request(actor, request_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")


@router.get("/{request_id}/answers", response_model=list[MarketRequestAnswerResponse])
async def list_market_request_answers(
    request_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> list[MarketRequestAnswerResponse]:
    try:
        return await service.list_answers(actor, request_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")


@router.patch("/{request_id}", response_model=MarketRequestResponse)
async def update_market_request(
    request_id: UUID,
    payload: MarketRequestUpdateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestResponse:
    try:
        return await service.update_request(actor, request_id, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")


@router.put(
    "/{request_id}/answers/{question_key}",
    response_model=MarketRequestAnswerResponse,
)
async def upsert_market_request_answer(
    request_id: UUID,
    question_key: str,
    payload: MarketRequestAnswerUpsertRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestAnswerResponse:
    try:
        return await service.upsert_answer(actor, request_id, question_key, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")


@router.post("/{request_id}/submit", response_model=MarketRequestResponse)
async def submit_market_request(
    request_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestResponse:
    try:
        return await service.submit_request(actor, request_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{request_id}/approve", response_model=MarketRequestResponse)
async def approve_market_request(
    request_id: UUID,
    payload: ReviewDecisionRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestResponse:
    try:
        return await service.approve_request(actor, request_id, payload.review_notes)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{request_id}/reject", response_model=MarketRequestResponse)
async def reject_market_request(
    request_id: UUID,
    payload: ReviewDecisionRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketRequestService = Depends(get_market_request_service),
) -> MarketRequestResponse:
    try:
        return await service.reject_request(actor, request_id, payload.review_notes)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market request not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
