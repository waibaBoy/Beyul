from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentActor, get_community_service, get_current_actor, get_post_service
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.schemas.common import MessageResponse
from app.schemas.community import (
    CommunityCreateRequest,
    CommunityMemberCreateRequest,
    CommunityMemberResponse,
    CommunityMemberUpdateRequest,
    CommunityResponse,
    CommunityUpdateRequest,
)
from app.schemas.post import PostCreateRequest, PostResponse
from app.services.community_service import CommunityService
from app.services.post_service import PostService

router = APIRouter(prefix="/communities", tags=["communities"])


@router.get("", response_model=list[CommunityResponse])
async def list_communities(
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> list[CommunityResponse]:
    return await service.list_communities(actor)


@router.post("", response_model=CommunityResponse, status_code=status.HTTP_201_CREATED)
async def create_community(
    payload: CommunityCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> CommunityResponse:
    try:
        return await service.create_community(actor, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{community_slug}", response_model=CommunityResponse)
async def get_community(
    community_slug: str,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> CommunityResponse:
    try:
        return await service.get_community(actor, community_slug)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")


@router.patch("/{community_slug}", response_model=CommunityResponse)
async def update_community(
    community_slug: str,
    payload: CommunityUpdateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> CommunityResponse:
    try:
        return await service.update_community(actor, community_slug, payload)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")


@router.get("/{community_slug}/members", response_model=list[CommunityMemberResponse])
async def list_community_members(
    community_slug: str,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> list[CommunityMemberResponse]:
    try:
        return await service.list_members(actor, community_slug)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")


@router.post(
    "/{community_slug}/members",
    response_model=CommunityMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_community_member(
    community_slug: str,
    payload: CommunityMemberCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> CommunityMemberResponse:
    try:
        return await service.add_member(actor, community_slug, payload)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")


@router.patch("/{community_slug}/members/{member_id}", response_model=CommunityMemberResponse)
async def update_community_member(
    community_slug: str,
    member_id: UUID,
    payload: CommunityMemberUpdateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> CommunityMemberResponse:
    try:
        return await service.update_member(actor, community_slug, member_id, payload)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except NotFoundError as exc:
        detail = "Community not found" if "Community" in str(exc) else "Member not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.delete("/{community_slug}/members/{member_id}", response_model=MessageResponse)
async def delete_community_member(
    community_slug: str,
    member_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
    service: CommunityService = Depends(get_community_service),
) -> MessageResponse:
    try:
        await service.delete_member(actor, community_slug, member_id)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError as exc:
        detail = "Community not found" if "Community" in str(exc) else "Member not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return MessageResponse(message="Community member removal scaffolded locally")


@router.get("/{community_slug}/posts", response_model=list[PostResponse])
async def list_community_posts(
    community_slug: str,
    actor: CurrentActor = Depends(get_current_actor),
    service: PostService = Depends(get_post_service),
) -> list[PostResponse]:
    try:
        return await service.list_posts(actor, community_slug)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")


@router.post("/{community_slug}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_community_post(
    community_slug: str,
    payload: PostCreateRequest,
    actor: CurrentActor = Depends(get_current_actor),
    service: PostService = Depends(get_post_service),
) -> PostResponse:
    try:
        return await service.create_post(actor, community_slug, payload)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
