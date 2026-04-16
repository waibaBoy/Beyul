import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.deps import CurrentActor, get_current_actor, get_market_service, get_notification_service, get_trading_service, require_oracle_secret
from app.core.container import container
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ServiceUnavailableError
from app.schemas.market import (
    MarketDisputeCreateRequest,
    MarketDisputeEvidenceCreateRequest,
    MarketDisputeResponse,
    MarketDisputeReviewRequest,
    MarketHoldersResponse,
    MarketHistoryResponse,
    MarketOrderCreateRequest,
    MarketOrderResponse,
    MarketResolutionStateResponse,
    MarketResponse,
    MarketStatusUpdateRequest,
    MarketTradingShellResponse,
)
from app.schemas.market_bootstrap import MarketDetailBootstrapResponse
from app.schemas.portfolio import MarketResolutionResponse, MarketSettlementFinalizeRequest, MarketSettlementRequestCreateRequest
from app.services.market_service import MarketService
from app.services.notification_emitter import emit_market_status_change, emit_settlement_finalized
from app.services.notification_service import NotificationService
from app.services.trading_service import TradingService

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=list[MarketResponse])
async def list_markets(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    service: MarketService = Depends(get_market_service),
) -> list[MarketResponse]:
    return await service.list_markets(limit=limit, offset=offset, status_filter=status)


@router.get("/{market_slug}/trading-shell", response_model=MarketTradingShellResponse)
async def get_market_trading_shell(
    market_slug: str,
    service: TradingService = Depends(get_trading_service),
) -> MarketTradingShellResponse:
    try:
        return await service.get_market_trading_shell(market_slug)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")


@router.get("/{market_slug}/bootstrap", response_model=MarketDetailBootstrapResponse)
async def get_market_bootstrap(
    market_slug: str,
    authorization: str | None = Header(default=None),
    trading_service: TradingService = Depends(get_trading_service),
    market_service: MarketService = Depends(get_market_service),
) -> MarketDetailBootstrapResponse:
    try:
        shell_task = trading_service.get_market_trading_shell(market_slug)
        holders_task = trading_service.get_market_holders(market_slug, limit=12)
        resolution_task = market_service.get_market_resolution_state(market_slug)
        shell, holders, resolution_state = await asyncio.gather(shell_task, holders_task, resolution_task)

        backend_user = None
        my_orders = []
        portfolio = None
        if authorization:
            claims = await container.supabase_auth_service.verify_bearer_token(authorization)
            actor = await container.actor_service.resolve_authenticated_actor(claims)
            backend_user = {
                "id": actor.id,
                "username": actor.username,
                "display_name": actor.display_name,
                "is_admin": actor.is_admin,
            }
            my_orders, portfolio = await asyncio.gather(
                trading_service.list_market_orders(actor, market_slug),
                trading_service.get_portfolio_summary(actor),
            )

        return MarketDetailBootstrapResponse(
            shell=shell,
            holders=holders,
            resolution_state=resolution_state,
            backend_user=backend_user,
            my_orders=my_orders,
            portfolio=portfolio,
        )
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    except (ConflictError, ForbiddenError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{market_slug}/holders", response_model=MarketHoldersResponse)
async def get_market_holders(
    market_slug: str,
    limit: int = Query(default=20, ge=1, le=50),
    service: TradingService = Depends(get_trading_service),
) -> MarketHoldersResponse:
    try:
        return await service.get_market_holders(market_slug, limit)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")


@router.get("/{market_slug}/resolution", response_model=MarketResolutionStateResponse)
async def get_market_resolution_state(
    market_slug: str,
    service: MarketService = Depends(get_market_service),
) -> MarketResolutionStateResponse:
    try:
        return await service.get_market_resolution_state(market_slug)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")


@router.post("/{market_slug}/disputes", response_model=MarketDisputeResponse, status_code=status.HTTP_201_CREATED)
async def create_market_dispute(
    market_slug: str,
    payload: MarketDisputeCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketService = Depends(get_market_service),
) -> MarketDisputeResponse:
    try:
        return await service.create_market_dispute(actor, market_slug, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{market_slug}/disputes/{dispute_id}/evidence", response_model=MarketDisputeResponse)
async def add_market_dispute_evidence(
    market_slug: str,
    dispute_id: UUID,
    payload: MarketDisputeEvidenceCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketService = Depends(get_market_service),
) -> MarketDisputeResponse:
    try:
        return await service.add_market_dispute_evidence(actor, market_slug, dispute_id, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/{market_slug}/oracle/disputes/{dispute_id}/review",
    response_model=MarketDisputeResponse,
    dependencies=[Depends(require_oracle_secret)],
)
async def review_market_dispute(
    market_slug: str,
    dispute_id: UUID,
    payload: MarketDisputeReviewRequest,
    service: MarketService = Depends(get_market_service),
) -> MarketDisputeResponse:
    try:
        return await service.review_market_dispute(market_slug, dispute_id, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{market_slug}/history", response_model=MarketHistoryResponse)
async def get_market_history(
    market_slug: str,
    outcome_id: UUID,
    range_key: str = Query(default="1H", alias="range"),
    service: TradingService = Depends(get_trading_service),
) -> MarketHistoryResponse:
    try:
        return await service.get_market_history(market_slug, outcome_id, range_key)
    except NotFoundError as exc:
        detail = "Market outcome not found" if "outcome" in str(exc).lower() else "Market not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{market_slug}/orders/me", response_model=list[MarketOrderResponse])
async def list_my_market_orders(
    market_slug: str,
    actor: CurrentActor = Depends(get_current_actor),
    service: TradingService = Depends(get_trading_service),
) -> list[MarketOrderResponse]:
    try:
        return await service.list_market_orders(actor, market_slug)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")


@router.post("/{market_slug}/orders", response_model=MarketOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_market_order(
    market_slug: str,
    payload: MarketOrderCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: TradingService = Depends(get_trading_service),
) -> MarketOrderResponse:
    try:
        return await service.create_market_order(actor, market_slug, payload)
    except NotFoundError as exc:
        detail = "Market outcome not found" if "outcome" in str(exc).lower() else "Market not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.delete("/{market_slug}/orders/{order_id}", response_model=MarketOrderResponse)
async def cancel_market_order(
    market_slug: str,
    order_id: str,
    actor: CurrentActor = Depends(get_current_actor),
    service: TradingService = Depends(get_trading_service),
) -> MarketOrderResponse:
    try:
        from uuid import UUID

        return await service.cancel_market_order(actor, market_slug, UUID(order_id))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market order not found")
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/{market_slug}/status", response_model=MarketResponse)
async def update_market_status(
    market_slug: str,
    payload: MarketStatusUpdateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketService = Depends(get_market_service),
    trading_service: TradingService = Depends(get_trading_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> MarketResponse:
    try:
        result = await service.update_market_status(actor, market_slug, payload.status)
        holders = None
        try:
            holders = await trading_service.get_market_holders(market_slug, limit=500)
        except Exception:
            pass
        await emit_market_status_change(notification_service, holders, market_slug, payload.status)
        return result
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{market_slug}/settlement-requests", response_model=MarketResolutionResponse)
async def request_market_settlement(
    market_slug: str,
    payload: MarketSettlementRequestCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: MarketService = Depends(get_market_service),
) -> MarketResolutionResponse:
    try:
        return await service.request_settlement(actor, market_slug, payload)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/{market_slug}/oracle/reconcile",
    response_model=MarketResolutionStateResponse,
    dependencies=[Depends(require_oracle_secret)],
)
async def reconcile_market_oracle_resolution(
    market_slug: str,
    service: MarketService = Depends(get_market_service),
) -> MarketResolutionStateResponse:
    try:
        return await service.reconcile_oracle_resolution(market_slug)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{market_slug}/oracle/finalize", response_model=MarketResolutionResponse, dependencies=[Depends(require_oracle_secret)])
async def finalize_market_settlement(
    market_slug: str,
    payload: MarketSettlementFinalizeRequest,
    service: MarketService = Depends(get_market_service),
    trading_service: TradingService = Depends(get_trading_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> MarketResolutionResponse:
    try:
        result = await service.finalize_oracle_settlement(market_slug, payload)
        holders = None
        try:
            holders = await trading_service.get_market_holders(market_slug, limit=500)
        except Exception:
            pass
        await emit_settlement_finalized(notification_service, holders, market_slug)
        return result
    except NotFoundError as exc:
        detail = "Winning outcome not found" if "outcome" in str(exc).lower() else "Market not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{market_slug}", response_model=MarketResponse)
async def get_market(
    market_slug: str,
    service: MarketService = Depends(get_market_service),
) -> MarketResponse:
    try:
        return await service.get_market(market_slug)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
