from app.core.actor import CurrentActor
from app.core.exceptions import ForbiddenError
from app.repositories.base import TradingRepository
from app.schemas.portfolio import AdminFundBalanceRequest, PortfolioSummaryResponse


class PortfolioService:
    def __init__(self, repository: TradingRepository) -> None:
        self._repository = repository

    async def get_portfolio_summary(self, actor: CurrentActor) -> PortfolioSummaryResponse:
        return await self._repository.get_portfolio_summary(actor.id)

    async def fund_balance(self, actor: CurrentActor, payload: AdminFundBalanceRequest) -> PortfolioSummaryResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        return await self._repository.fund_balance(actor.id, payload)
