from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentActor, get_creator_service, get_current_actor
from app.schemas.creator import (
    CreatorLeaderboardResponse,
    CreatorStatsResponse,
    CreatorTiersResponse,
)
from app.services.creator_service import CreatorService

router = APIRouter(prefix="/creators", tags=["creators"])


@router.get("/tiers", response_model=CreatorTiersResponse)
async def get_reward_tiers(
    service: CreatorService = Depends(get_creator_service),
) -> CreatorTiersResponse:
    return await service.get_tiers()


@router.get("/me/stats", response_model=CreatorStatsResponse)
async def get_my_creator_stats(
    actor: CurrentActor = Depends(get_current_actor),
    service: CreatorService = Depends(get_creator_service),
) -> CreatorStatsResponse:
    return await service.get_creator_stats(
        actor.id,
        username=actor.username,
        display_name=actor.display_name,
    )


@router.get("/leaderboard", response_model=CreatorLeaderboardResponse)
async def get_creator_leaderboard(
    limit: int = Query(default=20, ge=1, le=50),
    service: CreatorService = Depends(get_creator_service),
) -> CreatorLeaderboardResponse:
    return await service.get_leaderboard(limit=limit)
