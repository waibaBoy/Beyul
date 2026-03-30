from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_market_service
from app.core.exceptions import NotFoundError
from app.schemas.market import MarketResponse
from app.services.market_service import MarketService

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=list[MarketResponse])
async def list_markets(
    service: MarketService = Depends(get_market_service),
) -> list[MarketResponse]:
    return await service.list_markets()


@router.get("/{market_slug}", response_model=MarketResponse)
async def get_market(
    market_slug: str,
    service: MarketService = Depends(get_market_service),
) -> MarketResponse:
    try:
        return await service.get_market(market_slug)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
