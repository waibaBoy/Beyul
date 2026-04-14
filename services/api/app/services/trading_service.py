from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from app.core.actor import CurrentActor
from app.repositories.base import TradingRepository
from app.schemas.market import (
    MarketHoldersResponse,
    MarketHistoryResponse,
    MarketOrderCreateRequest,
    MarketOrderResponse,
    MarketTradingShellResponse,
)
from app.schemas.portfolio import PortfolioSummaryResponse

if TYPE_CHECKING:
    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class TradingService:
    def __init__(self, repository: TradingRepository, notification_service: NotificationService | None = None) -> None:
        self._repository = repository
        self._notifications = notification_service

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
        result = await self._repository.create_market_order(slug, actor.id, payload)
        await self._try_emit_order_notification(actor.id, slug, result)
        return result

    async def cancel_market_order(
        self,
        actor: CurrentActor,
        slug: str,
        order_id,
    ) -> MarketOrderResponse:
        result = await self._repository.cancel_market_order(slug, order_id, actor.id, actor.is_admin)
        if self._notifications and result.status == "cancelled":
            try:
                await self._notifications.emit(
                    profile_id=actor.id,
                    kind="order_cancelled",
                    title=f"Order cancelled on {slug}",
                    body=f"Your {result.side} order for {result.quantity} shares was cancelled.",
                    market_slug=slug,
                    order_id=UUID(result.id) if result.id else None,
                )
            except Exception:
                logger.debug("Failed to emit order_cancelled notification", exc_info=True)
        return result

    async def _try_emit_order_notification(self, profile_id: UUID, slug: str, order: MarketOrderResponse) -> None:
        if not self._notifications:
            return
        try:
            if order.status in {"filled", "partially_filled"}:
                await self._notifications.emit(
                    profile_id=profile_id,
                    kind="order_filled",
                    title=f"Order filled on {slug}",
                    body=f"Your {order.side} order for {order.matched_quantity} shares matched at {order.price or 'market'}.",
                    market_slug=slug,
                    order_id=UUID(order.id) if order.id else None,
                )
            elif order.status == "rejected":
                await self._notifications.emit(
                    profile_id=profile_id,
                    kind="order_rejected",
                    title=f"Order rejected on {slug}",
                    body=order.rejection_reason or "Your order was rejected.",
                    market_slug=slug,
                    order_id=UUID(order.id) if order.id else None,
                )
        except Exception:
            logger.debug("Failed to emit order notification", exc_info=True)

    async def get_portfolio_summary(self, actor: CurrentActor) -> PortfolioSummaryResponse:
        return await self._repository.get_portfolio_summary(actor.id)
