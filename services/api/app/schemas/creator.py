from pydantic import BaseModel, Field


class CreatorRewardTierResponse(BaseModel):
    tier_code: str
    tier_label: str
    min_volume_usd: str
    fee_share_bps: int
    badge_color: str
    sort_order: int


class CreatorStatsResponse(BaseModel):
    profile_id: str
    username: str | None = None
    display_name: str | None = None
    markets_created: int = 0
    markets_open: int = 0
    markets_settled: int = 0
    total_volume: str = "0"
    total_trades: int = 0
    current_tier: CreatorRewardTierResponse
    next_tier: CreatorRewardTierResponse | None = None
    volume_to_next_tier: str = "0"
    progress_pct: float = 0.0


class CreatorTiersResponse(BaseModel):
    tiers: list[CreatorRewardTierResponse] = Field(default_factory=list)


class CreatorLeaderboardEntry(BaseModel):
    profile_id: str
    username: str | None = None
    display_name: str
    markets_created: int = 0
    total_volume: str = "0"
    total_trades: int = 0
    tier_code: str
    tier_label: str
    badge_color: str


class CreatorLeaderboardResponse(BaseModel):
    entries: list[CreatorLeaderboardEntry] = Field(default_factory=list)
