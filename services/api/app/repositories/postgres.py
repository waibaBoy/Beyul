from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ServiceUnavailableError
from app.core.market_templates import build_contract_metadata_from_template
from app.core.slug import normalize_slug
from app.db.tables import (
    assets,
    communities,
    community_members,
    dispute_evidence,
    disputes,
    ledger_accounts,
    ledger_entries,
    ledger_transactions,
    market_outcomes,
    market_creation_request_answers,
    market_creation_requests,
    market_resolutions,
    market_resolution_candidates,
    markets,
    orders,
    positions,
    posts,
    profiles,
    settlement_sources,
    trades,
    user_wallets,
)
from app.repositories.base import (
    CommunityRepository,
    MarketRepository,
    MarketRequestRepository,
    PostRepository,
    ProfileRepository,
    TradingRepository,
)
from app.services.market_data_service import MarketDataService
from app.schemas.community import (
    CommunityCreateRequest,
    CommunityMemberCreateRequest,
    CommunityMemberResponse,
    CommunityMemberUpdateRequest,
    CommunityResponse,
    CommunityUpdateRequest,
)
from app.schemas.market_request import (
    MarketRequestAnswerResponse,
    MarketRequestAnswerUpsertRequest,
    MarketRequestCreateRequest,
    MarketTemplateConfigResponse,
    MarketRequestResponse,
    MarketRequestUpdateRequest,
)
from app.schemas.market import (
    MarketDisputeCreateRequest,
    MarketDisputeEvidenceCreateRequest,
    MarketDisputeEvidenceResponse,
    MarketDisputeResponse,
    MarketDisputeReviewRequest,
    MarketContractTimesResponse,
    MarketHolderEntryResponse,
    MarketHolderGroupResponse,
    MarketHoldersResponse,
    MarketHistoryResponse,
    MarketHistoryBucketResponse,
    MarketDepthLevelResponse,
    MarketOrderCreateRequest,
    MarketOrderResponse,
    MarketOrderBookResponse,
    MarketOutcomeResponse,
    MarketQuoteResponse,
    MarketResolutionCandidateResponse,
    MarketResolutionEventResponse,
    MarketResolutionStateResponse,
    MarketReferenceContextResponse,
    MarketResponse,
    MarketSettlementSourceResponse,
    MarketTradeResponse,
    MarketTradingShellResponse,
    resolve_market_history_range,
)
from app.schemas.post import PostCreateRequest, PostResponse
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)
from app.schemas.portfolio import (
    AdminFundBalanceRequest,
    MarketResolutionResponse,
    MarketSettlementFinalizeRequest,
    MarketSettlementRequestCreateRequest,
    PortfolioBalanceResponse,
    PortfolioPositionResponse,
    PortfolioSummaryResponse,
)
from app.services.oracle_service import (
    OracleConfigurationError,
    OracleResolutionRequest,
    OracleResolutionStatusRequest,
    OracleService,
)


def _profile_from_row(row: object) -> ProfileResponse:
    mapping = row._mapping
    return ProfileResponse(
        id=mapping["id"],
        username=mapping["username"],
        display_name=mapping["display_name"],
        bio=mapping["bio"],
        avatar_url=mapping["avatar_url"],
        is_admin=mapping["is_admin"],
    )


def _wallet_from_row(row: object) -> UserWalletResponse:
    mapping = row._mapping
    return UserWalletResponse(
        id=mapping["id"],
        chain_name=mapping["chain_name"],
        wallet_address=mapping["wallet_address"],
        is_primary=mapping["is_primary"],
    )


def _community_from_row(row: object) -> CommunityResponse:
    mapping = row._mapping
    return CommunityResponse(
        id=mapping["id"],
        slug=mapping["slug"],
        name=mapping["name"],
        description=mapping["description"],
        visibility=mapping["visibility"],
        require_post_approval=mapping["require_post_approval"],
        require_market_approval=mapping["require_market_approval"],
    )


def _member_from_row(row: object) -> CommunityMemberResponse:
    mapping = row._mapping
    return CommunityMemberResponse(
        id=mapping["id"],
        profile_id=mapping["profile_id"],
        username=mapping["username"],
        display_name=mapping["display_name"],
        role=mapping["role"],
    )


def _market_request_from_row(row: object) -> MarketRequestResponse:
    mapping = row._mapping
    metadata = mapping.get("metadata") if hasattr(mapping, "get") else None
    template_config = None
    if isinstance(metadata, dict) and isinstance(metadata.get("template_config"), dict):
        template_config = MarketTemplateConfigResponse.model_validate(metadata["template_config"])
    return MarketRequestResponse(
        id=mapping["id"],
        requester_id=mapping["requester_id"],
        requester_username=mapping.get("requester_username"),
        requester_display_name=mapping.get("requester_display_name", "Unknown"),
        community_id=mapping.get("community_id"),
        community_slug=mapping.get("community_slug"),
        community_name=mapping.get("community_name"),
        title=mapping["title"],
        slug=mapping["slug"],
        question=mapping["question"],
        description=mapping["description"],
        template_key=metadata.get("template_key") if isinstance(metadata, dict) else None,
        template_config=template_config,
        market_access_mode=mapping["market_access_mode"],
        requested_rail=mapping["requested_rail"],
        resolution_mode=mapping["resolution_mode"],
        settlement_reference_url=mapping.get("settlement_reference_url"),
        status=mapping["status"],
        review_notes=mapping.get("review_notes"),
        submitted_at=mapping.get("submitted_at"),
        reviewed_at=mapping.get("reviewed_at"),
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


def _market_request_answer_from_row(row: object) -> MarketRequestAnswerResponse:
    mapping = row._mapping
    return MarketRequestAnswerResponse(
        question_key=mapping["question_key"],
        question_label=mapping["question_label"],
        answer_text=mapping["answer_text"],
        answer_json=mapping["answer_json"],
    )


def _post_from_row(row: object) -> PostResponse:
    mapping = row._mapping
    return PostResponse(
        id=mapping["id"],
        community_id=mapping["community_id"],
        community_slug=mapping["community_slug"],
        community_name=mapping["community_name"],
        author_id=mapping["author_id"],
        author_username=mapping.get("author_username"),
        author_display_name=mapping.get("author_display_name", "Unknown"),
        title=mapping["title"],
        body=mapping["body"],
        status=mapping["status"],
        submitted_at=mapping["submitted_at"],
        reviewed_at=mapping["reviewed_at"],
        reviewed_by=mapping["reviewed_by"],
        review_notes=mapping["review_notes"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


def _market_outcome_from_row(row: object) -> MarketOutcomeResponse:
    mapping = row._mapping
    settlement_value = mapping["settlement_value"]
    return MarketOutcomeResponse(
        id=mapping["id"],
        code=mapping["code"],
        label=mapping["label"],
        outcome_index=mapping["outcome_index"],
        status=mapping["status"],
        settlement_value=str(settlement_value) if settlement_value is not None else None,
    )


def _parse_datetime_value(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _coerce_market_contract_metadata(raw_metadata: object) -> dict[str, object]:
    if not isinstance(raw_metadata, dict):
        return {}
    contract_metadata = raw_metadata.get("contract")
    if isinstance(contract_metadata, dict):
        return contract_metadata
    return {}


def _extract_contract_answer_metadata(answer_rows: list[object]) -> dict[str, object]:
    text_answers: dict[str, str] = {}
    for answer_row in answer_rows:
        mapping = answer_row._mapping
        answer_text = mapping.get("answer_text")
        if isinstance(answer_text, str) and answer_text.strip():
            text_answers[mapping["question_key"]] = answer_text.strip()

    field_aliases = {
        "contract_type": ("contract_type",),
        "category": ("category",),
        "subcategory": ("subcategory", "sub_category"),
        "reference_label": ("reference_label",),
        "reference_source_label": ("reference_source_label", "settlement_source", "source_label"),
        "reference_asset": ("reference_asset", "asset_symbol"),
        "reference_price": ("reference_price", "opening_price", "reference_value"),
        "price_to_beat": ("price_to_beat", "strike_price", "target_price"),
        "reference_timestamp": ("reference_timestamp", "price_timestamp", "window_start_at"),
        "notes": ("contract_notes", "resolution_notes", "market_notes"),
    }

    contract_metadata: dict[str, object] = {}
    for field_name, aliases in field_aliases.items():
        for alias in aliases:
            if alias in text_answers:
                contract_metadata[field_name] = text_answers[alias]
                break
    return contract_metadata


def _build_market_reference_context(raw_metadata: object) -> MarketReferenceContextResponse | None:
    contract_metadata = _coerce_market_contract_metadata(raw_metadata)
    if not contract_metadata:
        return None

    def _safe_decimal_text(key: str) -> str | None:
        value = contract_metadata.get(key)
        if value is None:
            return None
        try:
            return _decimal_to_str(value)
        except Exception:
            return str(value)

    return MarketReferenceContextResponse(
        contract_type=str(contract_metadata["contract_type"]) if contract_metadata.get("contract_type") else None,
        category=str(contract_metadata["category"]) if contract_metadata.get("category") else None,
        subcategory=str(contract_metadata["subcategory"]) if contract_metadata.get("subcategory") else None,
        reference_label=str(contract_metadata["reference_label"]) if contract_metadata.get("reference_label") else None,
        reference_source_label=str(contract_metadata["reference_source_label"])
        if contract_metadata.get("reference_source_label")
        else None,
        reference_asset=str(contract_metadata["reference_asset"]) if contract_metadata.get("reference_asset") else None,
        reference_symbol=str(contract_metadata["reference_symbol"]) if contract_metadata.get("reference_symbol") else None,
        reference_price=_safe_decimal_text("reference_price"),
        price_to_beat=_safe_decimal_text("price_to_beat"),
        reference_timestamp=_parse_datetime_value(contract_metadata.get("reference_timestamp")),
        notes=str(contract_metadata["notes"]) if contract_metadata.get("notes") else None,
    )


def _market_from_row(row: object, outcomes: list[MarketOutcomeResponse]) -> MarketResponse:
    mapping = row._mapping
    return MarketResponse(
        id=mapping["id"],
        slug=mapping["slug"],
        title=mapping["title"],
        question=mapping["question"],
        description=mapping["description"],
        status=mapping["status"],
        market_access_mode=mapping["market_access_mode"],
        rail_mode=mapping["rail_mode"],
        resolution_mode=mapping["resolution_mode"],
        rules_text=mapping["rules_text"],
        community_id=mapping["community_id"],
        community_slug=mapping.get("community_slug"),
        community_name=mapping.get("community_name"),
        created_from_request_id=mapping["created_from_request_id"],
        creator_id=mapping["creator_id"],
        settlement_source_id=mapping["settlement_source_id"],
        settlement_reference_url=mapping["settlement_reference_url"],
        settlement_reference_label=mapping["settlement_reference_label"],
        settlement_source=MarketSettlementSourceResponse(
            id=mapping["settlement_source_id"],
            code=mapping["settlement_source_code"],
            name=mapping["settlement_source_name"],
            resolution_mode=mapping["settlement_source_resolution_mode"],
            base_url=mapping["settlement_source_base_url"],
        )
        if mapping.get("settlement_source_name")
        else None,
        timing=MarketContractTimesResponse(
            trading_opens_at=mapping["trading_opens_at"],
            trading_closes_at=mapping["trading_closes_at"],
            resolution_due_at=mapping["resolution_due_at"],
            dispute_window_ends_at=mapping["dispute_window_ends_at"],
            activated_at=mapping["activated_at"],
            cancelled_at=mapping["cancelled_at"],
            settled_at=mapping["settled_at"],
        ),
        reference_context=_build_market_reference_context(mapping.get("metadata")),
        min_seed_amount=str(mapping["min_seed_amount"]),
        min_liquidity_amount=_decimal_to_str(mapping["min_liquidity_amount"]),
        min_participants=mapping["min_participants"],
        creator_fee_bps=mapping["creator_fee_bps"],
        platform_fee_bps=mapping["platform_fee_bps"],
        traded_volume=_decimal_to_str(mapping.get("traded_volume")) or "0",
        total_volume=_decimal_to_str(mapping.get("computed_total_volume"))
        or _decimal_to_str(mapping.get("total_volume"))
        or _decimal_to_str(mapping.get("traded_volume"))
        or "0",
        last_price=_decimal_to_str(mapping.get("last_price")),
        total_trades_count=mapping.get("computed_total_trades_count") or mapping.get("total_trades_count") or 0,
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
        outcomes=outcomes,
    )


def _decimal_to_str(value: Decimal | int | float | None) -> str | None:
    if value is None:
        return None
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    normalized = decimal_value.quantize(Decimal("0.00000001"))
    return format(normalized.normalize(), "f")


def _market_quote_from_values(
    outcome_id: UUID,
    outcome_code: str,
    outcome_label: str,
    *,
    last_price: Decimal | None,
    best_bid: Decimal | None,
    best_ask: Decimal | None,
    traded_volume: Decimal | None,
    resting_bid_quantity: Decimal | None,
    resting_ask_quantity: Decimal | None,
) -> MarketQuoteResponse:
    return MarketQuoteResponse(
        outcome_id=outcome_id,
        outcome_code=outcome_code,
        outcome_label=outcome_label,
        last_price=_decimal_to_str(last_price),
        best_bid=_decimal_to_str(best_bid),
        best_ask=_decimal_to_str(best_ask),
        traded_volume=_decimal_to_str(traded_volume or Decimal("0")) or "0",
        resting_bid_quantity=_decimal_to_str(resting_bid_quantity or Decimal("0")) or "0",
        resting_ask_quantity=_decimal_to_str(resting_ask_quantity or Decimal("0")) or "0",
    )


def _market_depth_level_from_row(row: object) -> MarketDepthLevelResponse:
    mapping = row._mapping
    return MarketDepthLevelResponse(
        price=_decimal_to_str(mapping["price"]) or "0",
        quantity=_decimal_to_str(mapping["quantity"]) or "0",
        order_count=int(mapping["order_count"]),
    )


def _market_trade_from_row(row: object) -> MarketTradeResponse:
    mapping = row._mapping
    return MarketTradeResponse(
        id=mapping["id"],
        outcome_id=mapping["outcome_id"],
        outcome_label=mapping["outcome_label"],
        price=_decimal_to_str(mapping["price"]) or "0",
        quantity=_decimal_to_str(mapping["quantity"]) or "0",
        gross_notional=_decimal_to_str(mapping["gross_notional"]) or "0",
        executed_at=mapping["executed_at"],
    )


def _market_history_bucket_from_row(row: object, interval_seconds: int) -> MarketHistoryBucketResponse:
    mapping = row._mapping
    bucket_start = mapping["bucket_start"]
    return MarketHistoryBucketResponse(
        bucket_start=bucket_start,
        bucket_end=bucket_start + timedelta(seconds=interval_seconds),
        open_price=_decimal_to_str(mapping["open_price"]),
        high_price=_decimal_to_str(mapping["high_price"]),
        low_price=_decimal_to_str(mapping["low_price"]),
        close_price=_decimal_to_str(mapping["close_price"]),
        volume=_decimal_to_str(mapping["volume"]) or "0",
        trade_count=int(mapping["trade_count"]),
    )


def _market_order_from_row(row: object) -> MarketOrderResponse:
    mapping = row._mapping
    return MarketOrderResponse(
        id=mapping["id"],
        market_id=mapping["market_id"],
        outcome_id=mapping["outcome_id"],
        outcome_label=mapping["outcome_label"],
        side=mapping["side"],
        order_type=mapping["order_type"],
        status=mapping["status"],
        quantity=_decimal_to_str(mapping["quantity"]) or "0",
        price=_decimal_to_str(mapping["price"]),
        matched_quantity=_decimal_to_str(mapping["matched_quantity"]) or "0",
        remaining_quantity=_decimal_to_str(mapping["remaining_quantity"]) or "0",
        max_total_cost=_decimal_to_str(mapping["max_total_cost"]),
        source=mapping["source"],
        client_order_id=mapping["client_order_id"],
        rejection_reason=mapping["rejection_reason"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


def _portfolio_position_from_row(row: object) -> PortfolioPositionResponse:
    mapping = row._mapping
    return PortfolioPositionResponse(
        market_id=mapping["market_id"],
        market_slug=mapping["market_slug"],
        market_title=mapping["market_title"],
        market_status=mapping["market_status"],
        outcome_id=mapping["outcome_id"],
        outcome_label=mapping["outcome_label"],
        quantity=_decimal_to_str(mapping["quantity"]) or "0",
        average_entry_price=_decimal_to_str(mapping["average_entry_price"]),
        net_cost=_decimal_to_str(mapping["net_cost"]) or "0",
        realized_pnl=_decimal_to_str(mapping["realized_pnl"]) or "0",
        unrealized_pnl=_decimal_to_str(mapping["unrealized_pnl"]) or "0",
        last_trade_at=mapping["last_trade_at"],
    )


def _market_resolution_from_row(row: object) -> MarketResolutionResponse:
    mapping = row._mapping
    final_payload = mapping.get("final_payload") if hasattr(mapping, "get") else None
    resolution_status = None
    if isinstance(final_payload, dict):
        resolution_status = final_payload.get("status")
    return MarketResolutionResponse(
        id=mapping["id"],
        market_id=mapping["market_id"],
        winning_outcome_id=mapping["winning_outcome_id"],
        candidate_id=mapping.get("candidate_id"),
        status=str(resolution_status or ("finalized" if mapping["winning_outcome_id"] else "pending_oracle")),
        resolution_mode=mapping["resolution_mode"],
        settlement_source_id=mapping["settlement_source_id"],
        source_reference_url=mapping["source_reference_url"],
        finalizes_at=mapping.get("finalizes_at"),
        resolved_at=mapping["resolved_at"],
    )


def _market_resolution_candidate_from_row(row: object) -> MarketResolutionCandidateResponse:
    mapping = row._mapping
    return MarketResolutionCandidateResponse(
        id=mapping["id"],
        market_id=mapping["market_id"],
        proposed_outcome_id=mapping["proposed_outcome_id"],
        proposed_by=mapping["proposed_by"],
        settlement_source_id=mapping["settlement_source_id"],
        status=mapping["status"],
        source_reference_url=mapping["source_reference_url"],
        source_reference_text=mapping["source_reference_text"],
        payload=mapping["payload"] or {},
        proposed_at=mapping["proposed_at"],
        reviewed_at=mapping["reviewed_at"],
        reviewed_by=mapping["reviewed_by"],
    )


def _market_dispute_evidence_from_row(row: object) -> MarketDisputeEvidenceResponse:
    mapping = row._mapping
    return MarketDisputeEvidenceResponse(
        id=mapping["id"],
        dispute_id=mapping["dispute_id"],
        submitted_by=mapping["submitted_by"],
        evidence_type=mapping["evidence_type"],
        url=mapping["url"],
        description=mapping["description"],
        payload=mapping["payload"] or {},
        created_at=mapping["created_at"],
    )


def _market_dispute_from_row(
    row: object,
    evidence: list[MarketDisputeEvidenceResponse] | None = None,
) -> MarketDisputeResponse:
    mapping = row._mapping
    return MarketDisputeResponse(
        id=mapping["id"],
        market_id=mapping["market_id"],
        resolution_id=mapping["resolution_id"],
        raised_by=mapping["raised_by"],
        status=mapping["status"],
        title=mapping["title"],
        reason=mapping["reason"],
        fee_amount=_decimal_to_str(mapping["fee_amount"]) or "0",
        opened_at=mapping["opened_at"],
        closed_at=mapping["closed_at"],
        reviewed_by=mapping["reviewed_by"],
        review_notes=mapping["review_notes"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
        evidence=evidence or [],
    )


def _build_resolution_history(
    *,
    current_resolution_row: object | None,
    candidate_rows: list[object],
    dispute_rows: list[object],
    evidence_by_dispute_id: dict[UUID, list[MarketDisputeEvidenceResponse]],
) -> list[MarketResolutionEventResponse]:
    events: list[MarketResolutionEventResponse] = []
    if current_resolution_row is not None:
        resolution_mapping = current_resolution_row._mapping
        final_payload = resolution_mapping["final_payload"] if isinstance(resolution_mapping["final_payload"], dict) else {}
        events.append(
            MarketResolutionEventResponse(
                id=f"resolution:{resolution_mapping['id']}",
                event_type="resolution_state",
                title="Oracle resolution active",
                status=str(final_payload.get("status") or "pending_oracle"),
                occurred_at=resolution_mapping["resolved_at"] or resolution_mapping["created_at"],
                actor_id=resolution_mapping["resolved_by"],
                reference_id=str(resolution_mapping["id"]),
                details={
                    "candidate_id": str(resolution_mapping["candidate_id"]) if resolution_mapping["candidate_id"] else None,
                    "assertion_id": final_payload.get("assertion_id"),
                    "provider": final_payload.get("provider"),
                    "source_reference_url": resolution_mapping["source_reference_url"],
                },
            )
        )
    for row in candidate_rows:
        candidate = _market_resolution_candidate_from_row(row)
        events.append(
            MarketResolutionEventResponse(
                id=f"candidate:{candidate.id}",
                event_type="candidate_created",
                title="Resolution candidate proposed",
                status=candidate.status,
                occurred_at=candidate.proposed_at,
                actor_id=candidate.proposed_by,
                reference_id=str(candidate.id),
                details={
                    "provider": candidate.payload.get("provider"),
                    "assertion_id": candidate.payload.get("assertion_id"),
                    "source_reference_url": candidate.source_reference_url,
                },
            )
        )
        if candidate.reviewed_at is not None:
            events.append(
                MarketResolutionEventResponse(
                    id=f"candidate-review:{candidate.id}",
                    event_type="candidate_reviewed",
                    title="Resolution candidate reviewed",
                    status=candidate.status,
                    occurred_at=candidate.reviewed_at,
                    actor_id=candidate.reviewed_by,
                    reference_id=str(candidate.id),
                    details={},
                )
            )
    for row in dispute_rows:
        dispute = _market_dispute_from_row(row, evidence_by_dispute_id.get(row._mapping["id"], []))
        events.append(
            MarketResolutionEventResponse(
                id=f"dispute:{dispute.id}",
                event_type="dispute_opened",
                title=dispute.title,
                status=dispute.status,
                occurred_at=dispute.opened_at,
                actor_id=dispute.raised_by,
                reference_id=str(dispute.id),
                details={"reason": dispute.reason},
            )
        )
        for evidence in dispute.evidence:
            events.append(
                MarketResolutionEventResponse(
                    id=f"evidence:{evidence.id}",
                    event_type="dispute_evidence_added",
                    title="Dispute evidence attached",
                    status=dispute.status,
                    occurred_at=evidence.created_at,
                    actor_id=evidence.submitted_by,
                    reference_id=str(evidence.id),
                    details={
                        "dispute_id": str(dispute.id),
                        "evidence_type": evidence.evidence_type,
                        "url": evidence.url,
                        "description": evidence.description,
                    },
                )
            )
        if dispute.closed_at is not None:
            events.append(
                MarketResolutionEventResponse(
                    id=f"dispute-review:{dispute.id}",
                    event_type="dispute_reviewed",
                    title="Dispute reviewed",
                    status=dispute.status,
                    occurred_at=dispute.closed_at,
                    actor_id=dispute.reviewed_by,
                    reference_id=str(dispute.id),
                    details={"review_notes": dispute.review_notes},
                )
            )
    return sorted(events, key=lambda item: item.occurred_at, reverse=True)


def _merge_contract_metadata(
    *,
    template_metadata: dict[str, object],
    snapshot_metadata: dict[str, object],
    explicit_metadata: dict[str, object],
) -> dict[str, object]:
    return {
        **template_metadata,
        **snapshot_metadata,
        **{key: value for key, value in explicit_metadata.items() if value not in (None, "")},
    }


async def _get_or_create_ledger_account(
    session,
    *,
    account_code: str,
    owner_type: str,
    asset_id: UUID,
    rail_mode: str,
    owner_profile_id: UUID | None = None,
    owner_market_id: UUID | None = None,
    is_system: bool = False,
    metadata: dict | None = None,
) -> UUID:
    existing_result = await session.execute(
        select(ledger_accounts.c.id).where(ledger_accounts.c.account_code == account_code)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    insert_result = await session.execute(
        insert(ledger_accounts)
        .values(
            account_code=account_code,
            owner_type=owner_type,
            owner_profile_id=owner_profile_id,
            owner_market_id=owner_market_id,
            asset_id=asset_id,
            rail_mode=rail_mode,
            is_system=is_system,
            metadata=metadata or {},
        )
        .returning(ledger_accounts.c.id)
    )
    return insert_result.scalar_one()


async def _get_asset_id_by_code(session, asset_code: str) -> UUID:
    asset_result = await session.execute(select(assets.c.id).where(assets.c.code == asset_code))
    asset_id = asset_result.scalar_one_or_none()
    if asset_id is None:
        raise ConflictError(f"No asset is configured for code {asset_code}")
    return asset_id


class PostgresProfileRepository(ProfileRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
    ) -> ProfileResponse:
        async with self._session_factory() as session:
            result = await session.execute(select(profiles).where(profiles.c.id == actor_id))
            row = result.first()
            if row is not None:
                return _profile_from_row(row)
        return ProfileResponse(
            id=actor_id,
            username=username,
            display_name=display_name,
            bio=None,
            avatar_url=None,
            is_admin=is_admin,
        )

    async def get_profile_by_username(self, username: str) -> ProfileResponse:
        async with self._session_factory() as session:
            result = await session.execute(select(profiles).where(profiles.c.username == username))
            row = result.first()
            if row is None:
                raise NotFoundError("Profile not found")
            return _profile_from_row(row)

    async def update_current_profile(
        self,
        actor_id: UUID,
        username: str,
        display_name: str,
        is_admin: bool,
        payload: ProfileUpdateRequest,
    ) -> ProfileResponse:
        values = {
            "id": actor_id,
            "username": username,
            "display_name": payload.display_name or display_name,
            "bio": payload.bio,
            "avatar_url": payload.avatar_url,
            "is_admin": is_admin,
        }
        async with self._session_factory() as session:
            result = await session.execute(
                pg_insert(profiles)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[profiles.c.id],
                    set_={
                        "username": values["username"],
                        "display_name": values["display_name"],
                        "bio": values["bio"],
                        "avatar_url": values["avatar_url"],
                        "is_admin": values["is_admin"],
                    },
                )
                .returning(profiles)
            )
            row = result.first()
            await session.commit()
            return _profile_from_row(row)

    async def list_wallets(self, actor_id: UUID) -> list[UserWalletResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(user_wallets)
                .where(user_wallets.c.profile_id == actor_id)
                .order_by(user_wallets.c.is_primary.desc(), user_wallets.c.created_at.asc())
            )
            return [_wallet_from_row(row) for row in result.fetchall()]

    async def create_wallet(self, actor_id: UUID, payload: WalletCreateRequest) -> UserWalletResponse:
        async with self._session_factory() as session:
            if payload.is_primary:
                await session.execute(
                    update(user_wallets)
                    .where(user_wallets.c.profile_id == actor_id)
                    .values(is_primary=False)
                )
            try:
                result = await session.execute(
                    insert(user_wallets)
                    .values(
                        profile_id=actor_id,
                        chain_name=payload.chain_name,
                        wallet_address=payload.wallet_address,
                        is_primary=payload.is_primary,
                        metadata={},
                    )
                    .returning(user_wallets)
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Wallet already exists") from exc
            row = result.first()
            await session.commit()
            return _wallet_from_row(row)

    async def update_wallet(
        self,
        actor_id: UUID,
        wallet_id: UUID,
        payload: WalletUpdateRequest,
    ) -> UserWalletResponse:
        async with self._session_factory() as session:
            if payload.is_primary:
                await session.execute(
                    update(user_wallets)
                    .where(user_wallets.c.profile_id == actor_id)
                    .values(is_primary=False)
                )
            result = await session.execute(
                update(user_wallets)
                .where(and_(user_wallets.c.id == wallet_id, user_wallets.c.profile_id == actor_id))
                .values(is_primary=payload.is_primary)
                .returning(user_wallets)
            )
            row = result.first()
            if row is None:
                await session.rollback()
                raise NotFoundError("Wallet not found")
            await session.commit()
            return _wallet_from_row(row)

    async def delete_wallet(self, actor_id: UUID, wallet_id: UUID) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(user_wallets)
                .where(and_(user_wallets.c.id == wallet_id, user_wallets.c.profile_id == actor_id))
                .returning(user_wallets.c.id)
            )
            if result.first() is None:
                await session.rollback()
                raise NotFoundError("Wallet not found")
            await session.commit()


class PostgresCommunityRepository(CommunityRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_communities(self, actor_id: UUID, actor_is_admin: bool) -> list[CommunityResponse]:
        async with self._session_factory() as session:
            if actor_is_admin:
                stmt = select(communities).order_by(communities.c.created_at.desc())
            else:
                membership = community_members.alias("membership")
                stmt = (
                    select(communities)
                    .select_from(
                        communities.outerjoin(
                            membership,
                            and_(
                                membership.c.community_id == communities.c.id,
                                membership.c.profile_id == actor_id,
                            ),
                        )
                    )
                    .where(
                        or_(
                            communities.c.visibility == "public",
                            communities.c.created_by == actor_id,
                            membership.c.id.is_not(None),
                        )
                    )
                    .order_by(communities.c.created_at.desc())
                )
            result = await session.execute(stmt)
            return [_community_from_row(row) for row in result.fetchall()]

    async def create_community(self, actor_id: UUID, payload: CommunityCreateRequest) -> CommunityResponse:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    insert(communities)
                    .values(
                        slug=payload.slug,
                        name=payload.name,
                        description=payload.description,
                        visibility=payload.visibility,
                        require_post_approval=payload.require_post_approval,
                        require_market_approval=payload.require_market_approval,
                        created_by=actor_id,
                    )
                    .returning(communities)
                )
                community_row = result.first()
                await session.execute(
                    insert(community_members).values(
                        community_id=community_row._mapping["id"],
                        profile_id=actor_id,
                        role="owner",
                    )
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Community slug already exists") from exc
            await session.commit()
            return _community_from_row(community_row)

    async def get_community(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> CommunityResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            return _community_from_row(context["row"])

    async def update_community(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityUpdateRequest,
    ) -> CommunityResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not context["is_staff"]:
                raise ForbiddenError("You do not have permission to update this community")
            current = context["row"]._mapping
            await session.execute(
                update(communities)
                .where(communities.c.id == current["id"])
                .values(
                    name=payload.name or current["name"],
                    description=payload.description if payload.description is not None else current["description"],
                    visibility=payload.visibility or current["visibility"],
                    require_post_approval=(
                        payload.require_post_approval
                        if payload.require_post_approval is not None
                        else current["require_post_approval"]
                    ),
                    require_market_approval=(
                        payload.require_market_approval
                        if payload.require_market_approval is not None
                        else current["require_market_approval"]
                    ),
                )
            )
            refreshed = await session.execute(select(communities).where(communities.c.id == current["id"]))
            await session.commit()
            return _community_from_row(refreshed.first())

    async def list_members(self, slug: str, actor_id: UUID, actor_is_admin: bool) -> list[CommunityMemberResponse]:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            stmt = (
                select(
                    community_members.c.id,
                    community_members.c.profile_id,
                    community_members.c.role,
                    profiles.c.username,
                    profiles.c.display_name,
                )
                .select_from(community_members.join(profiles, community_members.c.profile_id == profiles.c.id))
                .where(community_members.c.community_id == context["row"]._mapping["id"])
                .order_by(community_members.c.joined_at.asc())
            )
            result = await session.execute(stmt)
            return [_member_from_row(row) for row in result.fetchall()]

    async def add_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: CommunityMemberCreateRequest,
    ) -> CommunityMemberResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not (
                actor_is_admin
                or context["is_staff"]
                or (payload.profile_id == actor_id and context["row"]._mapping["visibility"] == "public")
            ):
                raise ForbiddenError("You do not have permission to add members to this community")
            try:
                result = await session.execute(
                    insert(community_members)
                    .values(
                        community_id=context["row"]._mapping["id"],
                        profile_id=payload.profile_id,
                        role=payload.role,
                    )
                    .returning(community_members.c.id, community_members.c.profile_id, community_members.c.role)
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Community member already exists") from exc
            inserted = result.first()
            profile_result = await session.execute(
                select(profiles.c.username, profiles.c.display_name).where(profiles.c.id == payload.profile_id)
            )
            profile_row = profile_result.first()
            await session.commit()
            return CommunityMemberResponse(
                id=inserted._mapping["id"],
                profile_id=inserted._mapping["profile_id"],
                username=profile_row._mapping["username"] if profile_row else "unknown",
                display_name=profile_row._mapping["display_name"] if profile_row else "Unknown",
                role=inserted._mapping["role"],
            )

    async def update_member(
        self,
        slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        member_id: UUID,
        payload: CommunityMemberUpdateRequest,
    ) -> CommunityMemberResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not context["is_staff"]:
                raise ForbiddenError("You do not have permission to update community members")
            result = await session.execute(
                update(community_members)
                .where(
                    and_(
                        community_members.c.id == member_id,
                        community_members.c.community_id == context["row"]._mapping["id"],
                    )
                )
                .values(role=payload.role)
                .returning(
                    community_members.c.id,
                    community_members.c.profile_id,
                    community_members.c.role,
                )
            )
            row = result.first()
            if row is None:
                await session.rollback()
                raise NotFoundError("Member not found")
            profile_result = await session.execute(
                select(profiles.c.username, profiles.c.display_name)
                .where(profiles.c.id == row._mapping["profile_id"])
            )
            profile_row = profile_result.first()
            await session.commit()
            return CommunityMemberResponse(
                id=row._mapping["id"],
                profile_id=row._mapping["profile_id"],
                username=profile_row._mapping["username"] if profile_row else "unknown",
                display_name=profile_row._mapping["display_name"] if profile_row else "Unknown",
                role=row._mapping["role"],
            )

    async def delete_member(self, slug: str, actor_id: UUID, actor_is_admin: bool, member_id: UUID) -> None:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, slug, actor_id, actor_is_admin)
            if not context["is_staff"]:
                raise ForbiddenError("You do not have permission to remove community members")
            result = await session.execute(
                delete(community_members)
                .where(
                    and_(
                        community_members.c.id == member_id,
                        community_members.c.community_id == context["row"]._mapping["id"],
                    )
                )
                .returning(community_members.c.id)
            )
            if result.first() is None:
                await session.rollback()
                raise NotFoundError("Member not found")
            await session.commit()

    async def _get_community_context(self, session, slug: str, actor_id: UUID, actor_is_admin: bool) -> dict[str, object]:
        result = await session.execute(select(communities).where(communities.c.slug == slug))
        row = result.first()
        if row is None:
            raise NotFoundError("Community not found")
        mapping = row._mapping
        role: str | None = None
        if not actor_is_admin:
            membership = await session.execute(
                select(community_members.c.role).where(
                    and_(
                        community_members.c.community_id == mapping["id"],
                        community_members.c.profile_id == actor_id,
                    )
                )
            )
            membership_row = membership.first()
            role = membership_row._mapping["role"] if membership_row else None
        can_read = actor_is_admin or mapping["visibility"] == "public" or mapping["created_by"] == actor_id or role is not None
        if not can_read:
            raise ForbiddenError("You do not have access to this community")
        is_staff = actor_is_admin or mapping["created_by"] == actor_id or role in {"moderator", "admin", "owner"}
        return {"row": row, "is_staff": is_staff}


class PostgresPostRepository(PostRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_posts(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> list[PostResponse]:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, community_slug, actor_id, actor_is_admin)
            stmt = self._post_select_stmt().where(posts.c.community_id == context["community_id"])
            if not context["is_staff"]:
                stmt = stmt.where(or_(posts.c.status == "approved", posts.c.author_id == actor_id))
            stmt = stmt.order_by(posts.c.created_at.desc())
            result = await session.execute(stmt)
            return [_post_from_row(row) for row in result.fetchall()]

    async def create_post(
        self,
        community_slug: str,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: PostCreateRequest,
    ) -> PostResponse:
        async with self._session_factory() as session:
            context = await self._get_community_context(session, community_slug, actor_id, actor_is_admin)
            auto_approved = not context["require_post_approval"] or context["is_staff"]
            values = {
                "community_id": context["community_id"],
                "author_id": actor_id,
                "title": payload.title,
                "body": payload.body,
                "status": "approved" if auto_approved else "pending_review",
                "submitted_at": func.now(),
                "metadata": {},
            }
            if context["require_post_approval"] and context["is_staff"]:
                values["reviewed_at"] = func.now()
                values["reviewed_by"] = actor_id
            result = await session.execute(insert(posts).values(**values).returning(posts.c.id))
            post_id = result.scalar_one()
            row = await self._fetch_post(session, post_id)
            await session.commit()
            return _post_from_row(row)

    async def list_pending_posts(self) -> list[PostResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._post_select_stmt()
                .where(posts.c.status == "pending_review")
                .order_by(posts.c.submitted_at.desc().nullslast(), posts.c.created_at.desc())
            )
            return [_post_from_row(row) for row in result.fetchall()]

    async def review_post(
        self,
        post_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> PostResponse:
        async with self._session_factory() as session:
            current_result = await session.execute(select(posts.c.status).where(posts.c.id == post_id))
            current = current_result.first()
            if current is None:
                raise NotFoundError("Post not found")
            if current._mapping["status"] != "pending_review":
                raise ConflictError("Only pending posts can be reviewed")
            await session.execute(
                update(posts)
                .where(posts.c.id == post_id)
                .values(
                    status="approved" if approved else "rejected",
                    reviewed_at=func.now(),
                    reviewed_by=reviewer_id,
                    review_notes=review_notes,
                )
            )
            row = await self._fetch_post(session, post_id)
            await session.commit()
            return _post_from_row(row)

    def _post_select_stmt(self):
        author_profiles = profiles.alias("author_profiles")
        community_alias = communities.alias("post_communities")
        return (
            select(
                posts,
                author_profiles.c.username.label("author_username"),
                author_profiles.c.display_name.label("author_display_name"),
                community_alias.c.slug.label("community_slug"),
                community_alias.c.name.label("community_name"),
            )
            .select_from(
                posts.join(author_profiles, posts.c.author_id == author_profiles.c.id).join(
                    community_alias, posts.c.community_id == community_alias.c.id
                )
            )
        )

    async def _fetch_post(self, session, post_id: UUID):
        result = await session.execute(self._post_select_stmt().where(posts.c.id == post_id))
        row = result.first()
        if row is None:
            raise NotFoundError("Post not found")
        return row

    async def _get_community_context(self, session, community_slug: str, actor_id: UUID, actor_is_admin: bool) -> dict[str, object]:
        result = await session.execute(select(communities).where(communities.c.slug == community_slug))
        row = result.first()
        if row is None:
            raise NotFoundError("Community not found")
        mapping = row._mapping
        role: str | None = None
        if not actor_is_admin:
            membership = await session.execute(
                select(community_members.c.role).where(
                    and_(
                        community_members.c.community_id == mapping["id"],
                        community_members.c.profile_id == actor_id,
                    )
                )
            )
            membership_row = membership.first()
            role = membership_row._mapping["role"] if membership_row else None
        can_read = actor_is_admin or mapping["visibility"] == "public" or mapping["created_by"] == actor_id or role is not None
        if not can_read:
            raise ForbiddenError("You do not have access to this community")
        return {
            "community_id": mapping["id"],
            "require_post_approval": mapping["require_post_approval"],
            "is_staff": actor_is_admin or mapping["created_by"] == actor_id or role in {"moderator", "admin", "owner"},
        }


class PostgresMarketRequestRepository(MarketRequestRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_requests(self, requester_id: UUID) -> list[MarketRequestResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._market_request_select_stmt()
                .where(market_creation_requests.c.requester_id == requester_id)
                .order_by(market_creation_requests.c.created_at.desc())
            )
            return [_market_request_from_row(row) for row in result.fetchall()]

    async def list_pending_requests(self) -> list[MarketRequestResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._market_request_select_stmt()
                .where(market_creation_requests.c.status.in_(("submitted", "approved")))
                .order_by(
                    market_creation_requests.c.reviewed_at.desc().nullslast(),
                    market_creation_requests.c.submitted_at.desc().nullslast(),
                    market_creation_requests.c.created_at.desc(),
                )
            )
            return [_market_request_from_row(row) for row in result.fetchall()]

    async def create_request(
        self,
        requester_id: UUID,
        payload: MarketRequestCreateRequest,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    insert(market_creation_requests)
                    .values(
                        requester_id=requester_id,
                        community_id=payload.community_id,
                        title=payload.title,
                        slug=payload.slug,
                        question=payload.question,
                        description=payload.description,
                        market_access_mode=payload.market_access_mode,
                        requested_rail=payload.requested_rail,
                        settlement_source_id=payload.settlement_source_id,
                        settlement_reference_url=payload.settlement_reference_url,
                        resolution_mode=payload.resolution_mode,
                        status="draft",
                        metadata={
                            "template_key": payload.template_key,
                            "template_config": payload.template_config.model_dump(mode="json")
                            if payload.template_config is not None
                            else None,
                        },
                    )
                    .returning(market_creation_requests.c.id)
                )
            except IntegrityError as exc:
                await session.rollback()
                raise ConflictError("Market request slug already exists") from exc
            request_id = result.scalar_one()
            row = await self._fetch_request(session, request_id, requester_id)
            await session.commit()
            return _market_request_from_row(row)

    async def get_request(self, request_id: UUID, requester_id: UUID | None = None) -> MarketRequestResponse:
        async with self._session_factory() as session:
            row = await self._fetch_request(session, request_id, requester_id)
            return _market_request_from_row(row)

    async def update_request(
        self,
        request_id: UUID,
        requester_id: UUID,
        payload: MarketRequestUpdateRequest,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            current = await self._get_owned_request_row(session, request_id, requester_id)
            mapping = current._mapping
            if mapping["status"] != "draft":
                raise ConflictError("Only draft market requests can be updated")
            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(
                    title=payload.title or mapping["title"],
                    question=payload.question or mapping["question"],
                    description=payload.description if payload.description is not None else mapping["description"],
                    settlement_reference_url=(
                        payload.settlement_reference_url
                        if payload.settlement_reference_url is not None
                        else mapping["settlement_reference_url"]
                    ),
                )
            )
            row = await self._fetch_request(session, request_id, requester_id)
            await session.commit()
            return _market_request_from_row(row)

    async def upsert_answer(
        self,
        request_id: UUID,
        requester_id: UUID,
        question_key: str,
        payload: MarketRequestAnswerUpsertRequest,
    ) -> MarketRequestAnswerResponse:
        async with self._session_factory() as session:
            current = await self._get_owned_request_row(session, request_id, requester_id)
            if current._mapping["status"] != "draft":
                raise ConflictError("Only draft market requests can be edited")
            existing = await session.execute(
                select(market_creation_request_answers)
                .where(
                    and_(
                        market_creation_request_answers.c.market_request_id == request_id,
                        market_creation_request_answers.c.question_key == question_key,
                    )
                )
            )
            if existing.first() is None:
                result = await session.execute(
                    insert(market_creation_request_answers)
                    .values(
                        market_request_id=request_id,
                        question_key=question_key,
                        question_label=payload.question_label,
                        answer_text=payload.answer_text,
                        answer_json=payload.answer_json,
                    )
                    .returning(market_creation_request_answers)
                )
            else:
                result = await session.execute(
                    update(market_creation_request_answers)
                    .where(
                        and_(
                            market_creation_request_answers.c.market_request_id == request_id,
                            market_creation_request_answers.c.question_key == question_key,
                        )
                    )
                    .values(
                        question_label=payload.question_label,
                        answer_text=payload.answer_text,
                        answer_json=payload.answer_json,
                    )
                    .returning(market_creation_request_answers)
                )
            row = result.first()
            await session.commit()
            return _market_request_answer_from_row(row)

    async def ensure_exists(self, request_id: UUID, requester_id: UUID | None = None) -> None:
        async with self._session_factory() as session:
            await self._fetch_request(session, request_id, requester_id)

    async def list_answers(
        self,
        request_id: UUID,
        requester_id: UUID | None = None,
    ) -> list[MarketRequestAnswerResponse]:
        async with self._session_factory() as session:
            await self._fetch_request(session, request_id, requester_id)
            result = await session.execute(
                select(market_creation_request_answers)
                .where(market_creation_request_answers.c.market_request_id == request_id)
                .order_by(market_creation_request_answers.c.question_key.asc())
            )
            return [_market_request_answer_from_row(row) for row in result.fetchall()]

    async def submit_request(
        self,
        request_id: UUID,
        requester_id: UUID,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            current = await self._get_owned_request_row(session, request_id, requester_id)
            if current._mapping["status"] != "draft":
                raise ConflictError("Only draft market requests can be submitted")
            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(status="submitted", submitted_at=func.now())
            )
            row = await self._fetch_request(session, request_id, requester_id)
            await session.commit()
            return _market_request_from_row(row)

    async def review_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        review_notes: str | None,
    ) -> MarketRequestResponse:
        async with self._session_factory() as session:
            current_result = await session.execute(
                select(market_creation_requests.c.status).where(market_creation_requests.c.id == request_id)
            )
            current = current_result.first()
            if current is None:
                raise NotFoundError("Market request not found")
            if current._mapping["status"] != "submitted":
                raise ConflictError("Only submitted market requests can be reviewed")
            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(
                    status="approved" if approved else "rejected",
                    reviewed_at=func.now(),
                    reviewed_by=reviewer_id,
                    review_notes=review_notes,
                )
            )
            row = await self._fetch_request(session, request_id)
            await session.commit()
            return _market_request_from_row(row)

    def _market_request_select_stmt(self):
        requester_profiles = profiles.alias("requester_profiles")
        community_alias = communities.alias("request_communities")
        return (
            select(
                market_creation_requests,
                requester_profiles.c.username.label("requester_username"),
                requester_profiles.c.display_name.label("requester_display_name"),
                community_alias.c.slug.label("community_slug"),
                community_alias.c.name.label("community_name"),
            )
            .select_from(
                market_creation_requests.join(
                    requester_profiles,
                    market_creation_requests.c.requester_id == requester_profiles.c.id,
                ).outerjoin(community_alias, market_creation_requests.c.community_id == community_alias.c.id)
            )
        )

    async def _fetch_request(self, session, request_id: UUID, requester_id: UUID | None = None):
        stmt = self._market_request_select_stmt().where(market_creation_requests.c.id == request_id)
        if requester_id is not None:
            stmt = stmt.where(market_creation_requests.c.requester_id == requester_id)
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            raise NotFoundError("Market request not found")
        return row

    async def _get_owned_request_row(self, session, request_id: UUID, requester_id: UUID):
        result = await session.execute(
            select(market_creation_requests).where(
                and_(
                    market_creation_requests.c.id == request_id,
                    market_creation_requests.c.requester_id == requester_id,
                )
            )
        )
        row = result.first()
        if row is None:
            raise NotFoundError("Market request not found")
        return row


class PostgresMarketRepository(MarketRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker,
        market_data_service: MarketDataService | None = None,
        oracle_service: OracleService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._market_data_service = market_data_service
        self._oracle_service = oracle_service

    async def publish_from_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        review_notes: str | None,
    ) -> MarketResponse:
        async with self._session_factory() as session:
            request_result = await session.execute(
                select(market_creation_requests).where(market_creation_requests.c.id == request_id)
            )
            request_row = request_result.first()
            if request_row is None:
                raise NotFoundError("Market request not found")
            request_mapping = request_row._mapping
            if request_mapping["status"] not in {"submitted", "approved"}:
                raise ConflictError("Only submitted or approved market requests can be published")
            existing_market = await session.execute(
                select(markets.c.id, markets.c.slug).where(markets.c.created_from_request_id == request_id)
            )
            existing_market_row = existing_market.first()
            if existing_market_row is not None:
                raise ConflictError("A market has already been created from this request")
            if request_mapping["requested_rail"] is None:
                raise ConflictError("Market request is missing a requested rail")

            settlement_source_id = request_mapping["settlement_source_id"]
            settlement_source_name: str | None = None
            if settlement_source_id is None:
                source_result = await session.execute(
                    select(settlement_sources.c.id, settlement_sources.c.name).where(
                        settlement_sources.c.resolution_mode == request_mapping["resolution_mode"]
                    )
                )
                source_row = source_result.first()
                if source_row is None:
                    raise ConflictError("No settlement source is available for this request")
                settlement_source_id = source_row._mapping["id"]
                settlement_source_name = source_row._mapping["name"]
            else:
                source_result = await session.execute(
                    select(settlement_sources.c.name).where(settlement_sources.c.id == settlement_source_id)
                )
                settlement_source_name = source_result.scalar_one_or_none()

            request_answers_result = await session.execute(
                select(market_creation_request_answers).where(
                    market_creation_request_answers.c.market_request_id == request_id
                )
            )
            template_contract_metadata = {}
            request_metadata = request_mapping.get("metadata")
            if isinstance(request_metadata, dict):
                template_contract_metadata = build_contract_metadata_from_template(
                    request_metadata.get("template_key"),
                    request_metadata.get("template_config"),
                )
            explicit_contract_metadata = _extract_contract_answer_metadata(request_answers_result.fetchall())
            snapshot_metadata: dict[str, object] = {}
            request_metadata = request_mapping.get("metadata")
            template_config = request_metadata.get("template_config") if isinstance(request_metadata, dict) else None
            if self._market_data_service is not None:
                snapshot = await self._market_data_service.get_reference_snapshot(
                    template_key=request_metadata.get("template_key") if isinstance(request_metadata, dict) else None,
                    template_config=template_config if isinstance(template_config, dict) else None,
                    contract_metadata=template_contract_metadata,
                )
                if snapshot is not None:
                    snapshot_metadata = snapshot.as_contract_metadata()
                    if request_mapping["settlement_reference_url"] is None and snapshot.source_reference_url:
                        request_mapping = {
                            **request_mapping,
                            "settlement_reference_url": snapshot.source_reference_url,
                        }

            contract_metadata = _merge_contract_metadata(
                template_metadata=template_contract_metadata,
                snapshot_metadata=snapshot_metadata,
                explicit_metadata=explicit_contract_metadata,
            )

            rules_text = self._build_rules_text(request_mapping, review_notes)
            market_insert = await session.execute(
                insert(markets)
                .values(
                    community_id=request_mapping["community_id"],
                    created_from_request_id=request_id,
                    creator_id=request_mapping["requester_id"],
                    settlement_source_id=settlement_source_id,
                    slug=normalize_slug(
                        request_mapping["slug"],
                        fallback=request_mapping["title"] or f"market-{str(request_id).split('-')[0]}",
                    )
                    or f"market-{str(request_id).split('-')[0]}",
                    title=request_mapping["title"],
                    question=request_mapping["question"],
                    description=request_mapping["description"],
                    rules_text=rules_text,
                    market_access_mode=request_mapping["market_access_mode"],
                    rail_mode=request_mapping["requested_rail"],
                    status="pending_liquidity",
                    resolution_mode=request_mapping["resolution_mode"],
                    settlement_reference_url=request_mapping["settlement_reference_url"],
                    settlement_reference_label=settlement_source_name,
                    trading_opens_at=func.now(),
                    trading_closes_at=request_mapping["expires_at"],
                    resolution_due_at=request_mapping["expires_at"],
                    min_seed_amount=request_mapping["min_seed_amount"] or 0,
                    min_liquidity_amount=request_mapping["min_seed_amount"] or 0,
                    min_participants=request_mapping["min_participants"] or 2,
                    metadata={
                        "published_from_request": str(request_id),
                        "contract": contract_metadata,
                    },
                )
                .returning(markets.c.id, markets.c.slug)
            )
            market_row = market_insert.first()
            market_id = market_row._mapping["id"]

            for outcome_index, outcome in enumerate((("YES", "Yes"), ("NO", "No"))):
                await session.execute(
                    insert(market_outcomes).values(
                        market_id=market_id,
                        code=outcome[0],
                        label=outcome[1],
                        outcome_index=outcome_index,
                        status="active",
                    )
                )

            await session.execute(
                update(market_creation_requests)
                .where(market_creation_requests.c.id == request_id)
                .values(
                    status="converted",
                    reviewed_at=func.now(),
                    reviewed_by=reviewer_id,
                    review_notes=review_notes,
                )
            )
            market = await self._fetch_market(session, market_row._mapping["slug"])
            await session.commit()
            return market

    async def list_markets(self) -> list[MarketResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                self._market_select_stmt().order_by(markets.c.created_at.desc())
            )
            rows = result.fetchall()
            return [await self._hydrate_market(session, row) for row in rows]

    async def get_market(self, slug: str) -> MarketResponse:
        async with self._session_factory() as session:
            return await self._fetch_market(session, slug)

    async def update_market_status(self, slug: str, status: str) -> MarketResponse:
        allowed_next_statuses = {
            "pending_liquidity": {"open", "cancelled"},
            "open": {"trading_paused", "cancelled"},
            "trading_paused": {"open", "cancelled"},
        }
        async with self._session_factory() as session:
            current_result = await session.execute(select(markets.c.status).where(markets.c.slug == slug))
            current_status = current_result.scalar_one_or_none()
            if current_status is None:
                raise NotFoundError("Market not found")
            if status not in allowed_next_statuses.get(current_status, set()):
                raise ConflictError(f"Cannot transition market from {current_status} to {status}")
            update_values: dict[str, object] = {
                "status": status,
                "updated_at": func.now(),
            }
            if status == "open":
                update_values["activated_at"] = func.coalesce(markets.c.activated_at, func.now())
            if status == "cancelled":
                update_values["cancelled_at"] = func.now()
            await session.execute(
                update(markets)
                .where(markets.c.slug == slug)
                .values(**update_values)
            )
            market = await self._fetch_market(session, slug)
            await session.commit()
            return market

    async def get_market_resolution_state(self, slug: str) -> MarketResolutionStateResponse:
        async with self._session_factory() as session:
            market_result = await session.execute(select(markets.c.id, markets.c.slug).where(markets.c.slug == slug))
            market_row = market_result.first()
            if market_row is None:
                raise NotFoundError("Market not found")
            market_id = market_row._mapping["id"]

            resolution_result = await session.execute(
                select(market_resolutions)
                .where(market_resolutions.c.market_id == market_id)
                .order_by(market_resolutions.c.created_at.desc())
            )
            current_resolution_row = resolution_result.first()

            candidates_result = await session.execute(
                select(market_resolution_candidates)
                .where(market_resolution_candidates.c.market_id == market_id)
                .order_by(market_resolution_candidates.c.proposed_at.desc())
            )
            candidate_rows = candidates_result.fetchall()
            disputes_result = await session.execute(
                select(disputes)
                .where(disputes.c.market_id == market_id)
                .order_by(disputes.c.created_at.desc())
            )
            dispute_rows = disputes_result.fetchall()
            evidence_by_dispute_id: dict[UUID, list[MarketDisputeEvidenceResponse]] = {}
            if dispute_rows:
                evidence_result = await session.execute(
                    select(dispute_evidence)
                    .where(dispute_evidence.c.dispute_id.in_([row._mapping["id"] for row in dispute_rows]))
                    .order_by(dispute_evidence.c.created_at.asc())
                )
                for evidence_row in evidence_result.fetchall():
                    evidence = _market_dispute_evidence_from_row(evidence_row)
                    evidence_by_dispute_id.setdefault(evidence.dispute_id, []).append(evidence)
            current_resolution = _market_resolution_from_row(current_resolution_row) if current_resolution_row else None
            current_payload = (
                current_resolution_row._mapping["final_payload"]
                if current_resolution_row is not None and isinstance(current_resolution_row._mapping["final_payload"], dict)
                else {}
            )
            return MarketResolutionStateResponse(
                market_id=market_id,
                market_slug=market_row._mapping["slug"],
                current_resolution_id=current_resolution.id if current_resolution else None,
                current_status=current_resolution.status if current_resolution else None,
                current_payload=current_payload,
                candidate_id=current_resolution.candidate_id if current_resolution else None,
                winning_outcome_id=current_resolution.winning_outcome_id if current_resolution else None,
                source_reference_url=current_resolution.source_reference_url if current_resolution else None,
                finalizes_at=current_resolution.finalizes_at if current_resolution else None,
                resolved_at=current_resolution.resolved_at if current_resolution else None,
                candidates=[_market_resolution_candidate_from_row(row) for row in candidate_rows],
                disputes=[
                    _market_dispute_from_row(row, evidence_by_dispute_id.get(row._mapping["id"], []))
                    for row in dispute_rows
                ],
                history=_build_resolution_history(
                    current_resolution_row=current_resolution_row,
                    candidate_rows=list(candidate_rows),
                    dispute_rows=list(dispute_rows),
                    evidence_by_dispute_id=evidence_by_dispute_id,
                ),
            )

    async def create_market_dispute(
        self,
        slug: str,
        actor_id: UUID,
        payload: MarketDisputeCreateRequest,
    ) -> MarketDisputeResponse:
        async with self._session_factory() as session:
            market_result = await session.execute(select(markets).where(markets.c.slug == slug))
            market_row = market_result.first()
            if market_row is None:
                raise NotFoundError("Market not found")
            market_mapping = market_row._mapping
            if market_mapping["status"] not in {"awaiting_resolution", "disputed"}:
                raise ConflictError("Disputes can only be raised while oracle resolution is pending")

            resolution_result = await session.execute(
                select(market_resolutions)
                .where(market_resolutions.c.market_id == market_mapping["id"])
                .order_by(market_resolutions.c.created_at.desc())
            )
            resolution_row = resolution_result.first()
            if resolution_row is None:
                raise ConflictError("No active resolution candidate exists for this market")
            existing_open_dispute = await session.execute(
                select(disputes.c.id)
                .where(
                    and_(
                        disputes.c.market_id == market_mapping["id"],
                        disputes.c.resolution_id == resolution_row._mapping["id"],
                        disputes.c.status.in_(["open", "under_review"]),
                    )
                )
                .limit(1)
            )
            if existing_open_dispute.scalar_one_or_none() is not None:
                raise ConflictError("An open dispute already exists for the active resolution candidate")

            dispute_insert = await session.execute(
                insert(disputes)
                .values(
                    market_id=market_mapping["id"],
                    resolution_id=resolution_row._mapping["id"],
                    raised_by=actor_id,
                    status="open",
                    title=payload.title,
                    reason=payload.reason,
                    fee_amount=Decimal("0"),
                    opened_at=func.now(),
                    created_at=func.now(),
                    updated_at=func.now(),
                )
                .returning(disputes)
            )
            dispute_row = dispute_insert.first()

            await session.execute(
                update(markets)
                .where(markets.c.id == market_mapping["id"])
                .values(
                    status="disputed",
                    updated_at=func.now(),
                )
            )
            await session.execute(
                update(market_resolutions)
                .where(market_resolutions.c.id == resolution_row._mapping["id"])
                .values(
                    final_payload={
                        **(resolution_row._mapping["final_payload"] or {}),
                        "status": "disputed",
                        "latest_dispute_id": str(dispute_row._mapping["id"]),
                    }
                )
            )
            candidate_id = resolution_row._mapping["candidate_id"]
            if candidate_id is not None:
                await session.execute(
                    update(market_resolution_candidates)
                    .where(market_resolution_candidates.c.id == candidate_id)
                    .values(
                        status="rejected",
                        reviewed_at=func.now(),
                        reviewed_by=actor_id,
                    )
                )
            await session.commit()
            return _market_dispute_from_row(dispute_row)

    async def add_market_dispute_evidence(
        self,
        slug: str,
        dispute_id: UUID,
        actor_id: UUID,
        payload: MarketDisputeEvidenceCreateRequest,
    ) -> MarketDisputeResponse:
        async with self._session_factory() as session:
            dispute_row, _market_row = await self._fetch_dispute_for_market(session, slug, dispute_id)
            if dispute_row._mapping["status"] not in {"open", "under_review"}:
                raise ConflictError("Evidence can only be attached while a dispute is open or under review")

            await session.execute(
                insert(dispute_evidence).values(
                    dispute_id=dispute_id,
                    submitted_by=actor_id,
                    evidence_type=payload.evidence_type,
                    url=payload.url,
                    description=payload.description,
                    payload=payload.payload,
                    created_at=func.now(),
                )
            )
            refreshed_dispute = await self._load_dispute_with_evidence(session, dispute_id)
            await session.commit()
            return refreshed_dispute

    async def review_market_dispute(
        self,
        slug: str,
        dispute_id: UUID,
        payload: MarketDisputeReviewRequest,
    ) -> MarketDisputeResponse:
        async with self._session_factory() as session:
            dispute_row, market_row = await self._fetch_dispute_for_market(session, slug, dispute_id)
            market_id = market_row._mapping["id"]
            if dispute_row._mapping["status"] in {"dismissed", "upheld", "withdrawn"}:
                raise ConflictError("This dispute has already been closed")

            resolution_result = await session.execute(
                select(market_resolutions)
                .where(market_resolutions.c.id == dispute_row._mapping["resolution_id"])
            )
            resolution_row = resolution_result.first()
            candidate_id = resolution_row._mapping["candidate_id"] if resolution_row is not None else None

            update_values: dict[str, object] = {
                "status": payload.status,
                "review_notes": payload.review_notes,
                "updated_at": func.now(),
            }
            if payload.status in {"dismissed", "upheld", "withdrawn"}:
                update_values["closed_at"] = func.now()
            await session.execute(
                update(disputes)
                .where(disputes.c.id == dispute_id)
                .values(**update_values)
            )

            if payload.status == "under_review":
                await session.execute(
                    update(markets)
                    .where(markets.c.id == market_id)
                    .values(status="disputed", updated_at=func.now())
                )
                if resolution_row is not None:
                    await session.execute(
                        update(market_resolutions)
                        .where(market_resolutions.c.id == resolution_row._mapping["id"])
                        .values(
                            final_payload={
                                **(resolution_row._mapping["final_payload"] or {}),
                                "status": "disputed",
                                "dispute_review_state": "under_review",
                                "latest_dispute_id": str(dispute_id),
                            }
                        )
                    )
            elif payload.status in {"dismissed", "withdrawn"}:
                await session.execute(
                    update(markets)
                    .where(markets.c.id == market_id)
                    .values(status="awaiting_resolution", updated_at=func.now())
                )
                if resolution_row is not None:
                    await session.execute(
                        update(market_resolutions)
                        .where(market_resolutions.c.id == resolution_row._mapping["id"])
                        .values(
                            final_payload={
                                **(resolution_row._mapping["final_payload"] or {}),
                                "status": "pending_oracle",
                                "dispute_review_state": payload.status,
                                "latest_dispute_id": str(dispute_id),
                            }
                        )
                    )
                if candidate_id is not None:
                    await session.execute(
                        update(market_resolution_candidates)
                        .where(market_resolution_candidates.c.id == candidate_id)
                        .values(status="proposed", reviewed_at=None, reviewed_by=None)
                    )
            elif payload.status == "upheld":
                await session.execute(
                    update(markets)
                    .where(markets.c.id == market_id)
                    .values(status="disputed", updated_at=func.now())
                )
                if resolution_row is not None:
                    await session.execute(
                        update(market_resolutions)
                        .where(market_resolutions.c.id == resolution_row._mapping["id"])
                        .values(
                            final_payload={
                                **(resolution_row._mapping["final_payload"] or {}),
                                "status": "disputed",
                                "dispute_review_state": "upheld",
                                "latest_dispute_id": str(dispute_id),
                            }
                        )
                    )

            refreshed_dispute = await self._load_dispute_with_evidence(session, dispute_id)
            await session.commit()
            return refreshed_dispute

    async def request_settlement(
        self,
        slug: str,
        requester_id: UUID,
        payload: MarketSettlementRequestCreateRequest,
    ) -> MarketResolutionResponse:
        async with self._session_factory() as session:
            market_result = await session.execute(select(markets).where(markets.c.slug == slug))
            market_row = market_result.first()
            if market_row is None:
                raise NotFoundError("Market not found")
            market_mapping = market_row._mapping
            if market_mapping["status"] in {"settled", "cancelled", "awaiting_resolution", "disputed"}:
                raise ConflictError(f"Cannot request oracle settlement in status {market_mapping['status']}")

            finalizes_at = datetime.now(timezone.utc) + timedelta(minutes=settings.oracle_liveness_minutes)
            candidate_id = uuid4()
            oracle_payload = {}
            if self._oracle_service is not None:
                try:
                    oracle_payload = await self._oracle_service.begin_resolution(
                        OracleResolutionRequest(
                            market_id=market_mapping["id"],
                            market_slug=slug,
                            candidate_id=candidate_id,
                            resolution_mode=market_mapping["resolution_mode"],
                            source_reference_url=payload.source_reference_url or market_mapping["settlement_reference_url"],
                            notes=payload.notes,
                            finalizes_at=finalizes_at,
                        )
                    )
                except OracleConfigurationError as exc:
                    raise ConflictError(str(exc)) from exc
            await session.execute(
                insert(market_resolution_candidates).values(
                    id=candidate_id,
                    market_id=market_mapping["id"],
                    proposed_outcome_id=None,
                    proposed_by=requester_id,
                    settlement_source_id=market_mapping["settlement_source_id"],
                    status="proposed",
                    source_reference_url=payload.source_reference_url or market_mapping["settlement_reference_url"],
                    source_reference_text=payload.notes,
                    payload={
                        "status": "pending_oracle",
                        "notes": payload.notes or "",
                        "requested_by": str(requester_id),
                        **oracle_payload,
                    },
                    proposed_at=func.now(),
                )
            )
            resolution_insert = await session.execute(
                insert(market_resolutions)
                .values(
                    market_id=market_mapping["id"],
                    candidate_id=candidate_id,
                    resolved_by=None,
                    resolution_mode=market_mapping["resolution_mode"],
                    settlement_source_id=market_mapping["settlement_source_id"],
                    source_reference_url=payload.source_reference_url or market_mapping["settlement_reference_url"],
                    final_payload={
                        "status": "pending_oracle",
                        "notes": payload.notes or "",
                        "requested_by": str(requester_id),
                        **oracle_payload,
                    },
                    finalizes_at=finalizes_at,
                    resolved_at=func.now(),
                )
                .returning(market_resolutions)
            )
            resolution_row = resolution_insert.first()

            await session.execute(
                update(markets)
                .where(markets.c.id == market_mapping["id"])
                .values(
                    status="awaiting_resolution",
                    resolution_due_at=finalizes_at,
                    dispute_window_ends_at=finalizes_at,
                    updated_at=func.now(),
                )
            )
            await session.commit()
            return _market_resolution_from_row(resolution_row)

    async def reconcile_oracle_resolution(self, slug: str) -> MarketResolutionStateResponse:
        async with self._session_factory() as session:
            market_result = await session.execute(select(markets.c.id).where(markets.c.slug == slug))
            market_id = market_result.scalar_one_or_none()
            if market_id is None:
                raise NotFoundError("Market not found")

            resolution_row = (
                await session.execute(
                    select(market_resolutions)
                    .where(market_resolutions.c.market_id == market_id)
                    .order_by(market_resolutions.c.created_at.desc())
                )
            ).first()
            if resolution_row is None or resolution_row._mapping["candidate_id"] is None:
                raise ConflictError("No oracle resolution candidate is pending for this market")

            candidate_id = resolution_row._mapping["candidate_id"]
            candidate_row = (
                await session.execute(
                    select(market_resolution_candidates).where(market_resolution_candidates.c.id == candidate_id)
                )
            ).first()
            if candidate_row is None:
                raise ConflictError("The active oracle candidate could not be found")

            current_payload: dict[str, object] = {}
            candidate_payload = candidate_row._mapping["payload"]
            resolution_payload = resolution_row._mapping["final_payload"]
            if isinstance(candidate_payload, dict):
                current_payload.update(candidate_payload)
            if isinstance(resolution_payload, dict):
                current_payload.update(resolution_payload)

            if self._oracle_service is None:
                raise ConflictError("Oracle reconciliation is not configured for this environment")
            try:
                reconciled_payload = await self._oracle_service.reconcile_resolution(
                    OracleResolutionStatusRequest(
                        market_id=market_id,
                        market_slug=slug,
                        candidate_id=candidate_id,
                        current_payload=current_payload,
                    )
                )
            except OracleConfigurationError as exc:
                raise ConflictError(str(exc)) from exc

            await session.execute(
                update(market_resolution_candidates)
                .where(market_resolution_candidates.c.id == candidate_id)
                .values(payload=reconciled_payload)
            )
            await session.execute(
                update(market_resolutions)
                .where(market_resolutions.c.id == resolution_row._mapping["id"])
                .values(final_payload=reconciled_payload)
            )
            await session.commit()

        return await self.get_market_resolution_state(slug)

    async def settle_market(
        self,
        slug: str,
        reviewer_id: UUID | None,
        payload: MarketSettlementFinalizeRequest,
    ) -> MarketResolutionResponse:
        async with self._session_factory() as session:
            market_result = await session.execute(select(markets).where(markets.c.slug == slug))
            market_row = market_result.first()
            if market_row is None:
                raise NotFoundError("Market not found")
            market_mapping = market_row._mapping
            if market_mapping["status"] not in {"awaiting_resolution", "disputed"}:
                raise ConflictError(f"Market is not awaiting oracle finalization")
            open_dispute_result = await session.execute(
                select(disputes.c.id)
                .where(
                    and_(
                        disputes.c.market_id == market_mapping["id"],
                        disputes.c.status.in_(["open", "under_review"]),
                    )
                )
                .limit(1)
            )
            if open_dispute_result.scalar_one_or_none() is not None:
                raise ConflictError("Cannot finalize while an active dispute is still open")

            outcomes_result = await session.execute(
                select(market_outcomes).where(market_outcomes.c.market_id == market_mapping["id"])
            )
            outcome_rows = outcomes_result.fetchall()
            winning_outcome = next(
                (row for row in outcome_rows if row._mapping["id"] == payload.winning_outcome_id),
                None,
            )
            if winning_outcome is None:
                raise NotFoundError("Winning outcome not found")

            await session.execute(
                update(market_outcomes)
                .where(market_outcomes.c.market_id == market_mapping["id"])
                .values(
                    status="losing",
                    settlement_value=Decimal("0"),
                    updated_at=func.now(),
                )
            )
            await session.execute(
                update(market_outcomes)
                .where(market_outcomes.c.id == payload.winning_outcome_id)
                .values(
                    status="winning",
                    settlement_value=Decimal("1"),
                    updated_at=func.now(),
                )
            )

            resolution_lookup = select(market_resolutions).where(market_resolutions.c.market_id == market_mapping["id"])
            if payload.candidate_id is not None:
                resolution_lookup = resolution_lookup.where(market_resolutions.c.candidate_id == payload.candidate_id)
            resolution_lookup = resolution_lookup.order_by(market_resolutions.c.created_at.desc())
            resolution_row = (await session.execute(resolution_lookup)).first()

            existing_final_payload = resolution_row._mapping["final_payload"] if resolution_row is not None else {}
            final_payload = {
                **(existing_final_payload or {}),
                "status": "finalized",
                "notes": payload.notes or "",
                "finalized_by": "oracle_callback",
                "winning_outcome_id": str(payload.winning_outcome_id),
            }
            if payload.candidate_id is not None:
                candidate_row = (
                    await session.execute(
                        select(market_resolution_candidates).where(market_resolution_candidates.c.id == payload.candidate_id)
                    )
                ).first()
                candidate_payload = candidate_row._mapping["payload"] if candidate_row is not None else {}
                await session.execute(
                    update(market_resolution_candidates)
                    .where(market_resolution_candidates.c.id == payload.candidate_id)
                    .values(
                        proposed_outcome_id=payload.winning_outcome_id,
                        status="confirmed",
                        reviewed_at=func.now(),
                        reviewed_by=reviewer_id,
                        source_reference_url=payload.source_reference_url,
                        source_reference_text=payload.notes,
                        payload={
                            **(candidate_payload or {}),
                            "status": "finalized",
                            "notes": payload.notes or "",
                            "winning_outcome_id": str(payload.winning_outcome_id),
                        },
                    )
                )
            if resolution_row is None:
                resolution_write = await session.execute(
                    insert(market_resolutions)
                    .values(
                        market_id=market_mapping["id"],
                        winning_outcome_id=payload.winning_outcome_id,
                        candidate_id=payload.candidate_id,
                        resolved_by=reviewer_id,
                        resolution_mode=market_mapping["resolution_mode"],
                        settlement_source_id=market_mapping["settlement_source_id"],
                        source_reference_url=payload.source_reference_url or market_mapping["settlement_reference_url"],
                        final_payload=final_payload,
                    )
                    .returning(market_resolutions)
                )
            else:
                resolution_write = await session.execute(
                    update(market_resolutions)
                    .where(market_resolutions.c.id == resolution_row._mapping["id"])
                    .values(
                        winning_outcome_id=payload.winning_outcome_id,
                        resolved_by=reviewer_id,
                        source_reference_url=payload.source_reference_url
                        or resolution_row._mapping["source_reference_url"]
                        or market_mapping["settlement_reference_url"],
                        final_payload=final_payload,
                        resolved_at=func.now(),
                    )
                    .returning(market_resolutions)
                )
            resolution_row = resolution_write.first()

            asset_code = "USDC" if market_mapping["rail_mode"] == "onchain" else "AUD"
            asset_id = await _get_asset_id_by_code(session, asset_code)
            market_account_id = await _get_or_create_ledger_account(
                session,
                account_code=f"MARKET::{market_mapping['id']}::{asset_code}::{market_mapping['rail_mode']}",
                owner_type="market",
                owner_market_id=market_mapping["id"],
                asset_id=asset_id,
                rail_mode=market_mapping["rail_mode"],
                is_system=True,
                metadata={"purpose": "settlement"},
            )

            positions_result = await session.execute(
                select(positions).where(positions.c.market_id == market_mapping["id"])
            )
            position_rows = positions_result.fetchall()

            for position_row in position_rows:
                position_mapping = position_row._mapping
                settlement_value = Decimal("1") if position_mapping["outcome_id"] == payload.winning_outcome_id else Decimal("0")
                quantity = position_mapping["quantity"]
                payout_amount = quantity * settlement_value
                net_cost = position_mapping["net_cost"]
                realized_delta = payout_amount - net_cost

                if payout_amount != 0:
                    user_account_id = await _get_or_create_ledger_account(
                        session,
                        account_code=f"USER::{position_mapping['profile_id']}::{asset_code}::{position_mapping['rail_mode']}",
                        owner_type="user",
                        owner_profile_id=position_mapping["profile_id"],
                        asset_id=position_mapping["asset_id"],
                        rail_mode=position_mapping["rail_mode"],
                    )
                    transaction_result = await session.execute(
                        insert(ledger_transactions)
                        .values(
                            transaction_type="trade_settlement",
                            market_id=market_mapping["id"],
                            initiated_by=reviewer_id,
                            description=f"Settlement for market {market_mapping['slug']}",
                            metadata={
                                "position_id": str(position_mapping["id"]),
                                "winning_outcome_id": str(payload.winning_outcome_id),
                            },
                        )
                        .returning(ledger_transactions.c.id)
                    )
                    transaction_id = transaction_result.scalar_one()

                    if payout_amount > 0:
                        entry_values = [
                            {
                                "transaction_id": transaction_id,
                                "ledger_account_id": user_account_id,
                                "direction": "debit",
                                "amount": payout_amount,
                                "metadata": {},
                            },
                            {
                                "transaction_id": transaction_id,
                                "ledger_account_id": market_account_id,
                                "direction": "credit",
                                "amount": payout_amount,
                                "metadata": {},
                            },
                        ]
                    else:
                        absolute_amount = abs(payout_amount)
                        entry_values = [
                            {
                                "transaction_id": transaction_id,
                                "ledger_account_id": user_account_id,
                                "direction": "credit",
                                "amount": absolute_amount,
                                "metadata": {},
                            },
                            {
                                "transaction_id": transaction_id,
                                "ledger_account_id": market_account_id,
                                "direction": "debit",
                                "amount": absolute_amount,
                                "metadata": {},
                            },
                        ]
                    await session.execute(insert(ledger_entries), entry_values)

                await session.execute(
                    update(positions)
                    .where(positions.c.id == position_mapping["id"])
                    .values(
                        quantity=Decimal("0"),
                        average_entry_price=None,
                        net_cost=Decimal("0"),
                        realized_pnl=position_mapping["realized_pnl"] + realized_delta,
                        unrealized_pnl=Decimal("0"),
                        updated_at=func.now(),
                    )
                )

            await session.execute(
                update(orders)
                .where(
                    and_(
                        orders.c.market_id == market_mapping["id"],
                        orders.c.status.in_(("pending_acceptance", "open", "partially_filled")),
                    )
                )
                .values(
                    status="cancelled",
                    remaining_quantity=Decimal("0"),
                    cancelled_at=func.now(),
                    updated_at=func.now(),
                )
            )

            await session.execute(
                update(markets)
                .where(markets.c.id == market_mapping["id"])
                .values(
                    status="settled",
                    settled_at=func.now(),
                    updated_at=func.now(),
                )
            )
            await session.commit()
            return _market_resolution_from_row(resolution_row)

    def _market_select_stmt(self):
        community_alias = communities.alias("market_communities")
        settlement_source_alias = settlement_sources.alias("market_settlement_sources")
        traded_volume_subquery = (
            select(func.coalesce(func.sum(trades.c.quantity), 0))
            .where(trades.c.market_id == markets.c.id)
            .scalar_subquery()
        )
        computed_total_volume_subquery = (
            select(func.coalesce(func.sum(trades.c.gross_notional), 0))
            .where(trades.c.market_id == markets.c.id)
            .scalar_subquery()
        )
        computed_total_trades_count_subquery = (
            select(func.count(trades.c.id))
            .where(trades.c.market_id == markets.c.id)
            .scalar_subquery()
        )
        last_price_subquery = (
            select(trades.c.price)
            .where(trades.c.market_id == markets.c.id)
            .order_by(trades.c.executed_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        return (
            select(
                markets,
                community_alias.c.slug.label("community_slug"),
                community_alias.c.name.label("community_name"),
                settlement_source_alias.c.code.label("settlement_source_code"),
                settlement_source_alias.c.name.label("settlement_source_name"),
                settlement_source_alias.c.resolution_mode.label("settlement_source_resolution_mode"),
                settlement_source_alias.c.base_url.label("settlement_source_base_url"),
                traded_volume_subquery.label("traded_volume"),
                computed_total_volume_subquery.label("computed_total_volume"),
                last_price_subquery.label("last_price"),
                computed_total_trades_count_subquery.label("computed_total_trades_count"),
            )
            .select_from(
                markets.outerjoin(community_alias, markets.c.community_id == community_alias.c.id).outerjoin(
                    settlement_source_alias,
                    markets.c.settlement_source_id == settlement_source_alias.c.id,
                )
            )
        )

    async def _fetch_market(self, session, slug: str) -> MarketResponse:
        result = await session.execute(self._market_select_stmt().where(markets.c.slug == slug))
        row = result.first()
        if row is None:
            raise NotFoundError("Market not found")
        return await self._hydrate_market(session, row)

    async def _hydrate_market(self, session, row) -> MarketResponse:
        outcome_result = await session.execute(
            select(market_outcomes)
            .where(market_outcomes.c.market_id == row._mapping["id"])
            .order_by(market_outcomes.c.outcome_index.asc())
        )
        outcomes = [_market_outcome_from_row(outcome_row) for outcome_row in outcome_result.fetchall()]
        return _market_from_row(row, outcomes)

    async def _fetch_dispute_for_market(self, session, slug: str, dispute_id: UUID):
        market_result = await session.execute(select(markets).where(markets.c.slug == slug))
        market_row = market_result.first()
        if market_row is None:
            raise NotFoundError("Market not found")
        dispute_result = await session.execute(
            select(disputes)
            .where(and_(disputes.c.id == dispute_id, disputes.c.market_id == market_row._mapping["id"]))
        )
        dispute_row = dispute_result.first()
        if dispute_row is None:
            raise NotFoundError("Dispute not found")
        return dispute_row, market_row

    async def _load_dispute_with_evidence(self, session, dispute_id: UUID) -> MarketDisputeResponse:
        dispute_result = await session.execute(select(disputes).where(disputes.c.id == dispute_id))
        dispute_row = dispute_result.first()
        if dispute_row is None:
            raise NotFoundError("Dispute not found")
        evidence_result = await session.execute(
            select(dispute_evidence)
            .where(dispute_evidence.c.dispute_id == dispute_id)
            .order_by(dispute_evidence.c.created_at.asc())
        )
        evidence = [_market_dispute_evidence_from_row(row) for row in evidence_result.fetchall()]
        return _market_dispute_from_row(dispute_row, evidence)

    def _build_rules_text(self, request_mapping, review_notes: str | None) -> str:
        settlement_url = request_mapping["settlement_reference_url"] or "the approved settlement source"
        base = f"This market resolves against {settlement_url}. The winning outcome is determined by the final official result."
        if review_notes:
            return f"{base}\n\nAdmin notes: {review_notes}"
        return base


class PostgresTradingRepository(TradingRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._orders_queue = settings.matching_engine_orders_queue

    async def get_market_trading_shell(self, slug: str) -> MarketTradingShellResponse:
        async with self._session_factory() as session:
            market_repository = PostgresMarketRepository(self._session_factory)
            market = await market_repository._fetch_market(session, slug)
            quotes = await self._load_quotes(session, market)
            order_books = await self._load_order_books(session, market)
            recent_trades = await self._load_recent_trades(session, market.id)
            return MarketTradingShellResponse(
                market=market,
                quotes=quotes,
                order_books=order_books,
                recent_trades=recent_trades,
            )

    async def get_market_holders(self, slug: str, limit: int) -> MarketHoldersResponse:
        async with self._session_factory() as session:
            market_repository = PostgresMarketRepository(self._session_factory)
            market = await market_repository._fetch_market(session, slug)
            outcome_lookup = {outcome.id: outcome for outcome in market.outcomes}
            complement_lookup = self._build_complementary_outcome_lookup(market.outcomes)

            result = await session.execute(
                select(
                    positions.c.profile_id,
                    positions.c.outcome_id,
                    positions.c.quantity,
                    positions.c.average_entry_price,
                    positions.c.realized_pnl,
                    positions.c.unrealized_pnl,
                    profiles.c.username,
                    profiles.c.display_name,
                )
                .select_from(positions.join(profiles, positions.c.profile_id == profiles.c.id))
                .where(
                    and_(
                        positions.c.market_id == market.id,
                        positions.c.quantity != 0,
                    )
                )
                .order_by(func.abs(positions.c.quantity).desc(), profiles.c.display_name.asc())
            )
            groups: dict[UUID, list[MarketHolderEntryResponse]] = {outcome.id: [] for outcome in market.outcomes}
            for row in result.fetchall():
                mapping = row._mapping
                quantity = mapping["quantity"]
                base_outcome = outcome_lookup.get(mapping["outcome_id"])
                if base_outcome is None:
                    continue
                display_outcome = base_outcome if quantity >= 0 else complement_lookup.get(base_outcome.id, base_outcome)
                groups.setdefault(display_outcome.id, [])
                groups[display_outcome.id].append(
                    MarketHolderEntryResponse(
                        profile_id=mapping["profile_id"],
                        username=mapping["username"],
                        display_name=mapping["display_name"],
                        outcome_id=display_outcome.id,
                        outcome_label=display_outcome.label,
                        quantity=_decimal_to_str(abs(quantity)) or "0",
                        average_entry_price=_decimal_to_str(mapping["average_entry_price"]),
                        realized_pnl=_decimal_to_str(mapping["realized_pnl"]) or "0",
                        unrealized_pnl=_decimal_to_str(mapping["unrealized_pnl"]) or "0",
                    )
                )

            grouped_payload = [
                MarketHolderGroupResponse(
                    outcome_id=outcome.id,
                    outcome_label=outcome.label,
                    holders=groups.get(outcome.id, [])[:limit],
                )
                for outcome in market.outcomes
            ]
            return MarketHoldersResponse(
                market_id=market.id,
                market_slug=market.slug,
                groups=grouped_payload,
                last_updated_at=datetime.now(timezone.utc),
            )

    async def get_market_history(
        self,
        slug: str,
        outcome_id: UUID,
        range_key: str,
    ) -> MarketHistoryResponse:
        resolved_range, lookback_window, interval_seconds = resolve_market_history_range(range_key)
        window_end = datetime.now(timezone.utc)
        window_start = window_end - lookback_window

        async with self._session_factory() as session:
            market_repository = PostgresMarketRepository(self._session_factory)
            market = await market_repository._fetch_market(session, slug)
            outcome = next((item for item in market.outcomes if item.id == outcome_id), None)
            if outcome is None:
                raise NotFoundError("Market outcome not found")

            result = await session.execute(
                text(
                    """
                    with filtered_trades as (
                        select
                            t.id,
                            t.price,
                            t.quantity,
                            t.executed_at,
                            to_timestamp(
                                floor(extract(epoch from t.executed_at) / :bucket_seconds) * :bucket_seconds
                            ) as bucket_start
                        from public.trades t
                        where
                            t.market_id = :market_id
                            and t.outcome_id = :outcome_id
                            and t.executed_at >= :window_start
                            and t.executed_at <= :window_end
                    )
                    select
                        bucket_start,
                        (array_agg(price order by executed_at asc, id asc))[1] as open_price,
                        max(price) as high_price,
                        min(price) as low_price,
                        (array_agg(price order by executed_at desc, id desc))[1] as close_price,
                        coalesce(sum(quantity), 0) as volume,
                        count(*) as trade_count
                    from filtered_trades
                    group by bucket_start
                    order by bucket_start asc
                    """
                ),
                {
                    "bucket_seconds": interval_seconds,
                    "market_id": market.id,
                    "outcome_id": outcome_id,
                    "window_start": window_start,
                    "window_end": window_end,
                },
            )
            buckets = [_market_history_bucket_from_row(row, interval_seconds) for row in result.fetchall()]
            return MarketHistoryResponse(
                market_id=market.id,
                market_slug=market.slug,
                outcome_id=outcome.id,
                outcome_label=outcome.label,
                range_key=resolved_range,
                interval_seconds=interval_seconds,
                window_start=window_start,
                window_end=window_end,
                buckets=buckets,
            )

    async def list_market_orders(self, slug: str, actor_id: UUID) -> list[MarketOrderResponse]:
        async with self._session_factory() as session:
            market_id = await self._get_market_id(session, slug)
            result = await session.execute(
                self._market_order_select_stmt()
                .where(and_(orders.c.market_id == market_id, orders.c.profile_id == actor_id))
                .order_by(orders.c.created_at.desc())
            )
            return [_market_order_from_row(row) for row in result.fetchall()]

    async def create_market_order(
        self,
        slug: str,
        actor_id: UUID,
        payload: MarketOrderCreateRequest,
    ) -> MarketOrderResponse:
        async with self._session_factory() as session:
            market_repository = PostgresMarketRepository(self._session_factory)
            market = await market_repository._fetch_market(session, slug)
            if market.status not in {"pending_liquidity", "open"}:
                raise ConflictError("Orders are only accepted while the market is gathering liquidity or open for trading")
            if payload.order_type != "limit":
                raise ConflictError("Market orders are not enabled until the matching engine is live")
            if payload.side not in {"buy", "sell"}:
                raise ConflictError("Order side must be buy or sell")
            if payload.quantity <= 0:
                raise ConflictError("Order quantity must be greater than zero")
            if payload.price is None:
                raise ConflictError("Limit orders require a price")
            if payload.price <= 0 or payload.price >= 1:
                raise ConflictError("Order price must be between 0 and 1")

            outcome = next((item for item in market.outcomes if item.id == payload.outcome_id), None)
            if outcome is None:
                raise NotFoundError("Market outcome not found")

            asset_code = "USDC" if market.rail_mode == "onchain" else "AUD"
            asset_id = await _get_asset_id_by_code(session, asset_code)

            available_balance = await self._get_available_cash_balance(session, actor_id, asset_code, market.rail_mode)
            required_cost = self._required_order_collateral(payload.side, payload.quantity, payload.price)
            if available_balance < required_cost:
                raise ConflictError("Insufficient available balance for this order")

            order_insert = await session.execute(
                insert(orders)
                .values(
                    market_id=market.id,
                    outcome_id=payload.outcome_id,
                    profile_id=actor_id,
                    asset_id=asset_id,
                    rail_mode=market.rail_mode,
                    side=payload.side,
                    order_type=payload.order_type,
                    status="pending_acceptance",
                    quantity=payload.quantity,
                    price=payload.price,
                    matched_quantity=0,
                    remaining_quantity=payload.quantity,
                    max_total_cost=required_cost,
                    source="web",
                    client_order_id=payload.client_order_id,
                    metadata={},
                )
                .returning(orders.c.id)
            )
            order_id = order_insert.scalar_one()
            result = await session.execute(self._market_order_select_stmt().where(orders.c.id == order_id))
            row = result.first()
            await session.commit()
            try:
                await self._enqueue_order(order_id, market.id, payload.outcome_id)
            except Exception as exc:
                await self._mark_order_rejected(order_id, "Matching engine queue is unavailable")
                raise ServiceUnavailableError("Matching engine queue is unavailable") from exc
            return _market_order_from_row(row)

    async def cancel_market_order(
        self,
        slug: str,
        order_id: UUID,
        actor_id: UUID,
        actor_is_admin: bool,
    ) -> MarketOrderResponse:
        async with self._session_factory() as session:
            market_id = await self._get_market_id(session, slug)
            order_result = await session.execute(
                select(orders)
                .where(and_(orders.c.id == order_id, orders.c.market_id == market_id))
            )
            order_row = order_result.first()
            if order_row is None:
                raise NotFoundError("Market order not found")
            order_mapping = order_row._mapping
            if order_mapping["profile_id"] != actor_id and not actor_is_admin:
                raise ForbiddenError("You do not have permission to cancel this order")
            if order_mapping["status"] not in {"open", "partially_filled", "pending_acceptance"}:
                raise ConflictError("Only active orders can be cancelled")
            await session.execute(
                update(orders)
                .where(orders.c.id == order_id)
                .values(status="cancelled", cancelled_at=func.now(), updated_at=func.now())
            )
            result = await session.execute(self._market_order_select_stmt().where(orders.c.id == order_id))
            row = result.first()
            await session.commit()
            return _market_order_from_row(row)

    async def get_portfolio_summary(self, actor_id: UUID) -> PortfolioSummaryResponse:
        async with self._session_factory() as session:
            balance_rows = await session.execute(
                text(
                    """
                    select
                        account_code,
                        asset_code,
                        rail_mode::text as rail_mode,
                        balance
                    from public.account_balances
                    where owner_profile_id = :actor_id
                    order by asset_code, rail_mode, account_code
                    """
                ),
                {"actor_id": actor_id},
            )
            reserved_by_key = await self._load_reserved_cash_balances(session, actor_id)
            balances = [
                PortfolioBalanceResponse(
                    asset_code=row._mapping["asset_code"],
                    rail_mode=row._mapping["rail_mode"],
                    account_code=row._mapping["account_code"],
                    settled_balance=_decimal_to_str(row._mapping["balance"]) or "0",
                    reserved_balance=_decimal_to_str(
                        reserved_by_key.get((row._mapping["asset_code"], row._mapping["rail_mode"]), Decimal("0"))
                    )
                    or "0",
                    available_balance=_decimal_to_str(
                        row._mapping["balance"]
                        - reserved_by_key.get((row._mapping["asset_code"], row._mapping["rail_mode"]), Decimal("0"))
                    )
                    or "0",
                )
                for row in balance_rows.fetchall()
            ]

            positions_result = await session.execute(
                text(
                    """
                    with last_prices as (
                        select distinct on (outcome_id)
                            outcome_id,
                            price
                        from public.trades
                        order by outcome_id, executed_at desc
                    )
                    select
                        p.market_id,
                        m.slug as market_slug,
                        m.title as market_title,
                        m.status::text as market_status,
                        p.outcome_id,
                        mo.label as outcome_label,
                        p.quantity,
                        p.average_entry_price,
                        p.net_cost,
                        p.realized_pnl,
                        coalesce((p.quantity * (coalesce(lp.price, p.average_entry_price, 0) - coalesce(p.average_entry_price, 0))), 0) as unrealized_pnl,
                        p.last_trade_at
                    from public.positions p
                    join public.markets m on m.id = p.market_id
                    join public.market_outcomes mo on mo.id = p.outcome_id
                    left join last_prices lp on lp.outcome_id = p.outcome_id
                    where p.profile_id = :actor_id
                    order by p.last_trade_at desc nulls last, m.created_at desc
                    """
                ),
                {"actor_id": actor_id},
            )
            positions_payload = [_portfolio_position_from_row(row) for row in positions_result.fetchall()]

            open_orders_result = await session.execute(
                self._market_order_select_stmt()
                .where(
                    and_(
                        orders.c.profile_id == actor_id,
                        orders.c.status.in_(("pending_acceptance", "open", "partially_filled")),
                    )
                )
                .order_by(orders.c.created_at.desc())
            )
            open_orders = [_market_order_from_row(row) for row in open_orders_result.fetchall()]

            outcome_alias = market_outcomes.alias("portfolio_trade_outcomes")
            recent_trades_result = await session.execute(
                select(
                    trades,
                    outcome_alias.c.label.label("outcome_label"),
                )
                .select_from(trades.join(outcome_alias, trades.c.outcome_id == outcome_alias.c.id))
                .where(or_(trades.c.maker_profile_id == actor_id, trades.c.taker_profile_id == actor_id))
                .order_by(trades.c.executed_at.desc())
                .limit(20)
            )
            recent_trades = [_market_trade_from_row(row) for row in recent_trades_result.fetchall()]

            return PortfolioSummaryResponse(
                balances=balances,
                positions=positions_payload,
                open_orders=open_orders,
                recent_trades=recent_trades,
            )

    async def fund_balance(
        self,
        reviewer_id: UUID,
        payload: AdminFundBalanceRequest,
    ) -> PortfolioSummaryResponse:
        async with self._session_factory() as session:
            asset_code = payload.asset_code.upper()
            asset_id = await _get_asset_id_by_code(session, asset_code)
            user_account_id = await _get_or_create_ledger_account(
                session,
                account_code=f"USER::{payload.profile_id}::{asset_code}::{payload.rail_mode}",
                owner_type="user",
                owner_profile_id=payload.profile_id,
                asset_id=asset_id,
                rail_mode=payload.rail_mode,
            )
            treasury_account_id = await _get_or_create_ledger_account(
                session,
                account_code=f"TREASURY::{asset_code}::{payload.rail_mode}",
                owner_type="treasury",
                asset_id=asset_id,
                rail_mode=payload.rail_mode,
                is_system=True,
                metadata={"purpose": "treasury"},
            )
            transaction_result = await session.execute(
                insert(ledger_transactions)
                .values(
                    transaction_type="adjustment",
                    initiated_by=reviewer_id,
                    description=payload.description or f"Manual funding for {payload.profile_id}",
                    metadata={"funded_profile_id": str(payload.profile_id)},
                )
                .returning(ledger_transactions.c.id)
            )
            transaction_id = transaction_result.scalar_one()
            await session.execute(
                insert(ledger_entries),
                [
                    {
                        "transaction_id": transaction_id,
                        "ledger_account_id": user_account_id,
                        "direction": "debit",
                        "amount": payload.amount,
                        "metadata": {},
                    },
                    {
                        "transaction_id": transaction_id,
                        "ledger_account_id": treasury_account_id,
                        "direction": "credit",
                        "amount": payload.amount,
                        "metadata": {},
                    },
                ],
            )
            await session.commit()
        return await self.get_portfolio_summary(payload.profile_id)

    async def _load_quotes(self, session, market: MarketResponse) -> list[MarketQuoteResponse]:
        quotes: list[MarketQuoteResponse] = []
        for outcome in market.outcomes:
            best_bid_result = await session.execute(
                select(func.max(orders.c.price))
                .where(
                    and_(
                        orders.c.market_id == market.id,
                        orders.c.outcome_id == outcome.id,
                        orders.c.side == "buy",
                        orders.c.status.in_(("open", "partially_filled")),
                    )
                )
            )
            best_ask_result = await session.execute(
                select(func.min(orders.c.price))
                .where(
                    and_(
                        orders.c.market_id == market.id,
                        orders.c.outcome_id == outcome.id,
                        orders.c.side == "sell",
                        orders.c.status.in_(("open", "partially_filled")),
                    )
                )
            )
            bid_qty_result = await session.execute(
                select(func.coalesce(func.sum(orders.c.remaining_quantity), 0))
                .where(
                    and_(
                        orders.c.market_id == market.id,
                        orders.c.outcome_id == outcome.id,
                        orders.c.side == "buy",
                        orders.c.status.in_(("open", "partially_filled")),
                    )
                )
            )
            ask_qty_result = await session.execute(
                select(func.coalesce(func.sum(orders.c.remaining_quantity), 0))
                .where(
                    and_(
                        orders.c.market_id == market.id,
                        orders.c.outcome_id == outcome.id,
                        orders.c.side == "sell",
                        orders.c.status.in_(("open", "partially_filled")),
                    )
                )
            )
            last_trade_result = await session.execute(
                select(trades.c.price)
                .where(and_(trades.c.market_id == market.id, trades.c.outcome_id == outcome.id))
                .order_by(trades.c.executed_at.desc())
                .limit(1)
            )
            trade_volume_result = await session.execute(
                select(func.coalesce(func.sum(trades.c.quantity), 0))
                .where(and_(trades.c.market_id == market.id, trades.c.outcome_id == outcome.id))
            )
            quotes.append(
                _market_quote_from_values(
                    outcome.id,
                    outcome.code,
                    outcome.label,
                    last_price=last_trade_result.scalar_one_or_none(),
                    best_bid=best_bid_result.scalar_one_or_none(),
                    best_ask=best_ask_result.scalar_one_or_none(),
                    traded_volume=trade_volume_result.scalar_one(),
                    resting_bid_quantity=bid_qty_result.scalar_one(),
                    resting_ask_quantity=ask_qty_result.scalar_one(),
                )
            )
        return quotes

    async def _load_order_books(self, session, market: MarketResponse) -> list[MarketOrderBookResponse]:
        order_books: list[MarketOrderBookResponse] = []
        for outcome in market.outcomes:
            bids_result = await session.execute(
                text(
                    """
                    select
                        price,
                        coalesce(sum(remaining_quantity), 0) as quantity,
                        count(*) as order_count
                    from public.orders
                    where
                        market_id = :market_id
                        and outcome_id = :outcome_id
                        and side = 'buy'
                        and status in ('open', 'partially_filled')
                    group by price
                    order by price desc
                    limit 5
                    """
                ),
                {"market_id": market.id, "outcome_id": outcome.id},
            )
            asks_result = await session.execute(
                text(
                    """
                    select
                        price,
                        coalesce(sum(remaining_quantity), 0) as quantity,
                        count(*) as order_count
                    from public.orders
                    where
                        market_id = :market_id
                        and outcome_id = :outcome_id
                        and side = 'sell'
                        and status in ('open', 'partially_filled')
                    group by price
                    order by price asc
                    limit 5
                    """
                ),
                {"market_id": market.id, "outcome_id": outcome.id},
            )
            order_books.append(
                MarketOrderBookResponse(
                    outcome_id=outcome.id,
                    outcome_label=outcome.label,
                    bids=[_market_depth_level_from_row(row) for row in bids_result.fetchall()],
                    asks=[_market_depth_level_from_row(row) for row in asks_result.fetchall()],
                )
            )
        return order_books

    async def _load_recent_trades(self, session, market_id: UUID) -> list[MarketTradeResponse]:
        outcome_alias = market_outcomes.alias("trade_outcomes")
        result = await session.execute(
            select(
                trades,
                outcome_alias.c.label.label("outcome_label"),
            )
            .select_from(trades.join(outcome_alias, trades.c.outcome_id == outcome_alias.c.id))
            .where(trades.c.market_id == market_id)
            .order_by(trades.c.executed_at.desc())
            .limit(10)
        )
        return [_market_trade_from_row(row) for row in result.fetchall()]

    async def _get_market_id(self, session, slug: str) -> UUID:
        result = await session.execute(select(markets.c.id).where(markets.c.slug == slug))
        market_id = result.scalar_one_or_none()
        if market_id is None:
            raise NotFoundError("Market not found")
        return market_id

    def _market_order_select_stmt(self):
        outcome_alias = market_outcomes.alias("order_outcomes")
        return (
            select(
                orders,
                outcome_alias.c.label.label("outcome_label"),
            )
            .select_from(orders.join(outcome_alias, orders.c.outcome_id == outcome_alias.c.id))
        )

    async def _enqueue_order(self, order_id: UUID, market_id: UUID, outcome_id: UUID) -> None:
        payload = json.dumps(
            {
                "event_type": "match_order",
                "order_id": str(order_id),
                "market_id": str(market_id),
                "outcome_id": str(outcome_id),
            }
        )
        await self._redis.lpush(self._orders_queue, payload)

    async def _mark_order_rejected(self, order_id: UUID, rejection_reason: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(orders)
                .where(orders.c.id == order_id)
                .values(
                    status="rejected",
                    rejection_reason=rejection_reason,
                    updated_at=func.now(),
                )
            )
            await session.commit()

    async def _load_reserved_cash_balances(
        self,
        session,
        actor_id: UUID,
    ) -> dict[tuple[str, str], Decimal]:
        result = await session.execute(
            text(
                """
                select
                    a.code as asset_code,
                    o.rail_mode::text as rail_mode,
                    coalesce(
                        sum(
                            case
                                when o.side = 'buy' then o.remaining_quantity * coalesce(o.price, 0)
                                else o.remaining_quantity * (1 - coalesce(o.price, 0))
                            end
                        ),
                        0
                    ) as reserved_balance
                from public.orders o
                join public.assets a on a.id = o.asset_id
                where
                    o.profile_id = :actor_id
                    and o.status in ('pending_acceptance', 'open', 'partially_filled')
                group by a.code, o.rail_mode
                """
            ),
            {"actor_id": actor_id},
        )
        return {
            (row._mapping["asset_code"], row._mapping["rail_mode"]): row._mapping["reserved_balance"]
            for row in result.fetchall()
        }

    async def _get_available_cash_balance(
        self,
        session,
        actor_id: UUID,
        asset_code: str,
        rail_mode: str,
    ) -> Decimal:
        balance_result = await session.execute(
            text(
                """
                select coalesce(sum(balance), 0) as balance
                from public.account_balances
                where
                    owner_profile_id = :actor_id
                    and asset_code = :asset_code
                    and rail_mode = :rail_mode
                """
            ),
            {"actor_id": actor_id, "asset_code": asset_code, "rail_mode": rail_mode},
        )
        settled_balance = balance_result.scalar_one() or Decimal("0")
        reserved_by_key = await self._load_reserved_cash_balances(session, actor_id)
        return settled_balance - reserved_by_key.get((asset_code, rail_mode), Decimal("0"))

    @staticmethod
    def _build_complementary_outcome_lookup(
        outcomes: list[MarketOutcomeResponse],
    ) -> dict[UUID, MarketOutcomeResponse]:
        if len(outcomes) != 2:
            return {outcome.id: outcome for outcome in outcomes}
        return {
            outcomes[0].id: outcomes[1],
            outcomes[1].id: outcomes[0],
        }

    @staticmethod
    def _required_order_collateral(side: str, quantity: Decimal, price: Decimal) -> Decimal:
        if side == "buy":
            return quantity * price
        return quantity * (Decimal("1") - price)
