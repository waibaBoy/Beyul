import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_cors_allowed_origins, settings
from app.middleware.jurisdiction import JurisdictionGateMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.schemas.common import RootResponse

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "%s starting (app_env=%s repository_backend=%s)",
        settings.app_name,
        settings.app_env,
        settings.repository_backend,
    )
    yield
    logger.info("%s shutdown complete", settings.app_name)


_is_prod = (settings.app_env or "").strip().lower() in {"production", "prod", "staging"}

app = FastAPI(
    title="Satta API",
    description=(
        "Satta is a social prediction market platform where anyone can create, trade, and settle markets. "
        "Built for Australian compliance with zero-trust on-chain settlement.\n\n"
        "## Authentication\n"
        "Use bearer token (Supabase JWT) in the `Authorization` header, or "
        "an API key (`sk_live_*`) for programmatic access.\n\n"
        "## Rate Limits\n"
        "- General: 100 req/min\n"
        "- Auth: 20 req/min\n"
        "- Trading: 50 req/min\n\n"
        "## API Keys\n"
        "For programmatic trading, create API keys at `/api/v1/api-keys`. "
        "Pass the key as `Authorization: Bearer sk_live_...`."
    ),
    version="1.0.0",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_tags=[
        {"name": "health", "description": "System health and diagnostics"},
        {"name": "auth", "description": "Authentication and session management"},
        {"name": "profiles", "description": "User profile management"},
        {"name": "social", "description": "Social features: follow, leaderboard, trading profiles"},
        {"name": "markets", "description": "Market discovery and detail"},
        {"name": "market-requests", "description": "Market creation proposals"},
        {"name": "trading", "description": "Order placement and management"},
        {"name": "advanced-orders", "description": "Conditional orders: stop-loss, take-profit"},
        {"name": "portfolio", "description": "Portfolio, positions, and trade history"},
        {"name": "transfers", "description": "Deposit and withdrawal management"},
        {"name": "liquidity", "description": "Fee preview, depth KPIs, AMM status"},
        {"name": "notifications", "description": "In-app notification management"},
        {"name": "push-notifications", "description": "Browser push notification subscriptions"},
        {"name": "communities", "description": "Community hub management"},
        {"name": "creators", "description": "Creator dashboard and reward tiers"},
        {"name": "api-keys", "description": "API key management for programmatic trading"},
        {"name": "admin", "description": "Admin operations, moderation, settlement"},
    ],
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JurisdictionGateMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(api_router)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(service=settings.app_name, status="scaffolded")
