import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_cors_allowed_origins, settings
from app.middleware.jurisdiction import JurisdictionGateMiddleware
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


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JurisdictionGateMiddleware)
app.include_router(api_router)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(service=settings.app_name, status="scaffolded")
