from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.schemas.community import (
    CommunityCreateRequest,
    CommunityMemberCreateRequest,
    CommunityMemberResponse,
    CommunityMemberUpdateRequest,
    CommunityResponse,
    CommunityUpdateRequest,
)
from app.schemas.market_request import (
    MarketRequestAnswerResponse,
    MarketRequestAnswerUpsertRequest,
    MarketRequestCreateRequest,
    MarketRequestResponse,
    MarketRequestUpdateRequest,
)
from app.schemas.market import MarketResponse
from app.schemas.post import PostCreateRequest, PostResponse
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)


class ProfileRepository(Protocol):
    async def get_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
    ) -> ProfileResponse: ...

    async def get_profile_by_username(self, username: str) -> ProfileResponse: ...

    async def update_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
        payload: ProfileUpdateRequest,
    ) -> ProfileResponse: ...

    async def list_wallets(self, actor_id: UUID) -> list[UserWalletResponse]: ...

    async def create_wallet(self, actor_id: UUID, payload: WalletCreateRequest) -> UserWalletResponse: ...

    async def update_wallet(
        self,
        actor_id: UUID,
        wallet_id: UUID,
        payload: WalletUpdateRequest,
    ) -> UserWalletResponse: ...

    async def delete_wallet(self, actor_id: UUID, wallet_id: UUID) -> None: ...


class CommunityRepository(Protocol):
    async def list_communities(self, actor_id: UUID, actor_is_admin: bool) -> list[CommunityResponse]: ...

    async def create_community(self, actor_id: UUID, payload: CommunityCreateRequest) -> CommunityResponse: ...

    async def get_community(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> CommunityResponse: ...

    async def update_community(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityUpdateRequest,
    ) -> CommunityResponse: ...

    async def list_members(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> list[CommunityMemberResponse]: ...

    async def add_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityMemberCreateRequest,
    ) -> CommunityMemberResponse: ...

    async def update_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        member_id: UUID,
        payload: CommunityMemberUpdateRequest,
    ) -> CommunityMemberResponse: ...

    async def delete_member(self, slug: str, actor_id: UUID, actor_is_admin: bool, member_id: UUID) -> None: ...


class PostRepository(Protocol):
    async def list_posts(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> list[PostResponse]: ...

    async def create_post(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: PostCreateRequest,
    ) -> PostResponse: ...

    async def list_pending_posts(self) -> list[PostResponse]: ...

    async def review_post(
        self,
        post_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> PostResponse: ...


class MarketRequestRepository(Protocol):
    async def list_requests(self, requester_id: UUID) -> list[MarketRequestResponse]: ...

    async def list_pending_requests(self) -> list[MarketRequestResponse]: ...

    async def create_request(
        self,
        requester_id: UUID,
        payload: MarketRequestCreateRequest,
    ) -> MarketRequestResponse: ...

    async def get_request(self, request_id: UUID, requester_id: UUID | None = None) -> MarketRequestResponse: ...

    async def update_request(
        self,
        request_id: UUID,
        requester_id: UUID,
        payload: MarketRequestUpdateRequest,
    ) -> MarketRequestResponse: ...

    async def upsert_answer(
        self,
        request_id: UUID,
        requester_id: UUID,
        question_key: str,
        payload: MarketRequestAnswerUpsertRequest,
    ) -> MarketRequestAnswerResponse: ...

    async def ensure_exists(self, request_id: UUID, requester_id: UUID | None = None) -> None: ...

    async def list_answers(
        self,
        request_id: UUID,
        requester_id: UUID | None = None,
    ) -> list[MarketRequestAnswerResponse]: ...

    async def submit_request(
        self,
        request_id: UUID,
        requester_id: UUID,
    ) -> MarketRequestResponse: ...

    async def review_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> MarketRequestResponse: ...


class MarketRepository(Protocol):
    async def publish_from_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        review_notes: str | None,
    ) -> MarketResponse: ...

    async def list_markets(self) -> list[MarketResponse]: ...

    async def get_market(self, slug: str) -> MarketResponse: ...
