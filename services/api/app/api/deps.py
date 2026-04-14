from uuid import UUID

from fastapi import Header, HTTPException, status

from app.core.actor import CurrentActor
from app.core.config import settings
from app.core.container import container
from app.services.actor_service import ActorService
from app.services.admin_service import AdminService
from app.services.community_service import CommunityService
from app.services.database_service import DatabaseService
from app.services.market_service import MarketService
from app.services.market_request_service import MarketRequestService
from app.services.oracle_service import OracleService
from app.services.post_service import PostService
from app.services.portfolio_service import PortfolioService
from app.services.profile_service import ProfileService
from app.services.supabase_auth_service import SupabaseAuthService
from app.services.creator_service import CreatorService
from app.services.market_quality_service import MarketQualityService
from app.services.notification_service import NotificationService
from app.services.trading_service import TradingService


async def get_current_actor(
    authorization: str | None = Header(default=None),
    x_beyul_user_id: UUID | None = Header(default=None),
    x_beyul_username: str | None = Header(default=None),
    x_beyul_display_name: str | None = Header(default=None),
    x_beyul_is_admin: bool | None = Header(default=None),
    x_satta_user_id: UUID | None = Header(default=None),
    x_satta_username: str | None = Header(default=None),
    x_satta_display_name: str | None = Header(default=None),
    x_satta_is_admin: bool | None = Header(default=None),
) -> CurrentActor:
    if authorization:
        claims = await container.supabase_auth_service.verify_bearer_token(authorization)
        return await container.actor_service.resolve_authenticated_actor(claims)
    if settings.allow_dev_auth:
        return await container.actor_service.resolve_dev_actor(
            user_id=x_satta_user_id or x_beyul_user_id,
            username=x_satta_username or x_beyul_username,
            display_name=x_satta_display_name or x_beyul_display_name,
            is_admin=x_satta_is_admin if x_satta_is_admin is not None else x_beyul_is_admin,
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
    )


def get_profile_service() -> ProfileService:
    return container.profile_service


def get_community_service() -> CommunityService:
    return container.community_service


def get_post_service() -> PostService:
    return container.post_service


def get_market_request_service() -> MarketRequestService:
    return container.market_request_service


def get_market_service() -> MarketService:
    return container.market_service


def get_admin_service() -> AdminService:
    return container.admin_service


def get_trading_service() -> TradingService:
    return container.trading_service


def get_portfolio_service() -> PortfolioService:
    return container.portfolio_service


def get_oracle_service() -> OracleService:
    return container.oracle_service


def get_database_service() -> DatabaseService:
    return container.database_service


def get_actor_service() -> ActorService:
    return container.actor_service


def get_supabase_auth_service() -> SupabaseAuthService:
    return container.supabase_auth_service


def get_notification_service() -> NotificationService:
    return container.notification_service


def get_creator_service() -> CreatorService:
    return container.creator_service


def get_market_quality_service() -> MarketQualityService:
    return container.market_quality_service


def get_fee_service():
    from app.services.fee_service import FeeService
    return container.fee_service


def get_depth_kpi_service():
    from app.services.depth_kpi_service import DepthKpiService
    return container.depth_kpi_service


def get_amm_service():
    from app.services.amm_service import AmmService
    return container.amm_service


def require_oracle_secret(
    x_satta_oracle_secret: str | None = Header(default=None),
) -> None:
    if not settings.oracle_callback_secret or x_satta_oracle_secret != settings.oracle_callback_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Oracle callback authentication failed.",
        )
