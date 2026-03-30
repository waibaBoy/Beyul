from uuid import UUID

from pydantic import BaseModel


class AuthActionResponse(BaseModel):
    message: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    username: str
    display_name: str


class AuthUserResponse(BaseModel):
    id: UUID
    username: str
    display_name: str
    is_admin: bool
