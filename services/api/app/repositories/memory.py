from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.base import CommunityRepository, MarketRepository, MarketRequestRepository, PostRepository, ProfileRepository
from app.schemas.market import MarketOutcomeResponse, MarketResponse
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
from app.schemas.post import PostCreateRequest, PostResponse
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
        return [request.model_copy() for request in self._requests.values() if request.status == "submitted"]

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
    def __init__(self, market_request_repository: InMemoryMarketRequestRepository | None = None) -> None:
        self._markets: dict[str, MarketResponse] = {}
        self._market_request_repository = market_request_repository

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
        created_at = _utcnow()
        slug = f"market-{str(request_id).split('-')[0]}"
        market = MarketResponse(
            id=uuid4(),
            slug=slug,
            title="Published Market",
            question="Published market question",
            description="Converted from a market request in memory mode.",
            status="pending_liquidity",
            market_access_mode="public",
            rail_mode="onchain",
            resolution_mode="oracle",
            rules_text=review_notes or "Official source resolves the winning outcome.",
            community_id=None,
            community_slug=None,
            community_name=None,
            created_from_request_id=request_id,
            creator_id=reviewer_id,
            settlement_source_id=UUID("60000000-0000-0000-0000-000000000001"),
            settlement_reference_url=None,
            min_seed_amount="0",
            min_participants=2,
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
