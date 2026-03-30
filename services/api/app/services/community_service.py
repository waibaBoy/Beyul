from uuid import UUID

from app.core.actor import CurrentActor
from app.repositories.base import CommunityRepository
from app.schemas.community import (
    CommunityCreateRequest,
    CommunityMemberCreateRequest,
    CommunityMemberResponse,
    CommunityMemberUpdateRequest,
    CommunityResponse,
    CommunityUpdateRequest,
)


class CommunityService:
    def __init__(self, repository: CommunityRepository) -> None:
        self._repository = repository

    async def list_communities(self, actor: CurrentActor) -> list[CommunityResponse]:
        return await self._repository.list_communities(actor.id, actor.is_admin)

    async def create_community(self, actor: CurrentActor, payload: CommunityCreateRequest) -> CommunityResponse:
        return await self._repository.create_community(actor.id, payload)

    async def get_community(self, actor: CurrentActor, slug: str) -> CommunityResponse:
        return await self._repository.get_community(slug, actor.id, actor.is_admin)

    async def update_community(
        self,
        actor: CurrentActor,
        slug: str,
        payload: CommunityUpdateRequest,
    ) -> CommunityResponse:
        return await self._repository.update_community(slug, actor.id, actor.is_admin, payload)

    async def list_members(self, actor: CurrentActor, slug: str) -> list[CommunityMemberResponse]:
        return await self._repository.list_members(slug, actor.id, actor.is_admin)

    async def add_member(
        self,
        actor: CurrentActor,
        slug: str,
        payload: CommunityMemberCreateRequest,
    ) -> CommunityMemberResponse:
        return await self._repository.add_member(slug, actor.id, actor.is_admin, payload)

    async def update_member(
        self,
        actor: CurrentActor,
        slug: str,
        member_id: UUID,
        payload: CommunityMemberUpdateRequest,
    ) -> CommunityMemberResponse:
        return await self._repository.update_member(slug, actor.id, actor.is_admin, member_id, payload)

    async def delete_member(self, actor: CurrentActor, slug: str, member_id: UUID) -> None:
        await self._repository.delete_member(slug, actor.id, actor.is_admin, member_id)
