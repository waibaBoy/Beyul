from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    label: str
    permissions: list[str] = Field(default_factory=lambda: ["read", "trade"])


class ApiKeyCreateResponse(BaseModel):
    id: str
    label: str
    key: str
    key_prefix: str
    permissions: list[str]
    is_active: bool
    created_at: str


class ApiKeyResponse(BaseModel):
    id: str
    label: str
    key_prefix: str
    permissions: list[str]
    is_active: bool
    last_used_at: str | None = None
    created_at: str


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse] = Field(default_factory=list)
    count: int = 0
