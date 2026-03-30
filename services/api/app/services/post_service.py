from uuid import UUID

from app.core.actor import CurrentActor
from app.core.exceptions import ForbiddenError
from app.repositories.base import PostRepository
from app.schemas.post import PostCreateRequest, PostResponse


class PostService:
    def __init__(self, repository: PostRepository) -> None:
        self._repository = repository

    async def list_posts(self, actor: CurrentActor, community_slug: str) -> list[PostResponse]:
        return await self._repository.list_posts(community_slug, actor.id, actor.is_admin)

    async def create_post(
        self,
        actor: CurrentActor,
        community_slug: str,
        payload: PostCreateRequest,
    ) -> PostResponse:
        return await self._repository.create_post(community_slug, actor.id, actor.is_admin, payload)

    async def list_pending_posts(self, actor: CurrentActor) -> list[PostResponse]:
        self._ensure_admin(actor)
        return await self._repository.list_pending_posts()

    async def approve_post(self, actor: CurrentActor, post_id: UUID, review_notes: str | None) -> PostResponse:
        self._ensure_admin(actor)
        return await self._repository.review_post(post_id, actor.id, True, review_notes)

    async def reject_post(self, actor: CurrentActor, post_id: UUID, review_notes: str | None) -> PostResponse:
        self._ensure_admin(actor)
        return await self._repository.review_post(post_id, actor.id, False, review_notes)

    def _ensure_admin(self, actor: CurrentActor) -> None:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
