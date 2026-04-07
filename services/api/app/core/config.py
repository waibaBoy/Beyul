from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


SERVICE_API_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "Satta API"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    postgres_dsn: str = "postgresql+asyncpg://beyul:change_me@localhost:5432/beyul"
    redis_url: str = "redis://localhost:6379/0"
    repository_backend: Literal["memory", "postgres"] = "memory"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    allow_dev_auth: bool = True
    dev_auth_user_id: str = ""
    dev_auth_username: str = "demo_admin"
    dev_auth_display_name: str = "Demo Admin"
    dev_auth_is_admin: bool = True
    admin_email: str = ""
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ws_public_url: str = "ws://localhost:9000"
    market_data_provider: Literal["none", "binance"] = "none"
    binance_api_base_url: str = "https://api.binance.com"
    oracle_provider: Literal["mock", "uma"] = "mock"
    oracle_callback_secret: str = "dev-oracle-secret"
    oracle_liveness_minutes: int = 120
    oracle_chain_id: int = 137
    oracle_reward_wei: str = "0"
    oracle_bond_wei: str = "0"
    oracle_rpc_url: str = ""
    oracle_signer_private_key: str = ""
    oracle_signer_address: str = ""
    oracle_currency_address: str = ""
    oracle_uma_oo_address: str = ""
    oracle_uma_finder_address: str = ""
    oracle_uma_assertion_identifier: str = "ASSERT_TRUTH2"
    oracle_uma_escalation_manager: str = ""
    oracle_execution_mode: Literal["simulated", "live"] = "simulated"
    matching_engine_orders_queue: str = "engine.orders.incoming"
    matching_engine_orders_events_channel: str = "engine.orders.accepted"
    matching_engine_trades_channel: str = "engine.trades.executed"
    matching_engine_books_channel: str = "engine.books.updated"

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


def get_cors_allowed_origins() -> list[str]:
    return [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
