from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.market_templates import build_contract_metadata_from_template
from app.core.slug import normalize_slug
from app.repositories.base import (
    CommunityRepository,
    MarketRepository,
    MarketRequestRepository,
    PostRepository,
    ProfileRepository,
    TradingRepository,
)
from app.services.market_data_service import MarketDataService
from app.schemas.market import (
    MarketDisputeCreateRequest,
    MarketDisputeEvidenceCreateRequest,
    MarketDisputeEvidenceResponse,
    MarketDisputeResponse,
    MarketDisputeReviewRequest,
    MarketContractTimesResponse,
    MarketHolderGroupResponse,
    MarketHoldersResponse,
    MarketHistoryBucketResponse,
    MarketHistoryResponse,
    MarketDepthLevelResponse,
    MarketOrderCreateRequest,
    MarketOrderResponse,
    MarketOrderBookResponse,
    MarketOutcomeResponse,
    MarketQuoteResponse,
    MarketResolutionCandidateResponse,
    MarketResolutionEventResponse,
    MarketResolutionStateResponse,
    MarketReferenceContextResponse,
    MarketResponse,
    MarketSettlementSourceResponse,
    MarketTradeResponse,
    MarketTradingShellResponse,
    resolve_market_history_range,
)
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
    MarketTemplateConfigResponse,
    MarketRequestResponse,
    MarketRequestUpdateRequest,
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
    PortfolioBalanceResponse,
    PortfolioPositionResponse,
    PortfolioSummaryResponse,
)
from app.services.oracle_service import (
    OracleConfigurationError,
    OracleResolutionRequest,
    OracleResolutionStatusRequest,
    OracleService,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_resolution_history_memory(
    *,
    current_resolution: MarketResolutionResponse | None,
    candidates: list[MarketResolutionCandidateResponse],
    disputes: list[MarketDisputeResponse],
) -> list[MarketResolutionEventResponse]:
    events: list[MarketResolutionEventResponse] = []
    if current_resolution is not None:
        events.append(
            MarketResolutionEventResponse(
                id=f"resolution:{current_resolution.id}",
                event_type="resolution_state",
                title="Oracle resolution active",
                status=current_resolution.status,
                occurred_at=current_resolution.resolved_at,
                reference_id=str(current_resolution.id),
                details={"candidate_id": str(current_resolution.candidate_id) if current_resolution.candidate_id else None},
            )
        )
    for candidate in candidates:
        events.append(
            MarketResolutionEventResponse(
                id=f"candidate:{candidate.id}",
                event_type="candidate_created",
                title="Resolution candidate proposed",
                status=candidate.status,
                occurred_at=candidate.proposed_at,
                actor_id=candidate.proposed_by,
                reference_id=str(candidate.id),
                details={
                    "provider": candidate.payload.get("provider"),
                    "assertion_id": candidate.payload.get("assertion_id"),
                    "source_reference_url": candidate.source_reference_url,
                },
            )
        )
        if candidate.reviewed_at is not None:
            events.append(
                MarketResolutionEventResponse(
                    id=f"candidate-review:{candidate.id}",
                    event_type="candidate_reviewed",
                    title="Resolution candidate reviewed",
                    status=candidate.status,
                    occurred_at=candidate.reviewed_at,
                    actor_id=candidate.reviewed_by,
                    reference_id=str(candidate.id),
                    details={},
                )
            )
    for dispute in disputes:
        events.append(
            MarketResolutionEventResponse(
                id=f"dispute:{dispute.id}",
                event_type="dispute_opened",
                title=dispute.title,
                status=dispute.status,
                occurred_at=dispute.opened_at,
                actor_id=dispute.raised_by,
                reference_id=str(dispute.id),
                details={"reason": dispute.reason},
            )
        )
        for evidence in dispute.evidence:
            events.append(
                MarketResolutionEventResponse(
                    id=f"evidence:{evidence.id}",
                    event_type="dispute_evidence_added",
                    title="Dispute evidence attached",
                    status=dispute.status,
                    occurred_at=evidence.created_at,
                    actor_id=evidence.submitted_by,
                    reference_id=str(evidence.id),
                    details={
                        "dispute_id": str(dispute.id),
                        "evidence_type": evidence.evidence_type,
                        "url": evidence.url,
                        "description": evidence.description,
                    },
                )
            )
        if dispute.closed_at is not None:
            events.append(
                MarketResolutionEventResponse(
                    id=f"dispute-review:{dispute.id}",
                    event_type="dispute_reviewed",
                    title="Dispute reviewed",
                    status=dispute.status,
                    occurred_at=dispute.closed_at,
                    actor_id=dispute.reviewed_by,
                    reference_id=str(dispute.id),
                    details={"review_notes": dispute.review_notes},
                )
            )
    return sorted(events, key=lambda item: item.occurred_at, reverse=True)


def _seed_profile() -> ProfileResponse:
    return ProfileResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        username="demo_admin",
        display_name="Demo Admin",
        bio="Local development actor",
        avatar_url=None,
        is_admin=True,
    )


class InMemoryProfileRepository(ProfileRepository):
    def __init__(self) -> None:
        self._profile = _seed_profile()
        self._wallets = [
            UserWalletResponse(
                id=UUID("10000000-0000-0000-0000-000000000001"),
                chain_name="polygon",
                wallet_address="0x0000000000000000000000000000000000000001",
                is_primary=True,
            )
        ]

    async def get_current_profile(self, actor_id: UUID, username: str, display_name: str, is_admin: bool) -> ProfileResponse:
        return self._profile.model_copy(
            update={
                "id": actor_id,
                "username": username,
                "display_name": display_name,
                "is_admin": is_admin,
            }
        )

    async def get_profile_by_username(self, username: str) -> ProfileResponse:
        if username != self._profile.username:
            raise NotFoundError("Profile not found")
        return self._profile.model_copy()

    async def update_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
        payload: ProfileUpdateRequest,
    ) -> ProfileResponse:
        self._profile = self._profile.model_copy(
            update={
                "id": actor_id,
                "username": username,
                "display_name": payload.display_name or display_name,
                "bio": payload.bio if payload.bio is not None else self._profile.bio,
                "avatar_url": payload.avatar_url if payload.avatar_url is not None else self._profile.avatar_url,
                "is_admin": is_admin,
            }
        )
        return self._profile.model_copy()

    async def list_wallets(self, actor_id: UUID) -> list[UserWalletResponse]:
        if actor_id != self._profile.id:
            return []
        return [wallet.model_copy() for wallet in self._wallets]

    async def create_wallet(self, actor_id: UUID, payload: WalletCreateRequest) -> UserWalletResponse:
        if any(wallet.wallet_address.lower() == payload.wallet_address.lower() for wallet in self._wallets):
            raise ConflictError("Wallet already exists")
        if payload.is_primary:
            self._wallets = [wallet.model_copy(update={"is_primary": False}) for wallet in self._wallets]
        wallet = UserWalletResponse(
            id=uuid4(),
            chain_name=payload.chain_name,
            wallet_address=payload.wallet_address,
            is_primary=payload.is_primary,
        )
        self._wallets.append(wallet)
        return wallet.model_copy()

    async def update_wallet(self, actor_id: UUID, wallet_id: UUID, payload: WalletUpdateRequest) -> UserWalletResponse:
        for index, wallet in enumerate(self._wallets):
            if wallet.id != wallet_id:
                continue
            if payload.is_primary:
                self._wallets = [item.model_copy(update={"is_primary": False}) for item in self._wallets]
            updated = wallet.model_copy(update={"is_primary": payload.is_primary})
            self._wallets[index] = updated
            return updated.model_copy()
        raise NotFoundError("Wallet not found")

    async def delete_wallet(self, actor_id: UUID, wallet_id: UUID) -> None:
        original_count = len(self._wallets)
        self._wallets = [wallet for wallet in self._wallets if wallet.id != wallet_id]
        if len(self._wallets) == original_count:
            raise NotFoundError("Wallet not found")


class InMemoryCommunityRepository(CommunityRepository):
    def __init__(self, owner_profile: ProfileResponse | None = None) -> None:
        owner_profile = owner_profile or _seed_profile()
        self._communities = {
            "aussie-politics": CommunityResponse(
                id=UUID("20000000-0000-0000-0000-000000000001"),
                slug="aussie-politics",
                name="Aussie Politics",
                description="Community scaffold for public election and policy markets.",
                visibility="public",
                require_post_approval=True,
                require_market_approval=True,
            ),
            "mates-club": CommunityResponse(
                id=UUID("20000000-0000-0000-0000-000000000002"),
                slug="mates-club",
                name="Mates Club",
                description="Private group scaffold for friend-only markets.",
                visibility="private",
                require_post_approval=True,
                require_market_approval=True,
            ),
        }
        self._members = {
            "aussie-politics": [
                CommunityMemberResponse(
                    id=UUID("30000000-0000-0000-0000-000000000001"),
                    profile_id=owner_profile.id,
                    username=owner_profile.username,
                    display_name=owner_profile.display_name,
                    role="owner",
                )
            ],
            "mates-club": [
                CommunityMemberResponse(
                    id=UUID("30000000-0000-0000-0000-000000000002"),
                    profile_id=owner_profile.id,
                    username=owner_profile.username,
                    display_name=owner_profile.display_name,
                    role="owner",
                )
            ],
        }
        self._community_creators = {
            "aussie-politics": owner_profile.id,
            "mates-club": owner_profile.id,
        }

    async def list_communities(self, actor_id: UUID, actor_is_admin: bool) -> list[CommunityResponse]:
        if actor_is_admin:
            return [community.model_copy() for community in self._communities.values()]
        visible: list[CommunityResponse] = []
        for slug, community in self._communities.items():
            if community.visibility == "public" or self._community_creators.get(slug) == actor_id or self._find_member(slug, actor_id):
                visible.append(community.model_copy())
        return visible

    async def create_community(self, actor_id: UUID, payload: CommunityCreateRequest) -> CommunityResponse:
        if payload.slug in self._communities:
            raise ConflictError("Community slug already exists")
        community = CommunityResponse(
            id=uuid4(),
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            visibility=payload.visibility,
            require_post_approval=payload.require_post_approval,
            require_market_approval=payload.require_market_approval,
        )
        self._communities[community.slug] = community
        self._community_creators[community.slug] = actor_id
        self._members[community.slug] = [
            CommunityMemberResponse(
                id=uuid4(),
                profile_id=actor_id,
                username="current_user",
                display_name="Current User",
                role="owner",
            )
        ]
        return community.model_copy()

    async def get_community(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> CommunityResponse:
        return self._get_accessible_community(slug, actor_id, actor_is_admin).model_copy()

    async def update_community(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityUpdateRequest,
    ) -> CommunityResponse:
        community = self._get_accessible_community(slug, actor_id, actor_is_admin)
        if not self._is_staff(slug, actor_id, actor_is_admin):
            raise ForbiddenError("You do not have permission to update this community")
        updated = community.model_copy(
            update={
                "name": payload.name or community.name,
                "description": payload.description if payload.description is not None else community.description,
                "visibility": payload.visibility or community.visibility,
                "require_post_approval": (
                    payload.require_post_approval
                    if payload.require_post_approval is not None
                    else community.require_post_approval
                ),
                "require_market_approval": (
                    payload.require_market_approval
                    if payload.require_market_approval is not None
                    else community.require_market_approval
                ),
            }
        )
        self._communities[slug] = updated
        return updated.model_copy()

    async def list_members(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> list[CommunityMemberResponse]:
        self._get_accessible_community(slug, actor_id, actor_is_admin)
        members = self._members.get(slug)
        return [member.model_copy() for member in members]

    async def add_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityMemberCreateRequest,
    ) -> CommunityMemberResponse:
        community = self._get_accessible_community(slug, actor_id, actor_is_admin)
        if not (
            self._is_staff(slug, actor_id, actor_is_admin)
            or actor_is_admin
            or (payload.profile_id == actor_id and community.visibility == "public")
        ):
            raise ForbiddenError("You do not have permission to add members to this community")
        members = self._members.get(slug)
        member = CommunityMemberResponse(
            id=uuid4(),
            profile_id=payload.profile_id,
            username="pending_user",
            display_name="Pending User",
            role=payload.role,
        )
        members.append(member)
        return member.model_copy()

    async def update_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        member_id: UUID,
        payload: CommunityMemberUpdateRequest,
    ) -> CommunityMemberResponse:
        if not self._is_staff(slug, actor_id, actor_is_admin):
            raise ForbiddenError("You do not have permission to update community members")
        members = self._members.get(slug)
        if members is None:
            raise NotFoundError("Community not found")
        for index, member in enumerate(members):
            if member.id != member_id:
                continue
            updated = member.model_copy(update={"role": payload.role})
            members[index] = updated
            return updated.model_copy()
        raise NotFoundError("Member not found")

    async def delete_member(self, slug: str, actor_id: UUID, actor_is_admin: bool, member_id: UUID) -> None:
        if not self._is_staff(slug, actor_id, actor_is_admin):
            raise ForbiddenError("You do not have permission to remove community members")
        members = self._members.get(slug)
        if members is None:
            raise NotFoundError("Community not found")
        original_count = len(members)
        self._members[slug] = [member for member in members if member.id != member_id]
        if len(self._members[slug]) == original_count:
            raise NotFoundError("Member not found")

    def _get_accessible_community(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> CommunityResponse:
        community = self._communities.get(slug)
        if community is None:
            raise NotFoundError("Community not found")
        if actor_is_admin or community.visibility == "public" or self._community_creators.get(slug) == actor_id or self._find_member(slug, actor_id):
            return community
        raise ForbiddenError("You do not have access to this community")

    def _find_member(self, slug: str, actor_id: UUID) -> CommunityMemberResponse | None:
        members = self._members.get(slug, [])
        for member in members:
            if member.profile_id == actor_id:
                return member
        return None

    def _is_staff(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> bool:
        if actor_is_admin or self._community_creators.get(slug) == actor_id:
            return True
        member = self._find_member(slug, actor_id)
        return member is not None and member.role in {"moderator", "admin", "owner"}

class InMemoryPostRepository(PostRepository):
    def __init__(self) -> None:
        created_at = _utcnow()
        self._posts = {
            UUID("50000000-0000-0000-0000-000000000001"): PostResponse(
                id=UUID("50000000-0000-0000-0000-000000000001"),
                community_id=UUID("20000000-0000-0000-0000-000000000001"),
                community_slug="aussie-politics",
                community_name="Aussie Politics",
                author_id=UUID("00000000-0000-0000-0000-000000000001"),
                author_username="demo_admin",
                author_display_name="Demo Admin",
                title="Election desk is live",
                body="Post moderation scaffold is ready for the community feed.",
                status="approved",
                submitted_at=created_at,
                reviewed_at=created_at,
                reviewed_by=UUID("00000000-0000-0000-0000-000000000001"),
                review_notes=None,
                created_at=created_at,
                updated_at=created_at,
            )
        }
        self._community_index = {
            "aussie-politics": UUID("20000000-0000-0000-0000-000000000001"),
            "mates-club": UUID("20000000-0000-0000-0000-000000000002"),
        }
        self._community_rules = {
            "aussie-politics": {"name": "Aussie Politics", "require_post_approval": True, "visibility": "public"},
            "mates-club": {"name": "Mates Club", "require_post_approval": True, "visibility": "private"},
        }
        self._community_members = {
            "aussie-politics": {UUID("00000000-0000-0000-0000-000000000001"): "owner"},
            "mates-club": {UUID("00000000-0000-0000-0000-000000000001"): "owner"},
        }
        self._community_creators = {
            "aussie-politics": UUID("00000000-0000-0000-0000-000000000001"),
            "mates-club": UUID("00000000-0000-0000-0000-000000000001"),
        }

    async def list_posts(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> list[PostResponse]:
        context = self._get_community_context(community_slug, actor_id, actor_is_admin)
        posts = [post.model_copy() for post in self._posts.values() if post.community_slug == community_slug]
        if context["is_staff"]:
            return sorted(posts, key=lambda post: post.created_at, reverse=True)
        visible = [post for post in posts if post.status == "approved" or post.author_id == actor_id]
        return sorted(visible, key=lambda post: post.created_at, reverse=True)

    async def create_post(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: PostCreateRequest,
    ) -> PostResponse:
        context = self._get_community_context(community_slug, actor_id, actor_is_admin)
        created_at = _utcnow()
        auto_approved = not context["require_post_approval"] or context["is_staff"]
        post = PostResponse(
            id=uuid4(),
            community_id=context["community_id"],
            community_slug=community_slug,
            community_name=context["community_name"],
            author_id=actor_id,
            author_username="current_user",
            author_display_name="Current User",
            title=payload.title,
            body=payload.body,
            status="approved" if auto_approved else "pending_review",
            submitted_at=created_at,
            reviewed_at=created_at if context["require_post_approval"] and context["is_staff"] else None,
            reviewed_by=actor_id if context["require_post_approval"] and context["is_staff"] else None,
            review_notes=None,
            created_at=created_at,
            updated_at=created_at,
        )
        self._posts[post.id] = post
        return post.model_copy()

    async def list_pending_posts(self) -> list[PostResponse]:
        return [
            post.model_copy()
            for post in sorted(self._posts.values(), key=lambda item: item.created_at, reverse=True)
            if post.status == "pending_review"
        ]

    async def review_post(
        self,
        post_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> PostResponse:
        post = self._posts.get(post_id)
        if post is None:
            raise NotFoundError("Post not found")
        if post.status != "pending_review":
            raise ConflictError("Only pending posts can be reviewed")
        updated = post.model_copy(
            update={
                "status": "approved" if approved else "rejected",
                "reviewed_at": _utcnow(),
                "reviewed_by": reviewer_id,
                "review_notes": review_notes,
                "updated_at": _utcnow(),
            }
        )
        self._posts[post_id] = updated
        return updated.model_copy()

    def _get_community_context(self, community_slug: str, actor_id: UUID, actor_is_admin: bool) -> dict[str, object]:
        community_id = self._community_index.get(community_slug)
        rules = self._community_rules.get(community_slug)
        if community_id is None or rules is None:
            raise NotFoundError("Community not found")
        member_role = self._community_members.get(community_slug, {}).get(actor_id)
        can_read = actor_is_admin or rules["visibility"] == "public" or self._community_creators.get(community_slug) == actor_id or member_role is not None
        if not can_read:
            raise ForbiddenError("You do not have access to this community")
        return {
            "community_id": community_id,
            "community_name": rules["name"],
            "require_post_approval": rules["require_post_approval"],
            "is_staff": actor_is_admin or self._community_creators.get(community_slug) == actor_id or member_role in {"moderator", "admin", "owner"},
        }


class InMemoryMarketRequestRepository(MarketRequestRepository):
    def __init__(self) -> None:
        created_at = _utcnow()
        market_request = MarketRequestResponse(
            id=UUID("40000000-0000-0000-0000-000000000001"),
            requester_id=UUID("00000000-0000-0000-0000-000000000001"),
            requester_username="demo_admin",
            requester_display_name="Demo Admin",
            community_id=UUID("20000000-0000-0000-0000-000000000001"),
            community_slug="aussie-politics",
            community_name="Aussie Politics",
            title="Will the RBA cut rates in Q3?",
            slug="rba-rate-cut-q3",
            question="Will the RBA cut the cash rate before the end of Q3?",
            description="Local API scaffold draft.",
            template_key=None,
            template_config=None,
            market_access_mode="public",
            requested_rail="custodial",
            resolution_mode="api",
            settlement_reference_url=None,
            status="draft",
            review_notes=None,
            submitted_at=None,
            reviewed_at=None,
            created_at=created_at,
            updated_at=created_at,
        )
        self._requests = {market_request.id: market_request}
        self._answers = {
            market_request.id: {
                "market_category": MarketRequestAnswerResponse(
                    question_key="market_category",
                    question_label="Market category",
                    answer_text="Macro",
                    answer_json=None,
                ),
                "why_now": MarketRequestAnswerResponse(
                    question_key="why_now",
                    question_label="Why should this market exist now?",
                    answer_text="There is a real decision date and an official source.",
                    answer_json=None,
                ),
            }
        }

    async def list_requests(self, requester_id: UUID) -> list[MarketRequestResponse]:
        return [request.model_copy() for request in self._requests.values() if request.requester_id == requester_id]

    async def list_pending_requests(self) -> list[MarketRequestResponse]:
        return [
            request.model_copy()
            for request in self._requests.values()
            if request.status in {"submitted", "approved"}
        ]

    async def create_request(self, requester_id: UUID, payload: MarketRequestCreateRequest) -> MarketRequestResponse:
        if payload.slug and any(item.slug == payload.slug for item in self._requests.values()):
            raise ConflictError("Market request slug already exists")
        created_at = _utcnow()
        request = MarketRequestResponse(
            id=uuid4(),
            requester_id=requester_id,
            requester_username="current_user",
            requester_display_name="Current User",
            community_id=payload.community_id,
            community_slug=None,
            community_name=None,
            title=payload.title,
            slug=payload.slug,
            question=payload.question,
            description=payload.description,
            template_key=payload.template_key,
            template_config=payload.template_config,
            market_access_mode=payload.market_access_mode,
            requested_rail=payload.requested_rail,
            resolution_mode=payload.resolution_mode,
            settlement_reference_url=payload.settlement_reference_url,
            status="draft",
            review_notes=None,
            submitted_at=None,
            reviewed_at=None,
            created_at=created_at,
            updated_at=created_at,
        )
        self._requests[request.id] = request
        self._answers[request.id] = {}
        return request.model_copy()

    async def get_request(self, request_id: UUID, requester_id: UUID | None = None) -> MarketRequestResponse:
        request = self._requests.get(request_id)
        if request is None:
            raise NotFoundError("Market request not found")
        if requester_id is not None and request.requester_id != requester_id:
            raise NotFoundError("Market request not found")
        return request.model_copy()

    async def update_request(
        self,
        request_id: UUID,
        requester_id: UUID,
        payload: MarketRequestUpdateRequest,
    ) -> MarketRequestResponse:
        request = self._requests.get(request_id)
        if request is None or request.requester_id != requester_id:
            raise NotFoundError("Market request not found")
        if request.status != "draft":
            raise ConflictError("Only draft market requests can be updated")
        updated = request.model_copy(
            update={
                "title": payload.title or request.title,
                "question": payload.question or request.question,
                "description": payload.description if payload.description is not None else request.description,
                "settlement_reference_url": (
                    payload.settlement_reference_url
                    if payload.settlement_reference_url is not None
                    else request.settlement_reference_url
                ),
                "updated_at": _utcnow(),
            }
        )
        self._requests[request_id] = updated
        return updated.model_copy()

    async def upsert_answer(
        self,
        request_id: UUID,
        requester_id: UUID,
        question_key: str,
        payload: MarketRequestAnswerUpsertRequest,
    ) -> MarketRequestAnswerResponse:
        request = self._requests.get(request_id)
        if request is None or request.requester_id != requester_id:
            raise NotFoundError("Market request not found")
        if request.status != "draft":
            raise ConflictError("Only draft market requests can be edited")
        answer = MarketRequestAnswerResponse(
            question_key=question_key,
            question_label=payload.question_label,
            answer_text=payload.answer_text,
            answer_json=deepcopy(payload.answer_json),
        )
        self._answers.setdefault(request_id, {})[question_key] = answer
        return answer.model_copy()

    async def ensure_exists(self, request_id: UUID, requester_id: UUID | None = None) -> None:
        request = self._requests.get(request_id)
        if request is None or (requester_id is not None and request.requester_id != requester_id):
            raise NotFoundError("Market request not found")

    async def list_answers(
        self,
        request_id: UUID,
        requester_id: UUID | None = None,
    ) -> list[MarketRequestAnswerResponse]:
        await self.ensure_exists(request_id, requester_id)
        answers = self._answers.get(request_id, {})
        return [answer.model_copy() for answer in answers.values()]

    async def submit_request(
        self,
        request_id: UUID,
        requester_id: UUID,
    ) -> MarketRequestResponse:
        request = self._requests.get(request_id)
        if request is None or request.requester_id != requester_id:
            raise NotFoundError("Market request not found")
        if request.status != "draft":
            raise ConflictError("Only draft market requests can be submitted")
        updated = request.model_copy(update={"status": "submitted", "submitted_at": _utcnow(), "updated_at": _utcnow()})
        self._requests[request_id] = updated
        return updated.model_copy()

    async def review_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> MarketRequestResponse:
        request = self._requests.get(request_id)
        if request is None:
            raise NotFoundError("Market request not found")
        if request.status != "submitted":
            raise ConflictError("Only submitted market requests can be reviewed")
        updated = request.model_copy(
            update={
                "status": "approved" if approved else "rejected",
                "review_notes": review_notes,
                "reviewed_at": _utcnow(),
                "updated_at": _utcnow(),
            }
        )
        self._requests[request_id] = updated
        return updated.model_copy()


class InMemoryMarketRepository(MarketRepository):
    def __init__(
        self,
        market_request_repository: InMemoryMarketRequestRepository | None = None,
        market_data_service: MarketDataService | None = None,
        oracle_service: OracleService | None = None,
    ) -> None:
        self._markets: dict[str, MarketResponse] = {}
        self._market_request_repository = market_request_repository
        self._trading_repository: InMemoryTradingRepository | None = None
        self._market_data_service = market_data_service
        self._oracle_service = oracle_service
        self._resolutions: dict[UUID, MarketResolutionResponse] = {}
        self._resolution_candidates: dict[UUID, list[MarketResolutionCandidateResponse]] = {}
        self._disputes: dict[UUID, list[MarketDisputeResponse]] = {}
        self._dispute_evidence: dict[UUID, list[MarketDisputeEvidenceResponse]] = {}

    async def publish_from_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        review_notes: str | None,
    ) -> MarketResponse:
        if self._market_request_repository is not None:
            request = self._market_request_repository._requests.get(request_id)
            if request is None:
                raise NotFoundError("Market request not found")
            if request.status not in {"submitted", "approved"}:
                raise ConflictError("Only submitted or approved market requests can be published")
            self._market_request_repository._requests[request_id] = request.model_copy(
                update={
                    "status": "converted",
                    "review_notes": review_notes,
                    "reviewed_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
            request_answers = self._market_request_repository._answers.get(request_id, {})
            template_contract_metadata = build_contract_metadata_from_template(
                request.template_key if request else None,
                request.template_config.model_dump(mode="json") if request and request.template_config else None,
            )
            get_answer = lambda key: request_answers.get(key).answer_text if request_answers.get(key) else None
            explicit_overrides = {
                "reference_label": get_answer("reference_label"),
                "reference_source_label": get_answer("reference_source_label") or get_answer("settlement_source"),
                "price_to_beat": get_answer("price_to_beat"),
                "reference_price": get_answer("reference_price"),
                "reference_asset": get_answer("reference_asset"),
                "category": get_answer("category") or get_answer("market_category"),
                "subcategory": get_answer("subcategory"),
                "notes": get_answer("contract_notes"),
            }
            snapshot_metadata: dict[str, object] = {}
            if self._market_data_service is not None:
                snapshot = await self._market_data_service.get_reference_snapshot(
                    template_key=request.template_key if request else None,
                    template_config=request.template_config.model_dump(mode="json")
                    if request and request.template_config
                    else None,
                    contract_metadata=template_contract_metadata,
                )
                if snapshot is not None:
                    snapshot_metadata = snapshot.as_contract_metadata()
                    if request and request.settlement_reference_url is None and snapshot.source_reference_url:
                        request = request.model_copy(update={"settlement_reference_url": snapshot.source_reference_url})
            contract_metadata = {
                **template_contract_metadata,
                **snapshot_metadata,
                **{key: value for key, value in explicit_overrides.items() if value},
            }
        else:
            contract_metadata = {"contract_type": "binary"}
            request = None
        created_at = _utcnow()
        slug = normalize_slug(
            request.slug if request else None,
            fallback=request.title if request else f"market-{str(request_id).split('-')[0]}",
        ) or f"market-{str(request_id).split('-')[0]}"
        market = MarketResponse(
            id=uuid4(),
            slug=slug,
            title=request.title if request else "Published Market",
            question=request.question if request else "Published market question",
            description=request.description if request else "Converted from a market request in memory mode.",
            status="pending_liquidity",
            market_access_mode=request.market_access_mode if request else "public",
            rail_mode=request.requested_rail if request and request.requested_rail else "onchain",
            resolution_mode=request.resolution_mode if request else "oracle",
            rules_text=review_notes or "Official source resolves the winning outcome.",
            community_id=request.community_id if request else None,
            community_slug=request.community_slug if request else None,
            community_name=request.community_name if request else None,
            created_from_request_id=request_id,
            creator_id=request.requester_id if request else reviewer_id,
            settlement_source_id=UUID("60000000-0000-0000-0000-000000000001"),
            settlement_reference_url=request.settlement_reference_url if request else None,
            settlement_reference_label="Demo oracle",
            settlement_source=MarketSettlementSourceResponse(
                id=UUID("60000000-0000-0000-0000-000000000001"),
                code="demo_oracle",
                name="Demo oracle",
                resolution_mode="oracle",
                base_url="https://example.com/oracle",
            ),
            timing=MarketContractTimesResponse(trading_opens_at=created_at),
            reference_context=MarketReferenceContextResponse(
                contract_type=str(contract_metadata.get("contract_type", "binary")),
                category=str(contract_metadata["category"]) if contract_metadata.get("category") else "trending",
                subcategory=str(contract_metadata["subcategory"]) if contract_metadata.get("subcategory") else None,
                reference_label=str(contract_metadata["reference_label"]) if contract_metadata.get("reference_label") else None,
                reference_source_label=str(contract_metadata["reference_source_label"])
                if contract_metadata.get("reference_source_label")
                else None,
                reference_asset=str(contract_metadata["reference_asset"]) if contract_metadata.get("reference_asset") else None,
                reference_symbol=str(contract_metadata["reference_symbol"]) if contract_metadata.get("reference_symbol") else None,
                reference_price=str(contract_metadata["reference_price"]) if contract_metadata.get("reference_price") else None,
                price_to_beat=str(contract_metadata["price_to_beat"]) if contract_metadata.get("price_to_beat") else None,
                reference_timestamp=(
                    datetime.fromisoformat(str(contract_metadata["reference_timestamp"]).replace("Z", "+00:00"))
                    if contract_metadata.get("reference_timestamp")
                    else None
                ),
                notes=str(contract_metadata["notes"]) if contract_metadata.get("notes") else None,
            ),
            min_seed_amount="0",
            min_liquidity_amount="0",
            min_participants=2,
            creator_fee_bps=0,
            platform_fee_bps=0,
            total_volume="0",
            total_trades_count=0,
            created_at=created_at,
            updated_at=created_at,
            outcomes=[
                MarketOutcomeResponse(
                    id=uuid4(),
                    code="YES",
                    label="Yes",
                    outcome_index=0,
                    status="active",
                    settlement_value=None,
                ),
                MarketOutcomeResponse(
                    id=uuid4(),
                    code="NO",
                    label="No",
                    outcome_index=1,
                    status="active",
                    settlement_value=None,
                ),
            ],
        )
        self._markets[slug] = market
        return market.model_copy()

    async def list_markets(self) -> list[MarketResponse]:
        return [market.model_copy() for market in self._markets.values()]

    async def get_market(self, slug: str) -> MarketResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        return market.model_copy()

    async def update_market_status(self, slug: str, status: str) -> MarketResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        allowed_next_statuses = {
            "pending_liquidity": {"open", "cancelled"},
            "open": {"trading_paused", "cancelled"},
            "trading_paused": {"open", "cancelled"},
        }
        if status not in allowed_next_statuses.get(market.status, set()):
            raise ConflictError(f"Cannot transition market from {market.status} to {status}")
        updated = market.model_copy(update={"status": status, "updated_at": _utcnow()})
        self._markets[slug] = updated
        return updated.model_copy()

    async def get_market_resolution_state(self, slug: str) -> MarketResolutionStateResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        current_resolution = self._resolutions.get(market.id)
        candidates = [candidate.model_copy() for candidate in self._resolution_candidates.get(market.id, [])]
        disputes = [
            dispute.model_copy(update={"evidence": [item.model_copy() for item in self._dispute_evidence.get(dispute.id, [])]})
            for dispute in self._disputes.get(market.id, [])
        ]
        current_candidate = next(
            (candidate for candidate in candidates if candidate.id == (current_resolution.candidate_id if current_resolution else None)),
            candidates[0] if candidates else None,
        )
        current_payload: dict[str, object] = dict(current_candidate.payload) if current_candidate is not None else {}
        if current_resolution is not None:
            current_payload["status"] = current_resolution.status
            if current_resolution.candidate_id:
                current_payload["candidate_id"] = str(current_resolution.candidate_id)
        if disputes:
            current_payload["latest_dispute_id"] = str(disputes[0].id)
            current_payload["dispute_review_state"] = disputes[0].status
        return MarketResolutionStateResponse(
            market_id=market.id,
            market_slug=market.slug,
            current_resolution_id=current_resolution.id if current_resolution else None,
            current_status=current_resolution.status if current_resolution else None,
            current_payload=current_payload,
            candidate_id=current_resolution.candidate_id if current_resolution else None,
            winning_outcome_id=current_resolution.winning_outcome_id if current_resolution else None,
            source_reference_url=current_resolution.source_reference_url if current_resolution else None,
            finalizes_at=current_resolution.finalizes_at if current_resolution else None,
            resolved_at=current_resolution.resolved_at if current_resolution else None,
            candidates=candidates,
            disputes=disputes,
            history=_build_resolution_history_memory(
                current_resolution=current_resolution,
                candidates=candidates,
                disputes=disputes,
            ),
        )

    async def create_market_dispute(
        self,
        slug: str,
        actor_id: UUID,
        payload: MarketDisputeCreateRequest,
    ) -> MarketDisputeResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        if market.status not in {"awaiting_resolution", "disputed"}:
            raise ConflictError("Disputes can only be raised while oracle resolution is pending")

        current_resolution = self._resolutions.get(market.id)
        if current_resolution is None:
            raise ConflictError("No active resolution candidate exists for this market")
        if any(dispute.status in {"open", "under_review"} for dispute in self._disputes.get(market.id, [])):
            raise ConflictError("An open dispute already exists for the active resolution candidate")

        dispute = MarketDisputeResponse(
            id=uuid4(),
            market_id=market.id,
            resolution_id=current_resolution.id,
            raised_by=actor_id,
            status="open",
            title=payload.title,
            reason=payload.reason,
            fee_amount="0",
            opened_at=_utcnow(),
            closed_at=None,
            reviewed_by=None,
            review_notes=None,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self._disputes.setdefault(market.id, []).insert(0, dispute)
        self._dispute_evidence.setdefault(dispute.id, [])
        self._markets[slug] = market.model_copy(update={"status": "disputed", "updated_at": _utcnow()})
        self._resolutions[market.id] = current_resolution.model_copy(update={"status": "disputed"})
        next_candidates: list[MarketResolutionCandidateResponse] = []
        for candidate in self._resolution_candidates.get(market.id, []):
            if candidate.id == current_resolution.candidate_id:
                next_candidates.append(
                    candidate.model_copy(update={"status": "rejected", "reviewed_at": _utcnow(), "reviewed_by": actor_id})
                )
            else:
                next_candidates.append(candidate)
        self._resolution_candidates[market.id] = next_candidates
        return dispute.model_copy()

    async def add_market_dispute_evidence(
        self,
        slug: str,
        dispute_id: UUID,
        actor_id: UUID,
        payload: MarketDisputeEvidenceCreateRequest,
    ) -> MarketDisputeResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        dispute_index = next(
            (index for index, dispute in enumerate(self._disputes.get(market.id, [])) if dispute.id == dispute_id),
            None,
        )
        if dispute_index is None:
            raise NotFoundError("Dispute not found")
        dispute = self._disputes[market.id][dispute_index]
        if dispute.status not in {"open", "under_review"}:
            raise ConflictError("Evidence can only be attached while a dispute is open or under review")
        evidence = MarketDisputeEvidenceResponse(
            id=uuid4(),
            dispute_id=dispute_id,
            submitted_by=actor_id,
            evidence_type=payload.evidence_type,
            url=payload.url,
            description=payload.description,
            payload=payload.payload,
            created_at=_utcnow(),
        )
        self._dispute_evidence.setdefault(dispute_id, []).append(evidence)
        updated_dispute = dispute.model_copy(
            update={
                "updated_at": _utcnow(),
                "evidence": [item.model_copy() for item in self._dispute_evidence[dispute_id]],
            }
        )
        self._disputes[market.id][dispute_index] = updated_dispute
        return updated_dispute.model_copy()

    async def review_market_dispute(
        self,
        slug: str,
        dispute_id: UUID,
        payload: MarketDisputeReviewRequest,
    ) -> MarketDisputeResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        dispute_index = next(
            (index for index, dispute in enumerate(self._disputes.get(market.id, [])) if dispute.id == dispute_id),
            None,
        )
        if dispute_index is None:
            raise NotFoundError("Dispute not found")
        dispute = self._disputes[market.id][dispute_index]
        if dispute.status in {"dismissed", "upheld", "withdrawn"}:
            raise ConflictError("This dispute has already been closed")

        current_resolution = self._resolutions.get(market.id)
        update_values = {
            "status": payload.status,
            "review_notes": payload.review_notes,
            "updated_at": _utcnow(),
            "evidence": [item.model_copy() for item in self._dispute_evidence.get(dispute_id, [])],
        }
        if payload.status in {"dismissed", "upheld", "withdrawn"}:
            update_values["closed_at"] = _utcnow()
        updated_dispute = dispute.model_copy(update=update_values)
        self._disputes[market.id][dispute_index] = updated_dispute

        if payload.status == "under_review":
            self._markets[slug] = market.model_copy(update={"status": "disputed", "updated_at": _utcnow()})
            if current_resolution is not None:
                self._resolutions[market.id] = current_resolution.model_copy(update={"status": "disputed"})
        elif payload.status in {"dismissed", "withdrawn"}:
            self._markets[slug] = market.model_copy(update={"status": "awaiting_resolution", "updated_at": _utcnow()})
            if current_resolution is not None:
                self._resolutions[market.id] = current_resolution.model_copy(update={"status": "pending_oracle"})
            next_candidates: list[MarketResolutionCandidateResponse] = []
            for candidate in self._resolution_candidates.get(market.id, []):
                if candidate.id == (current_resolution.candidate_id if current_resolution else None):
                    next_candidates.append(candidate.model_copy(update={"status": "proposed", "reviewed_at": None, "reviewed_by": None}))
                else:
                    next_candidates.append(candidate)
            self._resolution_candidates[market.id] = next_candidates
        elif payload.status == "upheld":
            self._markets[slug] = market.model_copy(update={"status": "disputed", "updated_at": _utcnow()})
            if current_resolution is not None:
                self._resolutions[market.id] = current_resolution.model_copy(update={"status": "disputed"})

        return updated_dispute.model_copy()

    async def request_settlement(
        self,
        slug: str,
        requester_id: UUID,
        payload: MarketSettlementRequestCreateRequest,
    ) -> MarketResolutionResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        if market.status in {"settled", "cancelled", "awaiting_resolution", "disputed"}:
            raise ConflictError(f"Cannot request oracle settlement in status {market.status}")
        finalizes_at = _utcnow() + timedelta(minutes=settings.oracle_liveness_minutes)
        candidate_id = uuid4()
        oracle_payload = {}
        if self._oracle_service is not None:
            try:
                oracle_payload = await self._oracle_service.begin_resolution(
                    OracleResolutionRequest(
                        market_id=market.id,
                        market_slug=slug,
                        candidate_id=candidate_id,
                        resolution_mode=market.resolution_mode,
                        source_reference_url=payload.source_reference_url or market.settlement_reference_url,
                        notes=payload.notes,
                        finalizes_at=finalizes_at,
                    )
                )
            except OracleConfigurationError as exc:
                raise ConflictError(str(exc)) from exc
        updated_market = market.model_copy(
            update={
                "status": "awaiting_resolution",
                "timing": market.timing.model_copy(
                    update={
                        "resolution_due_at": finalizes_at,
                        "dispute_window_ends_at": finalizes_at,
                    }
                ),
                "updated_at": _utcnow(),
            }
        )
        self._markets[slug] = updated_market
        candidate = MarketResolutionCandidateResponse(
            id=candidate_id,
            market_id=market.id,
            proposed_outcome_id=None,
            proposed_by=requester_id,
            settlement_source_id=market.settlement_source_id,
            status="proposed",
            source_reference_url=payload.source_reference_url or market.settlement_reference_url,
            source_reference_text=payload.notes,
            payload={
                "status": "pending_oracle",
                "notes": payload.notes or "",
                "requested_by": str(requester_id),
                **oracle_payload,
            },
            proposed_at=_utcnow(),
            reviewed_at=None,
            reviewed_by=None,
        )
        self._resolution_candidates.setdefault(market.id, []).insert(0, candidate)
        resolution = MarketResolutionResponse(
            id=uuid4(),
            market_id=market.id,
            winning_outcome_id=None,
            candidate_id=candidate_id,
            status="pending_oracle",
            resolution_mode=market.resolution_mode,
            settlement_source_id=market.settlement_source_id,
            source_reference_url=payload.source_reference_url or market.settlement_reference_url,
            finalizes_at=finalizes_at,
            resolved_at=_utcnow(),
        )
        self._resolutions[market.id] = resolution
        return resolution

    async def reconcile_oracle_resolution(self, slug: str) -> MarketResolutionStateResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        current_resolution = self._resolutions.get(market.id)
        if current_resolution is None or current_resolution.candidate_id is None:
            raise ConflictError("No oracle resolution candidate is pending for this market")
        current_candidate = next(
            (candidate for candidate in self._resolution_candidates.get(market.id, []) if candidate.id == current_resolution.candidate_id),
            None,
        )
        if current_candidate is None:
            raise ConflictError("The active oracle candidate could not be found")

        current_payload: dict[str, object] = {}
        current_payload.update(current_candidate.payload)
        current_payload["status"] = current_resolution.status
        current_payload["candidate_id"] = str(current_resolution.candidate_id)

        if self._oracle_service is None:
            raise ConflictError("Oracle reconciliation is not configured for this environment")
        try:
            reconciled_payload = await self._oracle_service.reconcile_resolution(
                OracleResolutionStatusRequest(
                    market_id=market.id,
                    market_slug=slug,
                    candidate_id=current_candidate.id,
                    current_payload=current_payload,
                )
            )
        except OracleConfigurationError as exc:
            raise ConflictError(str(exc)) from exc

        self._resolution_candidates[market.id] = [
            candidate.model_copy(update={"payload": reconciled_payload})
            if candidate.id == current_candidate.id
            else candidate
            for candidate in self._resolution_candidates.get(market.id, [])
        ]
        return await self.get_market_resolution_state(slug)

    async def settle_market(
        self,
        slug: str,
        reviewer_id: UUID | None,
        payload: MarketSettlementFinalizeRequest,
    ) -> MarketResolutionResponse:
        market = self._markets.get(slug)
        if market is None:
            raise NotFoundError("Market not found")
        if market.status not in {"awaiting_resolution", "disputed"}:
            raise ConflictError("Market is not awaiting oracle finalization")
        if any(dispute.status in {"open", "under_review"} for dispute in self._disputes.get(market.id, [])):
            raise ConflictError("Cannot finalize while an active dispute is still open")
        winning_found = False
        next_outcomes: list[MarketOutcomeResponse] = []
        for outcome in market.outcomes:
            if outcome.id == payload.winning_outcome_id:
                winning_found = True
                next_outcomes.append(
                    outcome.model_copy(update={"status": "winning", "settlement_value": "1"})
                )
            else:
                next_outcomes.append(
                    outcome.model_copy(update={"status": "losing", "settlement_value": "0"})
                )
        if not winning_found:
            raise NotFoundError("Winning outcome not found")
        updated = market.model_copy(
            update={
                "status": "settled",
                "outcomes": next_outcomes,
                "timing": market.timing.model_copy(update={"settled_at": _utcnow()}),
                "updated_at": _utcnow(),
            }
        )
        self._markets[slug] = updated
        if self._trading_repository is not None:
            self._trading_repository.cancel_orders_for_market(market.id)
        prior_resolution = self._resolutions.get(market.id)
        if payload.candidate_id:
            next_candidates: list[MarketResolutionCandidateResponse] = []
            for candidate in self._resolution_candidates.get(market.id, []):
                if candidate.id == payload.candidate_id:
                    next_candidates.append(
                        candidate.model_copy(
                            update={
                                "proposed_outcome_id": payload.winning_outcome_id,
                                "status": "confirmed",
                                "source_reference_url": payload.source_reference_url or candidate.source_reference_url,
                                "source_reference_text": payload.notes or candidate.source_reference_text,
                                "reviewed_at": _utcnow(),
                                "reviewed_by": reviewer_id,
                                "payload": {
                                    **candidate.payload,
                                    "status": "finalized",
                                    "notes": payload.notes or "",
                                    "winning_outcome_id": str(payload.winning_outcome_id),
                                },
                            }
                        )
                    )
                else:
                    next_candidates.append(candidate)
            self._resolution_candidates[market.id] = next_candidates
        resolution = MarketResolutionResponse(
            id=prior_resolution.id if prior_resolution else uuid4(),
            market_id=market.id,
            winning_outcome_id=payload.winning_outcome_id,
            candidate_id=payload.candidate_id or (prior_resolution.candidate_id if prior_resolution else None),
            status="finalized",
            resolution_mode=market.resolution_mode,
            settlement_source_id=market.settlement_source_id,
            source_reference_url=payload.source_reference_url or market.settlement_reference_url,
            finalizes_at=prior_resolution.finalizes_at if prior_resolution else None,
            resolved_at=_utcnow(),
        )
        self._resolutions[market.id] = resolution
        return resolution

    def find_market_by_id(self, market_id: UUID) -> MarketResponse | None:
        for market in self._markets.values():
            if market.id == market_id:
                return market
        return None


class InMemoryTradingRepository(TradingRepository):
    def __init__(self, market_repository: InMemoryMarketRepository) -> None:
        self._market_repository = market_repository
        self._market_repository._trading_repository = self
        self._orders: list[MarketOrderResponse] = []
        self._order_owners: dict[UUID, UUID] = {}
        self._trades: list[MarketTradeResponse] = []
        self._balances: dict[tuple[UUID, str, str], Decimal] = {}

    async def get_market_trading_shell(self, slug: str) -> MarketTradingShellResponse:
        market = await self._market_repository.get_market(slug)
        quotes = [self._build_quote(outcome.id, outcome.code, outcome.label) for outcome in market.outcomes]
        order_books = [self._build_order_book(outcome.id, outcome.label) for outcome in market.outcomes]
        recent_trades = [
            trade.model_copy()
            for trade in sorted(self._trades, key=lambda item: item.executed_at, reverse=True)
            if trade.outcome_id in {outcome.id for outcome in market.outcomes}
        ][:10]
        return MarketTradingShellResponse(
            market=market,
            quotes=quotes,
            order_books=order_books,
            recent_trades=recent_trades,
        )

    async def get_market_holders(self, slug: str, limit: int) -> MarketHoldersResponse:
        market = await self._market_repository.get_market(slug)
        return MarketHoldersResponse(
            market_id=market.id,
            market_slug=market.slug,
            groups=[
                MarketHolderGroupResponse(outcome_id=outcome.id, outcome_label=outcome.label, holders=[])
                for outcome in market.outcomes
            ],
            last_updated_at=_utcnow(),
        )

    async def get_market_history(
        self,
        slug: str,
        outcome_id: UUID,
        range_key: str,
    ) -> MarketHistoryResponse:
        resolved_range, lookback_window, interval_seconds = resolve_market_history_range(range_key)
        market = await self._market_repository.get_market(slug)
        outcome = next((item for item in market.outcomes if item.id == outcome_id), None)
        if outcome is None:
            raise NotFoundError("Market outcome not found")

        window_end = _utcnow()
        window_start = window_end - lookback_window
        outcome_trades = [
            trade
            for trade in self._trades
            if trade.outcome_id == outcome_id and window_start <= trade.executed_at <= window_end
        ]
        buckets = self._build_history_buckets(outcome_trades, window_start, interval_seconds)
        return MarketHistoryResponse(
            market_id=market.id,
            market_slug=market.slug,
            outcome_id=outcome.id,
            outcome_label=outcome.label,
            range_key=resolved_range,
            interval_seconds=interval_seconds,
            window_start=window_start,
            window_end=window_end,
            buckets=buckets,
        )

    async def list_market_orders(self, slug: str, actor_id: UUID) -> list[MarketOrderResponse]:
        market = await self._market_repository.get_market(slug)
        return [
            order.model_copy()
            for order in sorted(self._orders, key=lambda item: item.created_at, reverse=True)
            if order.market_id == market.id and self._order_owners.get(order.id) == actor_id
        ]

    async def create_market_order(
        self,
        slug: str,
        actor_id: UUID,
        payload: MarketOrderCreateRequest,
    ) -> MarketOrderResponse:
        market = await self._market_repository.get_market(slug)
        if market.status not in {"pending_liquidity", "open"}:
            raise ConflictError("Orders are only accepted while the market is gathering liquidity or open for trading")
        if payload.order_type != "limit":
            raise ConflictError("Market orders are not enabled until the matching engine is live")
        if payload.side not in {"buy", "sell"}:
            raise ConflictError("Order side must be buy or sell")
        if payload.price is None:
            raise ConflictError("Limit orders require a price")
        if payload.quantity <= 0:
            raise ConflictError("Order quantity must be greater than zero")
        if payload.price <= 0 or payload.price >= 1:
            raise ConflictError("Order price must be between 0 and 1")
        required_cost = self._required_order_collateral(payload.side, payload.quantity, payload.price)
        available_balance = self._get_available_balance(actor_id, market.rail_mode)
        if available_balance < required_cost:
            raise ConflictError("Insufficient available balance for this order")

        outcome = next((item for item in market.outcomes if item.id == payload.outcome_id), None)
        if outcome is None:
            raise NotFoundError("Market outcome not found")

        created_at = _utcnow()
        order = MarketOrderResponse(
            id=uuid4(),
            market_id=market.id,
            outcome_id=outcome.id,
            outcome_label=outcome.label,
            side=payload.side,
            order_type=payload.order_type,
            status="open",
            quantity=_decimal_to_str(payload.quantity),
            price=_decimal_to_str(payload.price),
            matched_quantity="0",
            remaining_quantity=_decimal_to_str(payload.quantity),
            max_total_cost=_decimal_to_str(required_cost),
            source="web",
            client_order_id=payload.client_order_id,
            rejection_reason=None,
            created_at=created_at,
            updated_at=created_at,
        )
        self._orders.append(order)
        self._order_owners[order.id] = actor_id
        return order.model_copy()

    async def cancel_market_order(
        self,
        slug: str,
        order_id: UUID,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> MarketOrderResponse:
        market = await self._market_repository.get_market(slug)
        for index, order in enumerate(self._orders):
            if order.id != order_id or order.market_id != market.id:
                continue
            owner_id = self._order_owners.get(order.id)
            if owner_id != actor_id and not actor_is_admin:
                raise ForbiddenError("You do not have permission to cancel this order")
            if order.status not in {"open", "partially_filled", "pending_acceptance"}:
                raise ConflictError("Only active orders can be cancelled")
            updated = order.model_copy(update={"status": "cancelled", "updated_at": _utcnow()})
            self._orders[index] = updated
            return updated.model_copy()
        raise NotFoundError("Market order not found")

    async def get_portfolio_summary(self, actor_id: UUID) -> PortfolioSummaryResponse:
        balances = [
            PortfolioBalanceResponse(
                asset_code=asset_code,
                rail_mode=rail_mode,
                account_code=f"USER::{actor_id}::{asset_code}::{rail_mode}",
                settled_balance=_decimal_to_str(balance),
                reserved_balance=_decimal_to_str(self._reserved_balance(actor_id, rail_mode)),
                available_balance=_decimal_to_str(balance - self._reserved_balance(actor_id, rail_mode)),
            )
            for (profile_id, asset_code, rail_mode), balance in self._balances.items()
            if profile_id == actor_id
        ]
        if not balances:
            seeded = self._seed_balance(actor_id, "USDC", "onchain")
            balances = [
                PortfolioBalanceResponse(
                    asset_code="USDC",
                    rail_mode="onchain",
                    account_code=f"USER::{actor_id}::USDC::onchain",
                    settled_balance=_decimal_to_str(seeded),
                    reserved_balance=_decimal_to_str(self._reserved_balance(actor_id, "onchain")),
                    available_balance=_decimal_to_str(seeded - self._reserved_balance(actor_id, "onchain")),
                )
            ]

        open_orders = [
            order.model_copy()
            for order in sorted(self._orders, key=lambda item: item.created_at, reverse=True)
            if self._order_owners.get(order.id) == actor_id and order.status in {"pending_acceptance", "open", "partially_filled"}
        ]
        recent_trades = [trade.model_copy() for trade in self._trades][:20]

        return PortfolioSummaryResponse(
            balances=balances,
            positions=[],
            open_orders=open_orders,
            recent_trades=recent_trades,
        )

    async def fund_balance(
        self,
        reviewer_id: UUID,
        payload: AdminFundBalanceRequest,
    ) -> PortfolioSummaryResponse:
        _ = reviewer_id
        key = (payload.profile_id, payload.asset_code.upper(), payload.rail_mode)
        self._balances[key] = self._balances.get(key, Decimal("0")) + payload.amount
        return await self.get_portfolio_summary(payload.profile_id)

    def _build_quote(self, outcome_id: UUID, outcome_code: str, outcome_label: str) -> MarketQuoteResponse:
        bids = [
            Decimal(order.price)
            for order in self._orders
            if order.outcome_id == outcome_id and order.side == "buy" and order.status in {"open", "partially_filled"} and order.price
        ]
        asks = [
            Decimal(order.price)
            for order in self._orders
            if order.outcome_id == outcome_id and order.side == "sell" and order.status in {"open", "partially_filled"} and order.price
        ]
        resting_bid_quantity = sum(
            Decimal(order.remaining_quantity)
            for order in self._orders
            if order.outcome_id == outcome_id and order.side == "buy" and order.status in {"open", "partially_filled"}
        )
        resting_ask_quantity = sum(
            Decimal(order.remaining_quantity)
            for order in self._orders
            if order.outcome_id == outcome_id and order.side == "sell" and order.status in {"open", "partially_filled"}
        )
        outcome_trades = [trade for trade in self._trades if trade.outcome_id == outcome_id]
        traded_volume = sum(Decimal(trade.quantity) for trade in outcome_trades)
        last_price = outcome_trades[-1].price if outcome_trades else None
        return MarketQuoteResponse(
            outcome_id=outcome_id,
            outcome_code=outcome_code,
            outcome_label=outcome_label,
            last_price=last_price,
            best_bid=_decimal_to_str(max(bids)) if bids else None,
            best_ask=_decimal_to_str(min(asks)) if asks else None,
            traded_volume=_decimal_to_str(traded_volume),
            resting_bid_quantity=_decimal_to_str(resting_bid_quantity),
            resting_ask_quantity=_decimal_to_str(resting_ask_quantity),
        )

    def _build_order_book(self, outcome_id: UUID, outcome_label: str) -> MarketOrderBookResponse:
        def build_levels(side: str, reverse: bool) -> list[MarketDepthLevelResponse]:
            levels: dict[str, dict[str, Decimal | int]] = {}
            for order in self._orders:
                if order.outcome_id != outcome_id or order.side != side or order.status not in {"open", "partially_filled"}:
                    continue
                price = order.price or "0"
                level = levels.setdefault(
                    price,
                    {"quantity": Decimal("0"), "order_count": 0},
                )
                level["quantity"] = Decimal(level["quantity"]) + Decimal(order.remaining_quantity)
                level["order_count"] = int(level["order_count"]) + 1
            sorted_prices = sorted((Decimal(price) for price in levels.keys()), reverse=reverse)[:5]
            return [
                MarketDepthLevelResponse(
                    price=_decimal_to_str(price) or "0",
                    quantity=_decimal_to_str(levels[_decimal_to_str(price) or "0"]["quantity"]) or "0",
                    order_count=int(levels[_decimal_to_str(price) or "0"]["order_count"]),
                )
                for price in sorted_prices
            ]

        return MarketOrderBookResponse(
            outcome_id=outcome_id,
            outcome_label=outcome_label,
            bids=build_levels("buy", True),
            asks=build_levels("sell", False),
        )

    def _build_history_buckets(
        self,
        trades_for_outcome: list[MarketTradeResponse],
        window_start: datetime,
        interval_seconds: int,
    ) -> list[MarketHistoryBucketResponse]:
        grouped: dict[datetime, list[MarketTradeResponse]] = {}
        for trade in sorted(trades_for_outcome, key=lambda item: item.executed_at):
            bucket_epoch = int(trade.executed_at.timestamp() // interval_seconds) * interval_seconds
            bucket_start = datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)
            grouped.setdefault(bucket_start, []).append(trade)

        buckets: list[MarketHistoryBucketResponse] = []
        for bucket_start, bucket_trades in sorted(grouped.items(), key=lambda item: item[0]):
            prices = [Decimal(trade.price) for trade in bucket_trades]
            volume = sum(Decimal(trade.quantity) for trade in bucket_trades)
            buckets.append(
                MarketHistoryBucketResponse(
                    bucket_start=bucket_start,
                    bucket_end=bucket_start + timedelta(seconds=interval_seconds),
                    open_price=bucket_trades[0].price,
                    high_price=_decimal_to_str(max(prices)),
                    low_price=_decimal_to_str(min(prices)),
                    close_price=bucket_trades[-1].price,
                    volume=_decimal_to_str(volume) or "0",
                    trade_count=len(bucket_trades),
                )
            )
        return buckets

    def _reserved_balance(self, actor_id: UUID, rail_mode: str) -> Decimal:
        return sum(
            self._required_order_collateral(order.side, Decimal(order.remaining_quantity), Decimal(order.price or "0"))
            for order in self._orders
            if self._order_owners.get(order.id) == actor_id
            and order.status in {"pending_acceptance", "open", "partially_filled"}
            and self._market_rail_mode(order.market_id) == rail_mode
        )

    def _seed_balance(self, actor_id: UUID, asset_code: str, rail_mode: str) -> Decimal:
        key = (actor_id, asset_code, rail_mode)
        self._balances.setdefault(key, Decimal("1000"))
        return self._balances[key]

    def _get_available_balance(self, actor_id: UUID, rail_mode: str) -> Decimal:
        settled = self._seed_balance(actor_id, "USDC" if rail_mode == "onchain" else "AUD", rail_mode)
        return settled - self._reserved_balance(actor_id, rail_mode)

    @staticmethod
    def _required_order_collateral(side: str, quantity: Decimal, price: Decimal) -> Decimal:
        if side == "buy":
            return quantity * price
        return quantity * (Decimal("1") - price)

    def _market_rail_mode(self, market_id: UUID) -> str | None:
        market = self._market_repository.find_market_by_id(market_id)
        return market.rail_mode if market is not None else None

    def cancel_orders_for_market(self, market_id: UUID) -> None:
        for index, order in enumerate(self._orders):
            if order.market_id != market_id or order.status not in {"pending_acceptance", "open", "partially_filled"}:
                continue
            self._orders[index] = order.model_copy(
                update={
                    "status": "cancelled",
                    "remaining_quantity": "0",
                    "updated_at": _utcnow(),
                }
            )


def _decimal_to_str(value: Decimal | int | float) -> str:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    normalized = decimal_value.quantize(Decimal("0.00000001"))
    return format(normalized.normalize(), "f")
