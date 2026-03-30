from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MarketRequestResponse(BaseModel):
    id: UUID
    requester_id: UUID
    requester_username: str | None = None
    requester_display_name: str
    community_id: UUID | None = None
    community_slug: str | None = None
    community_name: str | None = None
    title: str
    slug: str | None = None
    question: str
    description: str | None = None
    market_access_mode: str
    requested_rail: str | None = None
    resolution_mode: str
    settlement_reference_url: str | None = None
    status: str
    review_notes: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MarketRequestCreateRequest(BaseModel):
    title: str
    slug: str | None = None
    question: str
    description: str | None = None
    market_access_mode: str
    requested_rail: str | None = None
    resolution_mode: str
    community_id: UUID | None = None
    settlement_source_id: UUID | None = None
    settlement_reference_url: str | None = None


class MarketRequestUpdateRequest(BaseModel):
    title: str | None = None
    question: str | None = None
    description: str | None = None
    settlement_reference_url: str | None = None


class MarketRequestAnswerUpsertRequest(BaseModel):
    question_label: str
    answer_text: str | None = None
    answer_json: dict | None = None


class MarketRequestAnswerResponse(BaseModel):
    question_key: str
    question_label: str
    answer_text: str | None = None
    answer_json: dict | None = None
