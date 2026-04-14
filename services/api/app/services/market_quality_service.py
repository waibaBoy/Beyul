"""
Market quality controls: duplicate detection, anti-spam, moderation SLA,
and proposal content linting.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.slug import normalize_slug
from app.schemas.market_request import MarketRequestCreateRequest

logger = logging.getLogger(__name__)

MAX_PENDING_REQUESTS_PER_USER = 5
MODERATION_SLA_HOURS = 48
MIN_TITLE_LENGTH = 8
MAX_TITLE_LENGTH = 200
MIN_QUESTION_LENGTH = 10
MAX_QUESTION_LENGTH = 500
SIMILARITY_THRESHOLD = 0.45

_BANNED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(test|asdf|xxx|foo|bar)\b", re.IGNORECASE),
]

_REQUIRED_QUESTION_MARK = re.compile(r"\?")


class QualityWarning:
    def __init__(self, code: str, severity: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.severity = severity
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


class QualityReport:
    def __init__(self) -> None:
        self.warnings: list[QualityWarning] = []
        self.duplicate_matches: list[dict[str, Any]] = []
        self.blocked: bool = False
        self.block_reason: str | None = None

    @property
    def has_errors(self) -> bool:
        return self.blocked or any(w.severity == "error" for w in self.warnings)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "warnings": [w.to_dict() for w in self.warnings],
            "duplicate_matches": self.duplicate_matches,
        }


class MarketQualityService:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def check_proposal(
        self,
        requester_id: UUID,
        payload: MarketRequestCreateRequest,
    ) -> QualityReport:
        report = QualityReport()
        self._lint_content(payload, report)
        await self._check_spam(requester_id, report)
        await self._check_duplicates(payload.title, payload.question, payload.slug, report)
        return report

    async def get_moderation_sla_report(self) -> list[dict[str, Any]]:
        if settings.repository_backend != "postgres" or not self._session_factory:
            return []

        cutoff = datetime.now(UTC) - timedelta(hours=MODERATION_SLA_HOURS)
        try:
            from sqlalchemy import text
            async with self._session_factory() as session:
                result = await session.execute(text("""
                    select
                        id,
                        title,
                        requester_id,
                        submitted_at,
                        extract(epoch from (now() - submitted_at)) / 3600.0 as hours_pending
                    from public.market_creation_requests
                    where status = 'submitted'
                      and submitted_at < :cutoff
                    order by submitted_at asc
                    limit 50
                """), {"cutoff": cutoff})
                rows = result.fetchall()
                return [
                    {
                        "request_id": str(row.id),
                        "title": row.title,
                        "requester_id": str(row.requester_id),
                        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
                        "hours_pending": round(float(row.hours_pending), 1),
                        "sla_breached": True,
                    }
                    for row in rows
                ]
        except Exception:
            logger.debug("Failed to load moderation SLA report", exc_info=True)
            return []

    def _lint_content(self, payload: MarketRequestCreateRequest, report: QualityReport) -> None:
        title = (payload.title or "").strip()
        question = (payload.question or "").strip()

        if len(title) < MIN_TITLE_LENGTH:
            report.warnings.append(QualityWarning(
                "title_too_short", "error",
                f"Title must be at least {MIN_TITLE_LENGTH} characters.",
            ))
        if len(title) > MAX_TITLE_LENGTH:
            report.warnings.append(QualityWarning(
                "title_too_long", "error",
                f"Title must be at most {MAX_TITLE_LENGTH} characters.",
            ))
        if len(question) < MIN_QUESTION_LENGTH:
            report.warnings.append(QualityWarning(
                "question_too_short", "error",
                f"Question must be at least {MIN_QUESTION_LENGTH} characters.",
            ))
        if len(question) > MAX_QUESTION_LENGTH:
            report.warnings.append(QualityWarning(
                "question_too_long", "error",
                f"Question must be at most {MAX_QUESTION_LENGTH} characters.",
            ))

        if question and not _REQUIRED_QUESTION_MARK.search(question):
            report.warnings.append(QualityWarning(
                "question_no_question_mark", "warning",
                "A good market question should end with a question mark.",
            ))

        if title == title.upper() and len(title) > 10:
            report.warnings.append(QualityWarning(
                "title_all_caps", "warning",
                "Please avoid all-caps titles.",
            ))

        for pattern in _BANNED_PATTERNS:
            if pattern.search(title) or pattern.search(question):
                report.warnings.append(QualityWarning(
                    "spam_content", "error",
                    "Title or question contains placeholder or test content.",
                ))
                break

        if payload.resolution_mode not in {"oracle", "api", "council"}:
            report.warnings.append(QualityWarning(
                "invalid_resolution_mode", "error",
                f"Resolution mode '{payload.resolution_mode}' is not valid. Use oracle, api, or council.",
            ))

        if payload.market_access_mode not in {"public", "private_group"}:
            report.warnings.append(QualityWarning(
                "invalid_access_mode", "error",
                f"Access mode '{payload.market_access_mode}' is not valid.",
            ))

    async def _check_spam(self, requester_id: UUID, report: QualityReport) -> None:
        if settings.repository_backend != "postgres" or not self._session_factory:
            return

        try:
            from sqlalchemy import text
            async with self._session_factory() as session:
                result = await session.execute(text("""
                    select count(*) as cnt
                    from public.market_creation_requests
                    where requester_id = :uid
                      and status in ('draft', 'submitted')
                """), {"uid": requester_id})
                row = result.fetchone()
                pending_count = row.cnt if row else 0

                if pending_count >= MAX_PENDING_REQUESTS_PER_USER:
                    report.blocked = True
                    report.block_reason = (
                        f"You already have {pending_count} pending market requests. "
                        f"Please wait for them to be reviewed before submitting more (limit: {MAX_PENDING_REQUESTS_PER_USER})."
                    )
        except Exception:
            logger.debug("Failed to check spam for requester %s", requester_id, exc_info=True)

    async def _check_duplicates(
        self,
        title: str,
        question: str,
        slug: str | None,
        report: QualityReport,
    ) -> None:
        if settings.repository_backend != "postgres" or not self._session_factory:
            return

        normalized_slug = normalize_slug(slug, fallback=title)
        normalized_title = title.strip().lower()
        normalized_question = question.strip().lower()

        try:
            from sqlalchemy import text
            async with self._session_factory() as session:
                if normalized_slug:
                    slug_result = await session.execute(text("""
                        select slug, title, status from public.markets
                        where slug = :s and status not in ('cancelled', 'settled')
                        limit 3
                    """), {"s": normalized_slug})
                    slug_matches = slug_result.fetchall()
                    for row in slug_matches:
                        report.duplicate_matches.append({
                            "source": "market",
                            "slug": row.slug,
                            "title": row.title,
                            "status": row.status,
                            "match_type": "exact_slug",
                        })

                    req_slug_result = await session.execute(text("""
                        select slug, title, status from public.market_creation_requests
                        where slug = :s and status in ('draft', 'submitted', 'approved')
                        limit 3
                    """), {"s": normalized_slug})
                    for row in req_slug_result.fetchall():
                        report.duplicate_matches.append({
                            "source": "request",
                            "slug": row.slug,
                            "title": row.title,
                            "status": row.status,
                            "match_type": "exact_slug",
                        })

                title_result = await session.execute(text("""
                    select slug, title, status
                    from public.markets
                    where lower(title) = :t
                      and status not in ('cancelled', 'settled')
                    limit 3
                """), {"t": normalized_title})
                for row in title_result.fetchall():
                    already = any(m.get("slug") == row.slug for m in report.duplicate_matches)
                    if not already:
                        report.duplicate_matches.append({
                            "source": "market",
                            "slug": row.slug,
                            "title": row.title,
                            "status": row.status,
                            "match_type": "exact_title",
                        })

                try:
                    sim_result = await session.execute(text("""
                        select slug, title, status,
                               similarity(lower(title), :t) as sim
                        from public.markets
                        where status not in ('cancelled', 'settled')
                          and similarity(lower(title), :t) > :threshold
                        order by sim desc
                        limit 5
                    """), {"t": normalized_title, "threshold": SIMILARITY_THRESHOLD})
                    for row in sim_result.fetchall():
                        already = any(m.get("slug") == row.slug for m in report.duplicate_matches)
                        if not already:
                            report.duplicate_matches.append({
                                "source": "market",
                                "slug": row.slug,
                                "title": row.title,
                                "status": row.status,
                                "match_type": "similar_title",
                                "similarity": round(float(row.sim), 3),
                            })
                except Exception:
                    logger.debug("Trigram similarity query failed (pg_trgm may not be enabled)", exc_info=True)

                if report.duplicate_matches:
                    exact = any(m["match_type"] in ("exact_slug", "exact_title") for m in report.duplicate_matches)
                    if exact:
                        report.warnings.append(QualityWarning(
                            "duplicate_exact", "error",
                            "A market with the same title or slug already exists.",
                            {"matches": len(report.duplicate_matches)},
                        ))
                    else:
                        report.warnings.append(QualityWarning(
                            "duplicate_similar", "warning",
                            f"Found {len(report.duplicate_matches)} similar existing market(s). Consider checking for duplicates.",
                            {"matches": len(report.duplicate_matches)},
                        ))

        except Exception:
            logger.debug("Duplicate check failed", exc_info=True)
