from app.core.actor import CurrentActor
from app.core.exceptions import ConflictError, ForbiddenError
from app.repositories.base import MarketRepository, MarketRequestRepository, PostRepository
from app.schemas.market import MarketResponse
from app.schemas.admin import (
    OracleApprovalResponse,
    OracleLiveReadinessResponse,
    ReviewQueueResponse,
)
from app.schemas.portfolio import MarketResolutionResponse, MarketSettlementFinalizeRequest
from app.services.oracle_service import OracleConfigurationError, OracleService


class AdminService:
    def __init__(
        self,
        post_repository: PostRepository,
        market_request_repository: MarketRequestRepository,
        market_repository: MarketRepository,
        oracle_service: OracleService,
    ) -> None:
        self._post_repository = post_repository
        self._market_request_repository = market_request_repository
        self._market_repository = market_repository
        self._oracle_service = oracle_service

    async def get_review_queue(self, actor: CurrentActor) -> ReviewQueueResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        pending_posts = await self._post_repository.list_pending_posts()
        pending_market_requests = await self._market_request_repository.list_pending_requests()
        return ReviewQueueResponse(
            pending_posts=pending_posts,
            pending_market_requests=pending_market_requests,
        )

    async def publish_market_request(
        self,
        actor: CurrentActor,
        request_id,
        review_notes: str | None,
    ) -> MarketResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        return await self._market_repository.publish_from_request(request_id, actor.id, review_notes)

    async def settle_market(
        self,
        actor: CurrentActor,
        market_slug: str,
        payload: MarketSettlementFinalizeRequest,
    ) -> MarketResolutionResponse:
        raise ForbiddenError("Direct admin settlement is disabled. Use the oracle settlement workflow instead.")

    async def get_oracle_live_readiness(self, actor: CurrentActor) -> OracleLiveReadinessResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        try:
            return OracleLiveReadinessResponse.model_validate(await self._oracle_service.get_live_readiness())
        except OracleConfigurationError as exc:
            raise ConflictError(str(exc)) from exc

    async def approve_oracle_bond_allowance(
        self,
        actor: CurrentActor,
        amount_wei: str | None,
    ) -> OracleApprovalResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        try:
            return OracleApprovalResponse.model_validate(await self._oracle_service.approve_bond_allowance(amount_wei))
        except OracleConfigurationError as exc:
            raise ConflictError(str(exc)) from exc
