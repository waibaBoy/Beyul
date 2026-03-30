from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PostResponse(BaseModel):
    id: UUID
    community_id: UUID
    community_slug: str
    community_name: str
    author_id: UUID
    author_username: str | None = None
    author_display_name: str
    title: str | None = None
    body: str
    status: str
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class PostCreateRequest(BaseModel):
    title: str | None = None
    body: str
