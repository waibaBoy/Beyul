from fastapi import APIRouter, Depends

from app.api.deps import CurrentActor, get_current_actor
from app.schemas.auth import (
    AuthActionResponse,
    AuthUserResponse,
    LoginRequest,
    SignupRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthActionResponse)
async def signup(_: SignupRequest) -> AuthActionResponse:
    return AuthActionResponse(message="Signup flow scaffolded locally")


@router.post("/login", response_model=AuthActionResponse)
async def login(_: LoginRequest) -> AuthActionResponse:
    return AuthActionResponse(
        message="Login flow scaffolded locally",
        access_token="local-access-token",
        refresh_token="local-refresh-token",
        token_type="bearer",
    )


@router.post("/logout", response_model=AuthActionResponse)
async def logout() -> AuthActionResponse:
    return AuthActionResponse(message="Logout flow scaffolded locally")


@router.post("/refresh", response_model=AuthActionResponse)
async def refresh() -> AuthActionResponse:
    return AuthActionResponse(
        message="Refresh flow scaffolded locally",
        access_token="local-access-token",
        refresh_token="local-refresh-token",
        token_type="bearer",
    )


@router.get("/me", response_model=AuthUserResponse)
async def get_me(actor: CurrentActor = Depends(get_current_actor)) -> AuthUserResponse:
    return AuthUserResponse(
        id=actor.id,
        username=actor.username,
        display_name=actor.display_name,
        is_admin=actor.is_admin,
    )
