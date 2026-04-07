from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.core.slug import normalize_slug


class MarketTemplateConfigResponse(BaseModel):
    category: str | None = None
    subcategory: str | None = None
    subject: str | None = None
    reference_asset: str | None = None
    threshold_value: str | None = None
    timeframe_label: str | None = None
    interval_label: str | None = None
    reference_source_label: str | None = None
    reference_price: str | None = None
    reference_timestamp: str | None = None
    reference_label: str | None = None
    contract_notes: str | None = None


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
    template_key: str | None = None
    template_config: MarketTemplateConfigResponse | None = None
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
    template_key: str | None = None
    template_config: MarketTemplateConfigResponse | None = None
    market_access_mode: str
    requested_rail: str | None = None
    resolution_mode: str
    community_id: UUID | None = None
    settlement_source_id: UUID | None = None
    settlement_reference_url: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        return normalize_slug(value)


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
