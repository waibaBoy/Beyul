from pydantic import BaseModel, Field


class QualityWarningResponse(BaseModel):
    code: str
    severity: str
    message: str
    details: dict = Field(default_factory=dict)


class DuplicateMatchResponse(BaseModel):
    source: str
    slug: str | None = None
    title: str
    status: str
    match_type: str
    similarity: float | None = None


class QualityCheckResponse(BaseModel):
    blocked: bool = False
    block_reason: str | None = None
    warnings: list[QualityWarningResponse] = Field(default_factory=list)
    duplicate_matches: list[DuplicateMatchResponse] = Field(default_factory=list)


class ModerationSlaItemResponse(BaseModel):
    request_id: str
    title: str
    requester_id: str
    submitted_at: str | None = None
    hours_pending: float
    sla_breached: bool = True


class ModerationSlaReportResponse(BaseModel):
    sla_hours: int
    breached_items: list[ModerationSlaItemResponse] = Field(default_factory=list)
    total_breached: int = 0
