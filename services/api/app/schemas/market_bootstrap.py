from pydantic import BaseModel, Field

from app.schemas.auth import AuthUserResponse
from app.schemas.market import (
    MarketHoldersResponse,
    MarketOrderResponse,
    MarketResolutionStateResponse,
    MarketTradingShellResponse,
)
from app.schemas.portfolio import PortfolioSummaryResponse


class MarketDetailBootstrapResponse(BaseModel):
    shell: MarketTradingShellResponse
    holders: MarketHoldersResponse | None = None
    resolution_state: MarketResolutionStateResponse | None = None
    backend_user: AuthUserResponse | None = None
    my_orders: list[MarketOrderResponse] = Field(default_factory=list)
    portfolio: PortfolioSummaryResponse | None = None
