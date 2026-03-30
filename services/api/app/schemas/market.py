from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MarketOutcomeResponse(BaseModel):
    id: UUID
    code: str
    label: str
    outcome_index: int
    status: str
    settlement_value: str | None = None


class MarketResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    question: str
    description: str | None = None
    status: str
    market_access_mode: str
    rail_mode: str
    resolution_mode: str
    rules_text: str
    community_id: UUID | None = None
    community_slug: str | None = None
    community_name: str | None = None
    created_from_request_id: UUID | None = None
    creator_id: UUID
    settlement_source_id: UUID
    settlement_reference_url: str | None = None
    min_seed_amount: str
    min_participants: int
    created_at: datetime
    updated_at: datetime
    outcomes: list[MarketOutcomeResponse] = []
