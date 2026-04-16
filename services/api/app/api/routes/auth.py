from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentActor, get_current_actor
from app.core.config import settings
from app.schemas.auth import (
    AuthActionResponse,
    AuthUserResponse,
    LoginRequest,
    SignupRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_is_prod = (settings.app_env or "").strip().lower() in {"production", "prod", "staging"}


@router.post("/signup", response_model=AuthActionResponse)
async def signup(_: SignupRequest) -> AuthActionResponse:
    if _is_prod:
        raise HTTPException(status_code=501, detail="Use Supabase Auth for signup in production")
    return AuthActionResponse(message="Signup flow scaffolded locally")


@router.post("/login", response_model=AuthActionResponse)
async def login(_: LoginRequest) -> AuthActionResponse:
    if _is_prod:
        raise HTTPException(status_code=501, detail="Use Supabase Auth for login in production")
    return AuthActionResponse(
        message="Login flow scaffolded locally — do NOT use in production",
    )


@router.post("/logout", response_model=AuthActionResponse)
async def logout() -> AuthActionResponse:
    return AuthActionResponse(message="Logout flow scaffolded locally")


@router.post("/refresh", response_model=AuthActionResponse)
async def refresh() -> AuthActionResponse:
    if _is_prod:
        raise HTTPException(status_code=501, detail="Use Supabase Auth for refresh in production")
    return AuthActionResponse(
        message="Refresh flow scaffolded locally — do NOT use in production",
    )


@router.get("/me", response_model=AuthUserResponse)
async def get_me(actor: CurrentActor = Depends(get_current_actor)) -> AuthUserResponse:
    return AuthUserResponse(
        id=actor.id,
        username=actor.username,
        display_name=actor.display_name,
        is_admin=actor.is_admin,
    )
