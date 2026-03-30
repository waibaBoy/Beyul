from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db.tables import (
    communities,
    community_members,
    market_outcomes,
    market_creation_request_answers,
    market_creation_requests,
    markets,
    posts,
    profiles,
    settlement_sources,
    user_wallets,
)
from app.repositories.base import CommunityRepository, MarketRepository, MarketRequestRepository, PostRepository, ProfileRepository
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
from app.schemas.market import MarketOutcomeResponse, MarketResponse
from app.schemas.post import PostCreateRequest, PostResponse
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)


def _profile_from_row(row: object) -> ProfileResponse:
    mapping = row._mapping
    return ProfileResponse(
        id=mapping["id"],
        username=mapping["username"],
        display_name=mapping["display_name"],
        bio=mapping["bio"],
        avatar_url=mapping["avatar_url"],
        is_admin=mapping["is_admin"],
    )


def _wallet_from_row(row: object) -> UserWalletResponse:
    mapping = row._mapping
    return UserWalletResponse(
        id=mapping["id"],
        chain_name=mapping["chain_name"],
        wallet_address=mapping["wallet_address"],
        is_primary=mapping["is_primary"],
    )


def _community_from_row(row: object) -> CommunityResponse:
    mapping = row._mapping
    return CommunityResponse(
        id=mapping["id"],
        slug=mapping["slug"],
        name=mapping["name"],
        description=mapping["description"],
        visibility=mapping["visibility"],
        require_post_approval=mapping["require_post_approval"],
        require_market_approval=mapping["require_market_approval"],
    )


def _member_from_row(row: object) -> CommunityMemberResponse:
    mapping = row._mapping
    return CommunityMemberResponse(
        id=mapping["id"],
        profile_id=mapping["profile_id"],
        username=mapping["username"],
        display_name=mapping["display_name"],
        role=mapping["role"],
    )


def _market_request_from_row(row: object) -> MarketRequestResponse:
    mapping = row._mapping
    return MarketRequestResponse(
        id=mapping["id"],
        requester_id=mapping["requester_id"],
        requester_username=mapping.get("requester_username"),
        requester_display_name=mapping.get("requester_display_name", "Unknown"),
        community_id=mapping.get("community_id"),
        community_slug=mapping.get("community_slug"),
        community_name=mapping.get("community_name"),
        title=mapping["title"],
        slug=mapping["slug"],
        question=mapping["question"],
        description=mapping["description"],
        market_access_mode=mapping["market_access_mode"],
        requested_rail=mapping["requested_rail"],
        resolution_mode=mapping["resolution_mode"],
        settlement_reference_url=mapping.get("settlement_reference_url"),
        status=mapping["status"],
        review_notes=mapping.get("review_notes"),
        submitted_at=mapping.get("submitted_at"),
        reviewed_at=mapping.get("reviewed_at"),
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


def _market_request_answer_from_row(row: object) -> MarketRequestAnswerResponse:
    mapping = row._mapping
    return MarketRequestAnswerResponse(
        question_key=mapping["question_key"],
        question_label=mapping["question_label"],
        answer_text=mapping["answer_text"],
        answer_json=mapping["answer_json"],
    )


def _post_from_row(row: object) -> PostResponse:
    mapping = row._mapping
    return PostResponse(
        id=mapping["id"],
        community_id=mapping["community_id"],
        community_slug=mapping["community_slug"],
        community_name=mapping["community_name"],
        author_id=mapping["author_id"],
        author_username=mapping.get("author_username"),
        author_display_name=mapping.get("author_display_name", "Unknown"),
        title=mapping["title"],
        body=mapping["body"],
        status=mapping["status"],
        submitted_at=mapping["submitted_at"],
        reviewed_at=mapping["reviewed_at"],
        reviewed_by=mapping["reviewed_by"],
        review_notes=mapping["review_notes"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


def _market_outcome_from_row(row: object) -> MarketOutcomeResponse:
    mapping = row._mapping
    settlement_value = mapping["settlement_value"]
    return MarketOutcomeResponse(
        id=mapping["id"],
        code=mapping["code"],
        label=mapping["label"],
        outcome_index=mapping["outcome_index"],
        status=mapping["status"],
        settlement_value=str(settlement_value) if settlement_value is not None else None,
    )


def _market_from_row(row: object, outcomes: list[MarketOutcomeResponse]) -> MarketResponse:
    mapping = row._mapping
    return MarketResponse(
        id=mapping["id"],
        slug=mapping["slug"],
        title=mapping["title"],
        question=mapping["question"],
        description=mapping["description"],
        status=mapping["status"],
        market_access_mode=mapping["market_access_mode"],
        rail_mode=mapping["rail_mode"],
        resolution_mode=mapping["resolution_mode"],
        rules_text=mapping["rules_text"],
        community_id=mapping["community_id"],
        community_slug=mapping.get("community_slug"),
        community_name=mapping.get("community_name"),
        created_from_request_id=mapping["created_from_request_id"],
        creator_id=mapping["creator_id"],
        settlement_source_id=mapping["settlement_source_id"],
        settlement_reference_url=mapping["settlement_reference_url"],
        min_seed_amount=str(mapping["min_seed_amount"]),
        min_participants=mapping["min_participants"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
        outcomes=outcomes,
    )


class PostgresProfileRepository(ProfileRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
    ) -> ProfileResponse:
        async with self._session_factory() as session:
            result = await session.execute(select(profiles).where(profiles.c.id == actor_id))
            row = result.first()
            if row is not None:
                return _profile_from_row(row)
        return ProfileResponse(
            id=actor_id,
            username=username,
            display_name=display_name,
            bio=None,
            avatar_url=None,
            is_admin=is_admin,
        )

    async def get_profile_by_username(self, username: str) -> ProfileResponse:
        async with self._session_factory() as session:
            result = await session.execute(select(profiles).where(profiles.c.username == username))
            row = result.first()
            if row is None:
                raise NotFoundError("Profile not found")
            return _profile_from_row(row)

    async def update_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
        payload: ProfileUpdateRequest,
    ) -> ProfileResponse:
        values = {
            "id": actor_id,
            "username": username,
            "display_name": payload.display_name or display_name,
            "bio": payload.bio,
            "avatar_url": payload.avatar_url,
            "is_admin": is_admin,
        }
        async with self._session_factory() as session:
            result = await session.execute(
                pg_insert(profiles)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[profiles.c.id],
                    set_={
                        "username": values["username"],
                        "display_name": values["display_name"],
                        "bio": values["bio"],
                        "avatar_url": values["avatar_url"],
                        "is_admin": values["is_admin"],
                    },
                )
                .returning(profiles)
            )
            row = result.first()
            await session.commit()
            return _profile_from_row(row)

    async def list_wallets(self, actor_id: UUID) -> list[UserWalletResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(user_wallets)
                .where(user_wallets.c.profile_id == actor_id)
                .order_by(user_wallets.c.is_primary.desc(), user_wallets.c.created_at.asc())
            )
            return [_wallet_from_row(row) for row in result.fetchall()]

    async def create_wallet(self, actor_id: UUID, payload: WalletCreateRequest) -> UserWalletResponse:
        async with self._session_factory() as session:
            if payload.is_primary:
                await session.execute(
                    update(user_wallets)
                    .where(user_wallets.c.profile_id == actor_id)
                    .values(is_primary=False)
                )
            try:
                result = await session.execute(
                    insert(user_wallets)
                    .values(
                        profile_id=actor_id,
                        chain_name=payload.chain_name,
                        wallet_address=payload.wallet_address,
                        is_primary=payload.is_primary,
                        metadata={},
                    )
                    .returning(user_wallets)
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Wallet already exists") from exc
            row = result.first()
            await session.commit()
            return _wallet_from_row(row)

    async def update_wallet(
        self,
        actor_id: UUID,
        wallet_id: UUID,
        payload: WalletUpdateRequest,
    ) -> UserWalletResponse:
        async with self._session_factory() as session:
            if payload.is_primary:
                await session.execute(
                    update(user_wallets)
                    .where(user_wallets.c.profile_id == actor_id)
                    .values(is_primary=False)
                )
            result = await session.execute(
                update(user_wallets)
                .where(and_(user_wallets.c.id == wallet_id, user_wallets.c.profile_id == actor_id))
                .values(is_primary=payload.is_primary)
                .returning(user_wallets)
            )
            row = result.first()
            if row is None:
                await session.rollback()
                raise NotFoundError("Wallet not found")
            await session.commit()
            return _wallet_from_row(row)

    async def delete_wallet(self, actor_id: UUID, wallet_id: UUID) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(user_wallets)
                .where(and_(user_wallets.c.id == wallet_id, user_wallets.c.profile_id == actor_id))
                .returning(user_wallets.c.id)
            )
            if result.first() is None:
                await session.rollback()
                raise NotFoundError("Wallet not found")
            await session.commit()


class PostgresCommunityRepository(CommunityRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_communities(self, actor_id: UUID, actor_is_admin: bool) -> list[CommunityResponse]:
        async with self._session_factory() as session:
            if actor_is_admin:
                stmt = select(communities).order_by(communities.c.created_at.desc())
            else:
                membership = community_members.alias("membership")
                stmt = (
                    select(communities)
                    .select_from(
                        communities.outerjoin(
                            membership,
                            and_(
                                membership.c.community_id == communities.c.id,
                                membership.c.profile_id == actor_id,
                            ),
                        )
                    )
                    .where(
                        or_(
                            communities.c.visibility == "public",
                            communities.c.created_by == actor_id,
                            membership.c.id.is_not(None),
                        )
                    )
                    .order_by(communities.c.created_at.desc())
                )
            result = await session.execute(stmt)
            return [_community_from_row(row) for row in result.fetchall()]

    async def create_community(self, actor_id: UUID, payload: CommunityCreateRequest) -> CommunityResponse:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    insert(communities)
                    .values(
                        slug=payload.slug,
                        name=payload.name,
                        description=payload.description,
                        visibility=payload.visibility,
                        require_post_approval=payload.require_post_approval,
                        require_market_approval=payload.require_market_approval,
                        created_by=actor_id,
                    )
                    .returning(communities)
                )
                community_row = result.first()
                await session.execute(
                    insert(community_members).values(
                        community_id=community_row._mapping["id"],
                        profile_id=actor_id,
                        role="owner",
                    )
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Community slug already exists") from exc
            await session.commit()
            return _community_from_row(community_row)

    async def get_community(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> CommunityResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            return _community_from_row(context["row"])

    async def update_community(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityUpdateRequest,
    ) -> CommunityResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not context["is_staff"]:
                raise ForbiddenError("You do not have permission to update this community")
            current = context["row"]._mapping
            await session.execute(
                update(communities)
                .where(communities.c.id == current["id"])
                .values(
                    name=payload.name or current["name"],
                    description=payload.description if payload.description is not None else current["description"],
                    visibility=payload.visibility or current["visibility"],
                    require_post_approval=(
                        payload.require_post_approval
                        if payload.require_post_approval is not None
                        else current["require_post_approval"]
                    ),
                    require_market_approval=(
                        payload.require_market_approval
                        if payload.require_market_approval is not None
                        else current["require_market_approval"]
                    ),
                )
            )
            refreshed = await session.execute(select(communities).where(communities.c.id == current["id"]))
            await session.commit()
            return _community_from_row(refreshed.first())

    async def list_members(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> list[CommunityMemberResponse]:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            stmt = (
                select(
                    community_members.c.id,
                    community_members.c.profile_id,
                    community_members.c.role,
                    profiles.c.username,
                    profiles.c.display_name,
                )
                .select_from(community_members.join(profiles, community_members.c.profile_id == profiles.c.id))
                .where(community_members.c.community_id == context["row"]._mapping["id"])
                .order_by(community_members.c.joined_at.asc())
            )
            result = await session.execute(stmt)
            return [_member_from_row(row) for row in result.fetchall()]

    async def add_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityMemberCreateRequest,
    ) -> CommunityMemberResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not (
                actor_is_admin
                or context["is_staff"]
                or (payload.profile_id == actor_id and context["row"]._mapping["visibility"] == "public")
            ):
                raise ForbiddenError("You do not have permission to add members to this community")
            try:
                result = await session.execute(
                    insert(community_members)
                    .values(
                        community_id=context["row"]._mapping["id"],
                        profile_id=payload.profile_id,
                        role=payload.role,
                    )
                    .returning(community_members.c.id, community_members.c.profile_id, community_members.c.role)
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Community member already exists") from exc
            inserted = result.first()
            profile_result = await session.execute(
                select(profiles.c.username, profiles.c.display_name).where(profiles.c.id == payload.profile_id)
            )
            profile_row = profile_result.first()
            await session.commit()
            return CommunityMemberResponse(
                id=inserted._mapping["id"],
                profile_id=inserted._mapping["profile_id"],
                username=profile_row._mapping["username"] if profile_row else "unknown",
                display_name=profile_row._mapping["display_name"] if profile_row else "Unknown",
                role=inserted._mapping["role"],
            )

    async def update_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        member_id: UUID,
        payload: CommunityMemberUpdateRequest,
    ) -> CommunityMemberResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not context["is_staff"]:
                raise ForbiddenError("You do not have permission to update community members")
            result = await session.execute(
                update(community_members)
                .where(
                    and_(
                        community_members.c.id == member_id,
                        community_members.c.community_id == context["row"]._mapping["id"],
                    )
                )
                .values(role=payload.role)
                .returning(
                    community_members.c.id,
                    community_members.c.profile_id,
                    community_members.c.role,
                )
            )
            row = result.first()
            if row is None:
                await session.rollback()
                raise NotFoundError("Member not found")
            profile_result = await session.execute(
                select(profiles.c.username, profiles.c.display_name)
                .where(profiles.c.id == row._mapping["profile_id"])
            )
            profile_row = profile_result.first()
            await session.commit()
            return CommunityMemberResponse(
                id=row._mapping["id"],
                profile_id=row._mapping["profile_id"],
                username=profile_row._mapping["username"] if profile_row else "unknown",
                display_name=profile_row._mapping["display_name"] if profile_row else "Unknown",
                role=row._mapping["role"],
            )

    async def delete_member(self, slug: str, actor_id: UUID, actor_is_admin: bool, member_id: UUID) -> None:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not context["is_staff"]:
                raise ForbiddenError("You do not have permission to remove community members")
            result = await session.execute(
                delete(community_members)
                .where(
                    and_(
                        community_members.c.id == member_id,
                        community_members.c.community_id == context["row"]._mapping["id"],
                    )
                )
                .returning(community_members.c.id)
            )
            if result.first() is None:
                await session.rollback()
                raise NotFoundError("Member not found")
            await session.commit()

    async def _get_community_context(self, session, slug: str, actor_id: UUID, actor_is_admin: bool) -> dict[str, object]:
        result = await session.execute(select(communities).where(communities.c.slug == slug))
        row = result.first()
        if row is None:
            raise NotFoundError("Community not found")
        mapping = row._mapping
        role: str | None = None
        if not actor_is_admin:
            membership = await session.execute(
                select(community_members.c.role).where(
                    and_(
                        community_members.c.community_id == mapping["id"],
                        community_members.c.profile_id == actor_id,
                    )
                )
            )
            membership_row = membership.first()
            role = membership_row._mapping["role"] if membership_row else None
        can_read = actor_is_admin or mapping["visibility"] == "public" or mapping["created_by"] == actor_id or role is not None
        if not can_read:
            raise ForbiddenError("You do not have access to this community")
        is_staff = actor_is_admin or mapping["created_by"] == actor_id or role in {"moderator", "admin", "owner"}
        return {"row": row, "is_staff": is_staff}


class PostgresPostRepository(PostRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_posts(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> list[PostResponse]:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, community_slug, actor_id, actor_is_admin)
            stmt = self._post_select_stmt().where(posts.c.community_id == context["community_id"])
            if not context["is_staff"]:
                stmt = stmt.where(or_(posts.c.status == "approved", posts.c.author_id == actor_id))
            stmt = stmt.order_by(posts.c.created_at.desc())
            result = await session.execute(stmt)
            return [_post_from_row(row) for row in result.fetchall()]

    async def create_post(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: PostCreateRequest,
    ) -> PostResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, community_slug, actor_id, actor_is_admin)
            auto_approved = not context["require_post_approval"] or context["is_staff"]
            values = {
                "community_id": context["community_id"],
                "author_id": actor_id,
                "title": payload.title,
                "body": payload.body,
                "status": "approved" if auto_approved else "pending_review",
                "submitted_at": func.now(),
                "metadata": {},
            }
            if context["require_post_approval"] and context["is_staff"]:
                values["reviewed_at"] = func.now()
                values["reviewed_by"] = actor_id
            result = await session.execute(insert(posts).values(**values).returning(posts.c.id))
            post_id = result.scalar_one()
            row = await self._fetch_post(session, post_id)
            await session.commit()
            return _post_from_row(row)

    async def list_pending_posts(self) -> list[PostResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._post_select_stmt()
                .where(posts.c.status == "pending_review")
                .order_by(posts.c.submitted_at.desc().nullslast(), posts.c.created_at.desc())
            )
            return [_post_from_row(row) for row in result.fetchall()]

    async def review_post(
        self,
        post_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> PostResponse:
        async with self._session_factory() as session:
            current_result = await session.execute(select(posts.c.status).where(posts.c.id == post_id))
            current = current_result.first()
            if current is None:
                raise NotFoundError("Post not found")
            if current._mapping["status"] != "pending_review":
                raise ConflictError("Only pending posts can be reviewed")
            await session.execute(
                update(posts)
                .where(posts.c.id == post_id)
                .values(
                    status="approved" if approved else "rejected",
                    reviewed_at=func.now(),
                    reviewed_by=reviewer_id,
                    review_notes=review_notes,
                )
            )
            row = await self._fetch_post(session, post_id)
            await session.commit()
            return _post_from_row(row)

    def _post_select_stmt(self):
        author_profiles = profiles.alias("author_profiles")
        community_alias = communities.alias("post_communities")
        return (
            select(
                posts,
                author_profiles.c.username.label("author_username"),
                author_profiles.c.display_name.label("author_display_name"),
                community_alias.c.slug.label("community_slug"),
                community_alias.c.name.label("community_name"),
            )
            .select_from(
                posts.join(author_profiles, posts.c.author_id == author_profiles.c.id).join(
                    community_alias, posts.c.community_id == community_alias.c.id
                )
            )
        )

    async def _fetch_post(self, session, post_id: UUID):
        result = await session.execute(self._post_select_stmt().where(posts.c.id == post_id))
        row = result.first()
        if row is None:
            raise NotFoundError("Post not found")
        return row

    async def _get_community_context(self, session, community_slug: str, actor_id: UUID, actor_is_admin: bool) -> dict[str, object]:
        result = await session.execute(select(communities).where(communities.c.slug == community_slug))
        row = result.first()
        if row is None:
            raise NotFoundError("Community not found")
        mapping = row._mapping
        role: str | None = None
        if not actor_is_admin:
            membership = await session.execute(
                select(community_members.c.role).where(
                    and_(
                        community_members.c.community_id == mapping["id"],
                        community_members.c.profile_id == actor_id,
                    )
                )
            )
            membership_row = membership.first()
            role = membership_row._mapping["role"] if membership_row else None
        can_read = actor_is_admin or mapping["visibility"] == "public" or mapping["created_by"] == actor_id or role is not None
        if not can_read:
            raise ForbiddenError("You do not have access to this community")
        return {
            "community_id": mapping["id"],
            "require_post_approval": mapping["require_post_approval"],
            "is_staff": actor_is_admin or mapping["created_by"] == actor_id or role in {"moderator", "admin", "owner"},
        }


class PostgresMarketRequestRepository(MarketRequestRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_requests(self, requester_id: UUID) -> list[MarketRequestResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._market_request_select_stmt()
                .where(market_creation_requests.c.requester_id == requester_id)
                .order_by(market_creation_requests.c.created_at.desc())
            )
            return [_market_request_from_row(row) for row in result.fetchall()]

    async def list_pending_requests(self) -> list[MarketRequestResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._market_request_select_stmt()
                .where(market_creation_requests.c.status == "submitted")
                .order_by(
                    market_creation_requests.c.submitted_at.desc().nullslast(),
                    market_creation_requests.c.created_at.desc(),
                )
            )
            return [_market_request_from_row(row) for row in result.fetchall()]

    async def create_request(
        self,
        requester_id: UUID,
        payload: MarketRequestCreateRequest,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    insert(market_creation_requests)
                    .values(
                        requester_id=requester_id,
                        community_id=payload.community_id,
                        title=payload.title,
                        slug=payload.slug,
                        question=payload.question,
                        description=payload.description,
                        market_access_mode=payload.market_access_mode,
                        requested_rail=payload.requested_rail,
                        settlement_source_id=payload.settlement_source_id,
                        settlement_reference_url=payload.settlement_reference_url,
                        resolution_mode=payload.resolution_mode,
                        status="draft",
                        metadata={},
                    )
                    .returning(market_creation_requests.c.id)
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Market request slug already exists") from exc
            request_id = result.scalar_one()
            row = await self._fetch_request(session, request_id, requester_id)
            await session.commit()
            return _market_request_from_row(row)

    async def get_request(self, request_id: UUID, requester_id: UUID | None = None) -> MarketRequestResponse:
        async with self._session_factory() as session:
            row = await self._fetch_request(session, request_id, requester_id)
            return _market_request_from_row(row)

    async def update_request(
        self,
        request_id: UUID,
        requester_id: UUID,
        payload: MarketRequestUpdateRequest,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            current = await self._get_owned_request_row(session, request_id, requester_id)
            mapping = current._mapping
            if mapping["status"] != "draft":
                raise ConflictError("Only draft market requests can be updated")
            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(
                    title=payload.title or mapping["title"],
                    question=payload.question or mapping["question"],
                    description=payload.description if payload.description is not None else mapping["description"],
                    settlement_reference_url=(
                        payload.settlement_reference_url
                        if payload.settlement_reference_url is not None
                        else mapping["settlement_reference_url"]
                    ),
                )
            )
            row = await self._fetch_request(session, request_id, requester_id)
            await session.commit()
            return _market_request_from_row(row)

    async def upsert_answer(
        self,
        request_id: UUID,
        requester_id: UUID,
        question_key: str,
        payload: MarketRequestAnswerUpsertRequest,
    ) -> MarketRequestAnswerResponse:
        async with self._session_factory() as session:
            current = await self._get_owned_request_row(session, request_id, requester_id)
            if current._mapping["status"] != "draft":
                raise ConflictError("Only draft market requests can be edited")
            existing = await session.execute(
                select(market_creation_request_answers)
                .where(
                    and_(
                        market_creation_request_answers.c.market_request_id == request_id,
                        market_creation_request_answers.c.question_key == question_key,
                    )
                )
            )
            if existing.first() is None:
                result = await session.execute(
                    insert(market_creation_request_answers)
                    .values(
                        market_request_id=request_id,
                        question_key=question_key,
                        question_label=payload.question_label,
                        answer_text=payload.answer_text,
                        answer_json=payload.answer_json,
                    )
                    .returning(market_creation_request_answers)
                )
            else:
                result = await session.execute(
                    update(market_creation_request_answers)
                    .where(
                        and_(
                            market_creation_request_answers.c.market_request_id == request_id,
                            market_creation_request_answers.c.question_key == question_key,
                        )
                    )
                    .values(
                        question_label=payload.question_label,
                        answer_text=payload.answer_text,
                        answer_json=payload.answer_json,
                    )
                    .returning(market_creation_request_answers)
                )
            row = result.first()
            await session.commit()
            return _market_request_answer_from_row(row)

    async def ensure_exists(self, request_id: UUID, requester_id: UUID | None = None) -> None:
        async with self._session_factory() as session:
            await self._fetch_request(session, request_id, requester_id)

    async def list_answers(
        self,
        request_id: UUID,
        requester_id: UUID | None = None,
    ) -> list[MarketRequestAnswerResponse]:
        async with self._session_factory() as session:
            await self._fetch_request(session, request_id, requester_id)
            result = await session.execute(
                select(market_creation_request_answers)
                .where(market_creation_request_answers.c.market_request_id == request_id)
                .order_by(market_creation_request_answers.c.question_key.asc())
            )
            return [_market_request_answer_from_row(row) for row in result.fetchall()]

    async def submit_request(
        self,
        request_id: UUID,
        requester_id: UUID,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            current = await self._get_owned_request_row(session, request_id, requester_id)
            if current._mapping["status"] != "draft":
                raise ConflictError("Only draft market requests can be submitted")
            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(status="submitted", submitted_at=func.now())
            )
            row = await self._fetch_request(session, request_id, requester_id)
            await session.commit()
            return _market_request_from_row(row)

    async def review_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            current_result = await session.execute(
                select(market_creation_requests.c.status).where(market_creation_requests.c.id == request_id)
            )
            current = current_result.first()
            if current is None:
                raise NotFoundError("Market request not found")
            if current._mapping["status"] != "submitted":
                raise ConflictError("Only submitted market requests can be reviewed")
            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(
                    status="approved" if approved else "rejected",
                    reviewed_at=func.now(),
                    reviewed_by=reviewer_id,
                    review_notes=review_notes,
                )
            )
            row = await self._fetch_request(session, request_id)
            await session.commit()
            return _market_request_from_row(row)

    def _market_request_select_stmt(self):
        requester_profiles = profiles.alias("requester_profiles")
        community_alias = communities.alias("request_communities")
        return (
            select(
                market_creation_requests,
                requester_profiles.c.username.label("requester_username"),
                requester_profiles.c.display_name.label("requester_display_name"),
                community_alias.c.slug.label("community_slug"),
                community_alias.c.name.label("community_name"),
            )
            .select_from(
                market_creation_requests.join(
                    requester_profiles,
                    market_creation_requests.c.requester_id == requester_profiles.c.id,
                ).outerjoin(community_alias, market_creation_requests.c.community_id == community_alias.c.id)
            )
        )

    async def _fetch_request(self, session, request_id: UUID, requester_id: UUID | None = None):
        stmt = self._market_request_select_stmt().where(market_creation_requests.c.id == request_id)
        if requester_id is not None:
            stmt = stmt.where(market_creation_requests.c.requester_id == requester_id)
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            raise NotFoundError("Market request not found")
        return row

    async def _get_owned_request_row(self, session, request_id: UUID, requester_id: UUID):
        result = await session.execute(
            select(market_creation_requests).where(
                and_(
                    market_creation_requests.c.id == request_id,
                    market_creation_requests.c.requester_id == requester_id,
                )
            )
        )
        row = result.first()
        if row is None:
            raise NotFoundError("Market request not found")
        return row


class PostgresMarketRepository(MarketRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def publish_from_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        review_notes: str | None,
    ) -> MarketResponse:
        async with self._session_factory() as session:
            request_result = await session.execute(
                select(market_creation_requests).where(market_creation_requests.c.id == request_id)
            )
            request_row = request_result.first()
            if request_row is None:
                raise NotFoundError("Market request not found")
            request_mapping = request_row._mapping
            if request_mapping["status"] not in {"submitted", "approved"}:
                raise ConflictError("Only submitted or approved market requests can be published")
            existing_market = await session.execute(
                select(markets.c.id, markets.c.slug).where(markets.c.created_from_request_id == request_id)
            )
            existing_market_row = existing_market.first()
            if existing_market_row is not None:
                raise ConflictError("A market has already been created from this request")
            if request_mapping["requested_rail"] is None:
                raise ConflictError("Market request is missing a requested rail")

            settlement_source_id = request_mapping["settlement_source_id"]
            if settlement_source_id is None:
                source_result = await session.execute(
                    select(settlement_sources.c.id).where(
                        settlement_sources.c.resolution_mode == request_mapping["resolution_mode"]
                    )
                )
                source_row = source_result.first()
                if source_row is None:
                    raise ConflictError("No settlement source is available for this request")
                settlement_source_id = source_row._mapping["id"]

            rules_text = self._build_rules_text(request_mapping, review_notes)
            market_insert = await session.execute(
                insert(markets)
                .values(
                    community_id=request_mapping["community_id"],
                    created_from_request_id=request_id,
                    creator_id=request_mapping["requester_id"],
                    settlement_source_id=settlement_source_id,
                    slug=request_mapping["slug"] or f"market-{str(request_id).split('-')[0]}",
                    title=request_mapping["title"],
                    question=request_mapping["question"],
                    description=request_mapping["description"],
                    rules_text=rules_text,
                    market_access_mode=request_mapping["market_access_mode"],
                    rail_mode=request_mapping["requested_rail"],
                    status="pending_liquidity",
                    resolution_mode=request_mapping["resolution_mode"],
                    settlement_reference_url=request_mapping["settlement_reference_url"],
                    min_seed_amount=request_mapping["min_seed_amount"] or 0,
                    min_participants=request_mapping["min_participants"] or 2,
                    metadata={"published_from_request": str(request_id)},
                )
                .returning(markets.c.id, markets.c.slug)
            )
            market_row = market_insert.first()
            market_id = market_row._mapping["id"]

            for outcome_index, outcome in enumerate((("YES", "Yes"), ("NO", "No"))):
                await session.execute(
                    insert(market_outcomes).values(
                        market_id=market_id,
                        code=outcome[0],
                        label=outcome[1],
                        outcome_index=outcome_index,
                        status="active",
                    )
                )

            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(
                    status="converted",
                    reviewed_at=func.now(),
                    reviewed_by=reviewer_id,
                    review_notes=review_notes,
                )
            )
            market = await self._fetch_market(session, market_row._mapping["slug"])
            await session.commit()
            return market

    async def list_markets(self) -> list[MarketResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._market_select_stmt().order_by(markets.c.created_at.desc())
            )
            rows = result.fetchall()
            return [await self._hydrate_market(session, row) for row in rows]

    async def get_market(self, slug: str) -> MarketResponse:
        async with self._session_factory() as session:
            return await self._fetch_market(session, slug)

    def _market_select_stmt(self):
        community_alias = communities.alias("market_communities")
        return (
            select(
                markets,
                community_alias.c.slug.label("community_slug"),
                community_alias.c.name.label("community_name"),
            )
            .select_from(markets.outerjoin(community_alias, markets.c.community_id == community_alias.c.id))
        )

    async def _fetch_market(self, session, slug: str) -> MarketResponse:
        result = await session.execute(self._market_select_stmt().where(markets.c.slug == slug))
        row = result.first()
        if row is None:
            raise NotFoundError("Market not found")
        return await self._hydrate_market(session, row)

    async def _hydrate_market(self, session, row) -> MarketResponse:
        outcome_result = await session.execute(
            select(market_outcomes)
            .where(market_outcomes.c.market_id == row._mapping["id"])
            .order_by(market_outcomes.c.outcome_index.asc())
        )
        outcomes = [_market_outcome_from_row(outcome_row) for outcome_row in outcome_result.fetchall()]
        return _market_from_row(row, outcomes)

    def _build_rules_text(self, request_mapping, review_notes: str | None) -> str:
        settlement_url = request_mapping["settlement_reference_url"] or "the approved settlement source"
        base = f"This market resolves against {settlement_url}. The winning outcome is determined by the final official result."
        if review_notes:
            return f"{base}\n\nAdmin notes: {review_notes}"
        return base
