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
from app.schemas.market import (
    MarketDisputeCreateRequest,
    MarketDisputeEvidenceCreateRequest,
    MarketDisputeResponse,
    MarketDisputeReviewRequest,
    MarketHoldersResponse,
    MarketResolutionStateResponse,
    MarketResponse,
)
from app.schemas.market import (
    MarketHistoryResponse,
    MarketOrderCreateRequest,
    MarketOrderResponse,
    MarketStatusUpdateRequest,
    MarketTradingShellResponse,
)
from app.schemas.post import PostCreateRequest, PostResponse
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)
from app.schemas.portfolio import (
    AdminFundBalanceRequest,
    MarketResolutionResponse,
    MarketSettlementFinalizeRequest,
    MarketSettlementRequestCreateRequest,
    PortfolioSummaryResponse,
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

    async def update_market_status(self, slug: str, status: str) -> MarketResponse: ...

    async def get_market_resolution_state(self, slug: str) -> MarketResolutionStateResponse: ...

    async def create_market_dispute(
        self,
        slug: str,
        actor_id: UUID,
        payload: MarketDisputeCreateRequest,
    ) -> MarketDisputeResponse: ...

    async def add_market_dispute_evidence(
        self,
        slug: str,
        dispute_id: UUID,
        actor_id: UUID,
        payload: MarketDisputeEvidenceCreateRequest,
    ) -> MarketDisputeResponse: ...

    async def review_market_dispute(
        self,
        slug: str,
        dispute_id: UUID,
        payload: MarketDisputeReviewRequest,
    ) -> MarketDisputeResponse: ...

    async def request_settlement(
        self,
        slug: str,
        requester_id: UUID,
        payload: MarketSettlementRequestCreateRequest,
    ) -> MarketResolutionResponse: ...

    async def reconcile_oracle_resolution(self, slug: str) -> MarketResolutionStateResponse: ...

    async def settle_market(
        self,
        slug: str,
        reviewer_id: UUID,
        payload: MarketSettlementFinalizeRequest,
    ) -> MarketResolutionResponse: ...


class TradingRepository(Protocol):
    async def get_market_trading_shell(self, slug: str) -> MarketTradingShellResponse: ...

    async def get_market_holders(self, slug: str, limit: int) -> MarketHoldersResponse: ...

    async def get_market_history(
        self,
        slug: str,
        outcome_id: UUID,
        range_key: str,
    ) -> MarketHistoryResponse: ...

    async def list_market_orders(self, slug: str, actor_id: UUID) -> list[MarketOrderResponse]: ...

    async def create_market_order(
        self,
        slug: str,
        actor_id: UUID,
        payload: MarketOrderCreateRequest,
    ) -> MarketOrderResponse: ...

    async def cancel_market_order(
        self,
        slug: str,
        order_id: UUID,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> MarketOrderResponse: ...

    async def get_portfolio_summary(self, actor_id: UUID) -> PortfolioSummaryResponse: ...

    async def fund_balance(
        self,
        reviewer_id: UUID,
        payload: AdminFundBalanceRequest,
    ) -> PortfolioSummaryResponse: ...
