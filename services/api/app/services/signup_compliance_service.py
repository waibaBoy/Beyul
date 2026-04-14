from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.tables import legal_acceptances

logger = logging.getLogger(__name__)

_MAX_VERSION_LEN = 128


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
        return True
    return False


def _sanitize_version(raw: Any) -> str | None:
    if raw is None:
        return None
    text_value = str(raw).strip()
    if not text_value or len(text_value) > _MAX_VERSION_LEN:
        return None
    return text_value


def _parse_client_asserted_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if isinstance(raw, str):
        candidate = raw.strip()
        if not candidate:
            return None
        try:
            normalized = candidate.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def metadata_indicates_signup_compliance(user_metadata: dict[str, Any]) -> bool:
    if not user_metadata:
        return False
    if not _truthy(user_metadata.get("age_confirmed")):
        return False
    if not _sanitize_version(user_metadata.get("terms_version")):
        return False
    if not _sanitize_version(user_metadata.get("privacy_version")):
        return False
    if not _sanitize_version(user_metadata.get("legal_bundle_version")):
        return False
    if _parse_client_asserted_at(user_metadata.get("terms_accepted_at")) is None:
        return False
    return True


async def record_signup_compliance_from_metadata(profile_id: UUID, user_metadata: dict[str, Any]) -> None:
    """
    Persist compliance rows once per (profile, type, version) when JWT user_metadata
    contains the fields set at email/password signup. Server time is used for accepted_at.
    """
    if settings.repository_backend != "postgres":
        return
    if not metadata_indicates_signup_compliance(user_metadata):
        return

    terms_version = _sanitize_version(user_metadata.get("terms_version"))
    privacy_version = _sanitize_version(user_metadata.get("privacy_version"))
    bundle_version = _sanitize_version(user_metadata.get("legal_bundle_version"))
    client_asserted = _parse_client_asserted_at(user_metadata.get("terms_accepted_at"))
    assert terms_version and privacy_version and bundle_version and client_asserted is not None

    now = datetime.now(UTC)
    rows = [
        {
            "profile_id": profile_id,
            "acceptance_type": "terms",
            "document_version": terms_version,
            "accepted_at": now,
            "source": "api_jwt_sync",
            "client_asserted_at": client_asserted,
            "created_at": now,
        },
        {
            "profile_id": profile_id,
            "acceptance_type": "privacy",
            "document_version": privacy_version,
            "accepted_at": now,
            "source": "api_jwt_sync",
            "client_asserted_at": client_asserted,
            "created_at": now,
        },
        {
            "profile_id": profile_id,
            "acceptance_type": "age_18",
            "document_version": bundle_version,
            "accepted_at": now,
            "source": "api_jwt_sync",
            "client_asserted_at": client_asserted,
            "created_at": now,
        },
    ]

    try:
        async with SessionLocal() as session:
            for row in rows:
                stmt = (
                    pg_insert(legal_acceptances)
                    .values(**row)
                    .on_conflict_do_nothing(constraint="legal_acceptances_profile_type_version_key")
                )
                await session.execute(stmt)
            await session.commit()
    except Exception:
        logger.exception("Failed to record signup compliance for profile_id=%s", profile_id)

