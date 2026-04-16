import logging
from uuid import UUID

from app.core.actor import CurrentActor
from app.core.exceptions import ForbiddenError
from app.repositories.base import MarketRepository
from app.schemas.market import (
    MarketDisputeCreateRequest,
    MarketDisputeEvidenceCreateRequest,
    MarketDisputeResponse,
    MarketDisputeReviewRequest,
    MarketResolutionStateResponse,
    MarketResponse,
)
from app.schemas.portfolio import (
    MarketResolutionResponse,
    MarketSettlementFinalizeRequest,
    MarketSettlementRequestCreateRequest,
)

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def list_markets(self, limit: int = 50, offset: int = 0, status_filter: str | None = None) -> list[MarketResponse]:
        from app.services.cache_service import cache_get, cache_set

        cache_key = f"markets:list:{limit}:{offset}:{status_filter or 'all'}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return [MarketResponse.model_validate(m) for m in cached]

        rows = await self._repository.list_markets(limit=limit, offset=offset, status_filter=status_filter)
        await cache_set(cache_key, [m.model_dump(mode="json") for m in rows], ttl_seconds=15)
        return rows

    async def get_market(self, slug: str) -> MarketResponse:
        return await self._repository.get_market(slug)

    async def get_market_resolution_state(self, slug: str) -> MarketResolutionStateResponse:
        return await self._repository.get_market_resolution_state(slug)

    async def create_market_dispute(
        self,
        actor: CurrentActor,
        slug: str,
        payload: MarketDisputeCreateRequest,
    ) -> MarketDisputeResponse:
        logger.info(
            "market_dispute_requested market_slug=%s actor_id=%s title=%s",
            slug,
            actor.id,
            payload.title,
        )
        return await self._repository.create_market_dispute(slug, actor.id, payload)

    async def add_market_dispute_evidence(
        self,
        actor: CurrentActor,
        slug: str,
        dispute_id: UUID,
        payload: MarketDisputeEvidenceCreateRequest,
    ) -> MarketDisputeResponse:
        logger.info(
            "market_dispute_evidence_added market_slug=%s dispute_id=%s actor_id=%s evidence_type=%s",
            slug,
            dispute_id,
            actor.id,
            payload.evidence_type,
        )
        return await self._repository.add_market_dispute_evidence(slug, dispute_id, actor.id, payload)

    async def review_market_dispute(
        self,
        slug: str,
        dispute_id: UUID,
        payload: MarketDisputeReviewRequest,
    ) -> MarketDisputeResponse:
        logger.info(
            "market_dispute_reviewed market_slug=%s dispute_id=%s status=%s",
            slug,
            dispute_id,
            payload.status,
        )
        return await self._repository.review_market_dispute(slug, dispute_id, payload)

    async def update_market_status(self, actor: CurrentActor, slug: str, status: str) -> MarketResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        logger.info(
            "market_status_update_requested market_slug=%s actor_id=%s status=%s",
            slug,
            actor.id,
            status,
        )
        return await self._repository.update_market_status(slug, status)

    async def request_settlement(
        self,
        actor: CurrentActor,
        slug: str,
        payload: MarketSettlementRequestCreateRequest,
    ) -> MarketResolutionResponse:
        logger.info(
            "market_settlement_requested market_slug=%s actor_id=%s source_reference_url=%s",
            slug,
            actor.id,
            payload.source_reference_url,
        )
        return await self._repository.request_settlement(slug, actor.id, payload)

    async def reconcile_oracle_resolution(self, slug: str) -> MarketResolutionStateResponse:
        logger.info("market_oracle_reconcile_requested market_slug=%s", slug)
        return await self._repository.reconcile_oracle_resolution(slug)

    async def finalize_oracle_settlement(
        self,
        slug: str,
        payload: MarketSettlementFinalizeRequest,
    ) -> MarketResolutionResponse:
        logger.info(
            "market_oracle_finalize_requested market_slug=%s candidate_id=%s winning_outcome_id=%s",
            slug,
            payload.candidate_id,
            payload.winning_outcome_id,
        )
        return await self._repository.settle_market(slug, None, payload)
