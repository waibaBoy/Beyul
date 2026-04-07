from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.communities import router as communities_router
from app.api.routes.health import router as health_router
from app.api.routes.markets import router as markets_router
from app.api.routes.market_requests import router as market_requests_router
from app.api.routes.posts import router as posts_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.profiles import router as profiles_router


api_router = APIRouter()
api_router.include_router(health_router)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(profiles_router)
v1_router.include_router(communities_router)
v1_router.include_router(posts_router)
v1_router.include_router(portfolio_router)
v1_router.include_router(market_requests_router)
v1_router.include_router(markets_router)
v1_router.include_router(admin_router)

api_router.include_router(v1_router)
