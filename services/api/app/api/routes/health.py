from fastapi import APIRouter, Depends

from app.api.deps import get_database_service
from app.schemas.common import DatabaseHealthResponse, HealthResponse
from app.services.database_service import DatabaseService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def database_health(
    service: DatabaseService = Depends(get_database_service),
) -> DatabaseHealthResponse:
    return await service.get_health()
