from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import (
    CurrentActor,
    get_amm_service,
    get_current_actor,
    get_depth_kpi_service,
    get_fee_service,
)
from app.schemas.liquidity import (
    AmmStatusResponse,
    DepthSnapshotResponse,
    FeePreviewRequest,
    FeePreviewResponse,
    MarketDepthReportResponse,
)
from app.services.amm_service import AmmService
from app.services.depth_kpi_service import DepthKpiService
from app.services.fee_service import FeeService

router = APIRouter(prefix="/liquidity", tags=["liquidity"])


@router.post("/fee-preview", response_model=FeePreviewResponse)
async def preview_fee(
    payload: FeePreviewRequest,
    service: FeeService = Depends(get_fee_service),
) -> FeePreviewResponse:
    breakdown = await service.preview_fee(
        market_id=payload.market_id,
        quantity=Decimal(payload.quantity),
        price=Decimal(payload.price),
        is_maker=payload.is_maker,
    )
    return FeePreviewResponse(**breakdown.to_dict())


@router.get("/depth/{market_id}/{outcome_id}", response_model=DepthSnapshotResponse)
async def get_depth_snapshot(
    market_id: UUID,
    outcome_id: UUID,
    service: DepthKpiService = Depends(get_depth_kpi_service),
) -> DepthSnapshotResponse:
    snap = await service.get_depth_snapshot(market_id, outcome_id)
    return DepthSnapshotResponse(**snap.to_dict())


@router.get("/depth/{market_id}", response_model=MarketDepthReportResponse)
async def get_market_depth(
    market_id: UUID,
    outcome_ids: str = "",
    service: DepthKpiService = Depends(get_depth_kpi_service),
) -> MarketDepthReportResponse:
    ids = [UUID(oid.strip()) for oid in outcome_ids.split(",") if oid.strip()]
    snapshots = await service.get_market_depth_report(market_id, ids)
    return MarketDepthReportResponse(
        market_id=market_id,
        outcomes=[DepthSnapshotResponse(**s) for s in snapshots],
    )


@router.get("/amm/status", response_model=AmmStatusResponse)
async def amm_status(
    actor: CurrentActor = Depends(get_current_actor),
    service: AmmService = Depends(get_amm_service),
) -> AmmStatusResponse:
    if not actor.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    status = service.get_status()
    return AmmStatusResponse(**status)
