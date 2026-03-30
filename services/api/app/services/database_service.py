from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.schemas.common import DatabaseHealthResponse


REQUIRED_RELATIONS = (
    "public.profiles",
    "public.user_wallets",
    "public.communities",
    "public.community_members",
    "public.market_creation_requests",
    "public.market_creation_request_answers",
)


class DatabaseService:
    async def get_health(self) -> DatabaseHealthResponse:
        if settings.repository_backend == "memory":
            return DatabaseHealthResponse(
                backend="memory",
                status="skipped",
                detail="Database schema checks are skipped while REPOSITORY_BACKEND=memory.",
            )

        from app.db.session import SessionLocal

        try:
            async with SessionLocal() as session:
                missing_relations: list[str] = []
                for relation in REQUIRED_RELATIONS:
                    result = await session.execute(
                        text("select to_regclass(:relation) as relation_name"),
                        {"relation": relation},
                    )
                    if result.scalar_one() is None:
                        missing_relations.append(relation)
        except (SQLAlchemyError, OSError, ValueError) as exc:
            return DatabaseHealthResponse(
                backend="postgres",
                status="unreachable",
                detail=f"{exc.__class__.__name__}: {exc}",
            )

        if missing_relations:
            return DatabaseHealthResponse(
                backend="postgres",
                status="missing_schema",
                missing_relations=missing_relations,
                detail="Required relations are missing. Apply the Supabase migrations before enabling live Postgres usage.",
            )

        return DatabaseHealthResponse(
            backend="postgres",
            status="ok",
            detail="Required relations are present for the current repository set.",
        )
