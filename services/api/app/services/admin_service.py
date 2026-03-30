from app.core.actor import CurrentActor
from app.core.exceptions import ForbiddenError
from app.repositories.base import MarketRepository, MarketRequestRepository, PostRepository
from app.schemas.market import MarketResponse
from app.schemas.admin import ReviewQueueResponse


class AdminService:
    def __init__(
        self,
        post_repository: PostRepository,
        market_request_repository: MarketRequestRepository,
        market_repository: MarketRepository,
    ) -> None:
        self._post_repository = post_repository
        self._market_request_repository = market_request_repository
        self._market_repository = market_repository

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
