from app.repositories.base import MarketRepository
from app.schemas.market import MarketResponse


class MarketService:
    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def list_markets(self) -> list[MarketResponse]:
        return await self._repository.list_markets()

    async def get_market(self, slug: str) -> MarketResponse:
        return await self._repository.get_market(slug)
