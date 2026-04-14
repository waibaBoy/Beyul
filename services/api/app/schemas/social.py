from uuid import UUID

from pydantic import BaseModel, Field


class TradingProfileResponse(BaseModel):
    profile_id: UUID | None = None
    username: str
    display_name: str | None = None
    total_positions: int = 0
    realized_pnl: str = "0"
    total_trades: int = 0
    total_volume: str = "0"
    follower_count: int = 0
    following_count: int = 0
    is_following: bool = False


class FollowActionRequest(BaseModel):
    username: str


class FollowListEntry(BaseModel):
    username: str
    display_name: str | None = None
    followed_at: str


class FollowListResponse(BaseModel):
    users: list[FollowListEntry] = Field(default_factory=list)
    count: int = 0


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    display_name: str | None = None
    total_pnl: str = "0"
    position_count: int = 0


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry] = Field(default_factory=list)
