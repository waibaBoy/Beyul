from app.core.actor import CurrentActor
from app.repositories.base import TradingRepository
from uuid import UUID

from app.schemas.market import (
    MarketHoldersResponse,
    MarketHistoryResponse,
    MarketOrderCreateRequest,
    MarketOrderResponse,
    MarketTradingShellResponse,
)
from app.schemas.portfolio import PortfolioSummaryResponse


class TradingService:
    def __init__(self, repository: TradingRepository) -> None:
        self._repository = repository

    async def get_market_trading_shell(self, slug: str) -> MarketTradingShellResponse:
        return await self._repository.get_market_trading_shell(slug)

    async def get_market_holders(self, slug: str, limit: int = 20) -> MarketHoldersResponse:
        return await self._repository.get_market_holders(slug, limit)

    async def get_market_history(
        self,
        slug: str,
        outcome_id: UUID,
        range_key: str,
    ) -> MarketHistoryResponse:
        return await self._repository.get_market_history(slug, outcome_id, range_key)

    async def list_market_orders(self, actor: CurrentActor, slug: str) -> list[MarketOrderResponse]:
        return await self._repository.list_market_orders(slug, actor.id)

    async def create_market_order(
        self,
        actor: CurrentActor,
        slug: str,
        payload: MarketOrderCreateRequest,
    ) -> MarketOrderResponse:
        return await self._repository.create_market_order(slug, actor.id, payload)

    async def cancel_market_order(
        self,
        actor: CurrentActor,
        slug: str,
        order_id,
    ) -> MarketOrderResponse:
        return await self._repository.cancel_market_order(slug, order_id, actor.id, actor.is_admin)

    async def get_portfolio_summary(self, actor: CurrentActor) -> PortfolioSummaryResponse:
        return await self._repository.get_portfolio_summary(actor.id)
