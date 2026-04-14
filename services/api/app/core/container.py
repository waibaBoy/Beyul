from app.core.config import settings
from app.repositories.memory import (
    InMemoryCommunityRepository,
    InMemoryMarketRepository,
    InMemoryMarketRequestRepository,
    InMemoryPostRepository,
    InMemoryProfileRepository,
    InMemoryTradingRepository,
)
from app.services.admin_service import AdminService
from app.services.actor_service import ActorService
from app.services.community_service import CommunityService
from app.services.database_service import DatabaseService
from app.services.market_service import MarketService
from app.services.market_request_service import MarketRequestService
from app.services.market_data_service import BinanceMarketDataService, MarketDataService, NoopMarketDataService
from app.services.oracle_service import MockOracleService, OracleService, UMAOracleService
from app.services.portfolio_service import PortfolioService
from app.services.post_service import PostService
from app.services.profile_service import ProfileService
from app.services.creator_service import CreatorService
from app.services.market_quality_service import MarketQualityService
from app.services.notification_service import NotificationService
from app.services.amm_service import AmmConfig, AmmService
from app.services.depth_kpi_service import DepthKpiService
from app.services.fee_service import FeeService
from app.services.rolling_market_service import RollingMarketService
from app.services.advanced_order_service import AdvancedOrderService
from app.services.social_service import SocialService
from app.services.supabase_auth_service import SupabaseAuthService
from app.services.trading_service import TradingService
from app.services.push_notification_service import PushNotificationService
from app.services.transfer_service import TransferService
from app.services.api_key_service import ApiKeyService


class AppContainer:
    def __init__(self) -> None:
        market_data_service: MarketDataService
        oracle_service: OracleService
        if settings.market_data_provider == "binance":
            market_data_service = BinanceMarketDataService(settings.binance_api_base_url)
        else:
            market_data_service = NoopMarketDataService()
        if settings.oracle_provider == "uma":
            oracle_service = UMAOracleService()
        else:
            oracle_service = MockOracleService()

        if settings.repository_backend == "postgres":
            from app.db.session import SessionLocal
            from app.repositories.postgres import (
                PostgresCommunityRepository,
                PostgresMarketRepository,
                PostgresMarketRequestRepository,
                PostgresPostRepository,
                PostgresProfileRepository,
                PostgresTradingRepository,
            )

            profile_repository = PostgresProfileRepository(SessionLocal)
            community_repository = PostgresCommunityRepository(SessionLocal)
            post_repository = PostgresPostRepository(SessionLocal)
            market_request_repository = PostgresMarketRequestRepository(SessionLocal)
            market_repository = PostgresMarketRepository(SessionLocal, market_data_service, oracle_service)
            trading_repository = PostgresTradingRepository(SessionLocal)
            session_factory = SessionLocal
        else:
            profile_repository = InMemoryProfileRepository()
            community_repository = InMemoryCommunityRepository()
            post_repository = InMemoryPostRepository()
            market_request_repository = InMemoryMarketRequestRepository()
            market_repository = InMemoryMarketRepository(market_request_repository, market_data_service, oracle_service)
            trading_repository = InMemoryTradingRepository(market_repository)
            session_factory = None

        self.market_data_service = market_data_service
        self.oracle_service = oracle_service
        self.profile_service = ProfileService(profile_repository)
        self.community_service = CommunityService(community_repository)
        self.post_service = PostService(post_repository)
        self.market_quality_service = MarketQualityService(session_factory)
        self.market_request_service = MarketRequestService(market_request_repository, self.market_quality_service)
        self.market_service = MarketService(market_repository)
        self.notification_service = NotificationService(session_factory)
        self.creator_service = CreatorService(session_factory)
        self.trading_service = TradingService(trading_repository, self.notification_service)
        self.portfolio_service = PortfolioService(trading_repository)
        self.rolling_market_service = RollingMarketService(market_repository)
        self.admin_service = AdminService(
            post_repository,
            market_request_repository,
            market_repository,
            oracle_service,
            self.rolling_market_service,
        )
        self.fee_service = FeeService(session_factory)
        self.depth_kpi_service = DepthKpiService(session_factory)
        self.amm_service = AmmService(AmmConfig())
        self.social_service = SocialService(session_factory)
        self.transfer_service = TransferService(session_factory)
        self.database_service = DatabaseService()
        self.advanced_order_service = AdvancedOrderService()
        self.actor_service = ActorService()
        self.push_notification_service = PushNotificationService(session_factory)
        self.api_key_service = ApiKeyService(session_factory)
        self.supabase_auth_service = SupabaseAuthService()


container = AppContainer()
