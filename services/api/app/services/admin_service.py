from datetime import UTC, datetime

from app.core.actor import CurrentActor
from app.core.exceptions import ConflictError, ForbiddenError
from app.repositories.base import MarketRepository, MarketRequestRepository, PostRepository
from app.schemas.market import MarketResponse
from app.schemas.admin import (
    OracleApprovalResponse,
    OracleLiveReadinessResponse,
    SettlementAutomationRunRequest,
    SettlementAutomationRunResponse,
    SettlementQueueItemResponse,
    SettlementQueueResponse,
    RollingUpDownRunRequest,
    RollingUpDownRunResponse,
    ReviewQueueResponse,
)
from app.schemas.portfolio import MarketResolutionResponse, MarketSettlementFinalizeRequest
from app.services.oracle_service import OracleConfigurationError, OracleService
from app.services.rolling_market_service import RollingMarketService


class AdminService:
    def __init__(
        self,
        post_repository: PostRepository,
        market_request_repository: MarketRequestRepository,
        market_repository: MarketRepository,
        oracle_service: OracleService,
        rolling_market_service: RollingMarketService,
    ) -> None:
        self._post_repository = post_repository
        self._market_request_repository = market_request_repository
        self._market_repository = market_repository
        self._oracle_service = oracle_service
        self._rolling_market_service = rolling_market_service

    async def get_review_queue(self, actor: CurrentActor) -> ReviewQueueResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        pending_posts = await self._post_repository.list_pending_posts()
        pending_market_requests = await self._market_request_repository.list_pending_requests()
        return ReviewQueueResponse(
            pending_posts=pending_posts,
            pending_market_requests=pending_market_requests,
        )

    async def publish_market_request(
        self,
        actor: CurrentActor,
        request_id,
        review_notes: str | None,
    ) -> MarketResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        return await self._market_repository.publish_from_request(request_id, actor.id, review_notes)

    async def settle_market(
        self,
        actor: CurrentActor,
        market_slug: str,
        payload: MarketSettlementFinalizeRequest,
    ) -> MarketResolutionResponse:
        raise ForbiddenError("Direct admin settlement is disabled. Use the oracle settlement workflow instead.")

    async def get_oracle_live_readiness(self, actor: CurrentActor) -> OracleLiveReadinessResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        try:
            return OracleLiveReadinessResponse.model_validate(await self._oracle_service.get_live_readiness())
        except OracleConfigurationError as exc:
            raise ConflictError(str(exc)) from exc

    async def approve_oracle_bond_allowance(
        self,
        actor: CurrentActor,
        amount_wei: str | None,
    ) -> OracleApprovalResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        try:
            return OracleApprovalResponse.model_validate(await self._oracle_service.approve_bond_allowance(amount_wei))
        except OracleConfigurationError as exc:
            raise ConflictError(str(exc)) from exc

    async def run_rolling_up_down(
        self,
        actor: CurrentActor,
        payload: RollingUpDownRunRequest,
    ) -> RollingUpDownRunResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        return await self._rolling_market_service.run_up_down_cycle(actor.id, payload)

    async def get_settlement_queue(self, actor: CurrentActor) -> SettlementQueueResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        markets = await self._market_repository.list_markets()
        pending: list[SettlementQueueItemResponse] = []
        for market in markets:
            if market.status not in {"awaiting_resolution", "disputed"}:
                continue
            resolution_state = await self._market_repository.get_market_resolution_state(market.slug)
            pending.append(
                SettlementQueueItemResponse(
                    market_slug=market.slug,
                    market_status=market.status,
                    trading_closes_at=market.timing.trading_closes_at.isoformat() if market.timing.trading_closes_at else None,
                    resolution_due_at=market.timing.resolution_due_at.isoformat() if market.timing.resolution_due_at else None,
                    current_resolution_status=resolution_state.current_status,
                    dispute_count=len(resolution_state.disputes),
                    candidate_count=len(resolution_state.candidates),
                )
            )
        pending.sort(key=lambda item: item.resolution_due_at or "")
        return SettlementQueueResponse(pending=pending)

    async def run_settlement_automation(
        self,
        actor: CurrentActor,
        payload: SettlementAutomationRunRequest,
    ) -> SettlementAutomationRunResponse:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
        now = datetime.now(UTC)
        response = SettlementAutomationRunResponse()
        markets = await self._market_repository.list_markets()
        for market in markets:
            if market.status not in {"awaiting_resolution", "disputed"}:
                continue
            if market.status == "disputed" and not payload.include_disputed:
                response.skipped_markets.append(market.slug)
                continue
            due_at = market.timing.resolution_due_at
            if due_at is not None and due_at > now:
                response.skipped_markets.append(market.slug)
                continue
            response.processed_markets.append(market.slug)
            resolution_state = None
            if payload.reconcile_due_markets:
                if payload.dry_run:
                    response.reconciled_markets.append(market.slug)
                    try:
                        resolution_state = await self._market_repository.get_market_resolution_state(market.slug)
                    except Exception as exc:  # pragma: no cover - defensive
                        response.warnings.append(f"{market.slug}: unable to inspect resolution state in dry-run ({exc})")
                        continue
                else:
                    try:
                        resolution_state = await self._market_repository.reconcile_oracle_resolution(market.slug)
                        response.reconciled_markets.append(market.slug)
                    except Exception as exc:
                        response.warnings.append(f"{market.slug}: reconcile failed ({exc})")
                        continue
            else:
                try:
                    resolution_state = await self._market_repository.get_market_resolution_state(market.slug)
                except Exception as exc:
                    response.warnings.append(f"{market.slug}: unable to load resolution state ({exc})")
                    continue

            if not payload.finalize_settled_markets:
                continue
            winner_code = self._derive_oracle_winner_code(resolution_state.current_payload if resolution_state else {})
            if winner_code is None:
                response.skipped_markets.append(market.slug)
                continue
            winner = next((outcome for outcome in market.outcomes if outcome.code.upper() == winner_code), None)
            if winner is None:
                response.warnings.append(f"{market.slug}: winning outcome code {winner_code} not found on market.")
                continue
            if payload.dry_run:
                response.finalized_markets.append(market.slug)
                continue
            try:
                await self._market_repository.settle_market(
                    market.slug,
                    actor.id,
                    MarketSettlementFinalizeRequest(
                        winning_outcome_id=winner.id,
                        source_reference_url=resolution_state.source_reference_url or market.settlement_reference_url,
                        notes="Auto-finalized by admin settlement automation runner.",
                        candidate_id=resolution_state.candidate_id,
                    ),
                )
                response.finalized_markets.append(market.slug)
            except Exception as exc:
                response.warnings.append(f"{market.slug}: finalize failed ({exc})")
        return response

    @staticmethod
    def _derive_oracle_winner_code(current_payload: dict) -> str | None:
        if not isinstance(current_payload, dict):
            return None
        winner_code = current_payload.get("winner_code")
        if isinstance(winner_code, str):
            normalized = winner_code.strip().upper()
            if normalized in {"YES", "NO"}:
                return normalized
        assertion_resolution = current_payload.get("assertion_resolution")
        if isinstance(assertion_resolution, bool):
            return "YES" if assertion_resolution else "NO"
        onchain_state = current_payload.get("onchain_assertion_state")
        if isinstance(onchain_state, str):
            lowered = onchain_state.strip().lower()
            if lowered == "settled_true":
                return "YES"
            if lowered == "settled_false":
                return "NO"
        return None
