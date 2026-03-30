from uuid import UUID

from pydantic import BaseModel


class CommunityResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None
    visibility: str
    require_post_approval: bool
    require_market_approval: bool


class CommunityCreateRequest(BaseModel):
    slug: str
    name: str
    description: str | None = None
    visibility: str = "public"
    require_post_approval: bool = True
    require_market_approval: bool = True


class CommunityUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    require_post_approval: bool | None = None
    require_market_approval: bool | None = None


class CommunityMemberResponse(BaseModel):
    id: UUID
    profile_id: UUID
    username: str
    display_name: str
    role: str


class CommunityMemberCreateRequest(BaseModel):
    profile_id: UUID
    role: str = "member"


class CommunityMemberUpdateRequest(BaseModel):
    role: str
