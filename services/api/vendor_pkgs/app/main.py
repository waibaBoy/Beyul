from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.schemas.common import RootResponse


app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(service=settings.app_name, status="scaffolded")
