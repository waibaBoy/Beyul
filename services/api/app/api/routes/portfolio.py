from fastapi import APIRouter, Depends

from app.api.deps import CurrentActor, get_current_actor, get_trading_service
from app.schemas.portfolio import PortfolioSummaryResponse
from app.services.trading_service import TradingService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/me", response_model=PortfolioSummaryResponse)
async def get_my_portfolio(
    actor: CurrentActor = Depends(get_current_actor),
    service: TradingService = Depends(get_trading_service),
) -> PortfolioSummaryResponse:
    return await service.get_portfolio_summary(actor)
