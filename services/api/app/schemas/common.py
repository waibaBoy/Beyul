from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


class DatabaseHealthResponse(BaseModel):
    backend: str
    status: str
    missing_relations: list[str] = Field(default_factory=list)
    detail: str | None = None


class RootResponse(BaseModel):
    service: str
    status: str


class ReviewDecisionRequest(BaseModel):
    review_notes: str | None = None
