from fastapi import APIRouter, Depends

from app.api.deps import CurrentActor, get_current_actor
from app.core.container import container
from app.schemas.common import MessageResponse
from app.schemas.social import (
    FollowActionRequest,
    FollowListEntry,
    FollowListResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    TradingProfileResponse,
)

router = APIRouter(prefix="/social", tags=["social"])


def _get_social_service():
    return container.social_service


@router.get("/profile/{username}", response_model=TradingProfileResponse)
async def get_trading_profile(
    username: str,
    actor: CurrentActor | None = Depends(get_current_actor),
):
    svc = _get_social_service()
    viewer_id = actor.id if actor else None
    profile = await svc.get_trading_profile(username, viewer_id)
    return TradingProfileResponse(**profile.to_dict())


@router.post("/follow", response_model=MessageResponse)
async def follow_user(
    payload: FollowActionRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_social_service()
    await svc.follow(actor.id, payload.username)
    return MessageResponse(message=f"Now following {payload.username}")


@router.post("/unfollow", response_model=MessageResponse)
async def unfollow_user(
    payload: FollowActionRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_social_service()
    await svc.unfollow(actor.id, payload.username)
    return MessageResponse(message=f"Unfollowed {payload.username}")


@router.get("/followers/{username}", response_model=FollowListResponse)
async def get_followers(username: str):
    svc = _get_social_service()
    users = await svc.get_followers(username)
    return FollowListResponse(
        users=[FollowListEntry(**u) for u in users],
        count=len(users),
    )


@router.get("/following/{username}", response_model=FollowListResponse)
async def get_following(username: str):
    svc = _get_social_service()
    users = await svc.get_following(username)
    return FollowListResponse(
        users=[FollowListEntry(**u) for u in users],
        count=len(users),
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_pnl_leaderboard(limit: int = 25):
    svc = _get_social_service()
    entries = await svc.get_pnl_leaderboard(limit)
    return LeaderboardResponse(entries=[LeaderboardEntry(**e) for e in entries])
