import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import get_database_service
from app.schemas.common import DatabaseHealthResponse, HealthResponse, SystemStatusResponse
from app.services.database_service import DatabaseService
from app.core.config import settings

router = APIRouter(tags=["health"])

_BOOT_TIME = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def database_health(
    service: DatabaseService = Depends(get_database_service),
) -> DatabaseHealthResponse:
    return await service.get_health()


@router.get("/health/system", response_model=SystemStatusResponse)
async def system_status(
    db_service: DatabaseService = Depends(get_database_service),
) -> SystemStatusResponse:
    from app.api.deps import get_current_actor
    blocked = [j.strip() for j in settings.blocked_jurisdictions.split(",") if j.strip()]
    db_health = await db_service.get_health()

    env = (settings.app_env or "").lower()
    is_prod = env in {"production", "prod", "staging"}

    return SystemStatusResponse(
        status="ok",
        app_env=env if not is_prod else "production",
        repository_backend="configured" if is_prod else settings.repository_backend,
        oracle_provider="configured" if is_prod else settings.oracle_provider,
        oracle_execution_mode="configured" if is_prod else settings.oracle_execution_mode,
        market_data_provider="configured" if is_prod else settings.market_data_provider,
        blocked_jurisdictions=["redacted"] if is_prod and blocked else blocked,
        uptime_seconds=round(time.monotonic() - _BOOT_TIME, 2),
        server_time=datetime.now(timezone.utc),
        db_status=db_health.status,
        db_backend="configured" if is_prod else db_health.backend,
    )
