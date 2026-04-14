from datetime import datetime

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


class SystemStatusResponse(BaseModel):
    status: str
    app_env: str
    repository_backend: str
    oracle_provider: str
    oracle_execution_mode: str
    market_data_provider: str
    blocked_jurisdictions: list[str] = Field(default_factory=list)
    uptime_seconds: float
    server_time: datetime
    db_status: str | None = None
    db_backend: str | None = None


class RootResponse(BaseModel):
    service: str
    status: str


class ReviewDecisionRequest(BaseModel):
    review_notes: str | None = None
