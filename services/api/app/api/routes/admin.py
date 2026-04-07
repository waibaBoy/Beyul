from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentActor, get_admin_service, get_current_actor, get_portfolio_service
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.schemas.admin import OracleApprovalRequest, OracleApprovalResponse, OracleLiveReadinessResponse, ReviewQueueResponse
from app.schemas.common import ReviewDecisionRequest
from app.schemas.market import MarketResponse
from app.schemas.portfolio import AdminFundBalanceRequest, MarketResolutionResponse, MarketSettlementFinalizeRequest, PortfolioSummaryResponse
from app.services.admin_service import AdminService
from app.services.portfolio_service import PortfolioService

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


@router.post("/fund-balance", response_model=PortfolioSummaryResponse)
async def fund_balance(
    payload: AdminFundBalanceRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioSummaryResponse:
    try:
        return await service.fund_balance(actor, payload)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/oracle/live-readiness", response_model=OracleLiveReadinessResponse)
async def get_oracle_live_readiness(
    actor: CurrentActor = Depends(get_current_actor),
    service: AdminService = Depends(get_admin_service),
) -> OracleLiveReadinessResponse:
    try:
        return await service.get_oracle_live_readiness(actor)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/oracle/approve-bond", response_model=OracleApprovalResponse)
async def approve_oracle_bond(
    payload: OracleApprovalRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: AdminService = Depends(get_admin_service),
) -> OracleApprovalResponse:
    try:
        return await service.approve_oracle_bond_allowance(actor, payload.amount_wei)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/markets/{market_slug}/settle", response_model=MarketResolutionResponse)
async def settle_market(
    market_slug: str,
    payload: MarketSettlementFinalizeRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: AdminService = Depends(get_admin_service),
) -> MarketResolutionResponse:
    try:
        return await service.settle_market(actor, market_slug, payload)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
