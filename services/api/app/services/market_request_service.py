from uuid import UUID

from app.core.actor import CurrentActor
from app.core.exceptions import ForbiddenError
from app.repositories.base import MarketRequestRepository
from app.schemas.market_request import (
    MarketRequestAnswerResponse,
    MarketRequestAnswerUpsertRequest,
    MarketRequestCreateRequest,
    MarketRequestResponse,
    MarketRequestUpdateRequest,
)


class MarketRequestService:
    def __init__(self, repository: MarketRequestRepository) -> None:
        self._repository = repository

    async def list_my_requests(self, actor: CurrentActor) -> list[MarketRequestResponse]:
        return await self._repository.list_requests(actor.id)

    async def create_request(
        self,
        actor: CurrentActor,
        payload: MarketRequestCreateRequest,
    ) -> MarketRequestResponse:
        return await self._repository.create_request(actor.id, payload)

    async def get_request(self, actor: CurrentActor, request_id: UUID) -> MarketRequestResponse:
        requester_id = None if actor.is_admin else actor.id
        return await self._repository.get_request(request_id, requester_id)

    async def update_request(
        self,
        actor: CurrentActor,
        request_id: UUID,
        payload: MarketRequestUpdateRequest,
    ) -> MarketRequestResponse:
        return await self._repository.update_request(request_id, actor.id, payload)

    async def upsert_answer(
        self,
        actor: CurrentActor,
        request_id: UUID,
        question_key: str,
        payload: MarketRequestAnswerUpsertRequest,
    ) -> MarketRequestAnswerResponse:
        return await self._repository.upsert_answer(request_id, actor.id, question_key, payload)

    async def list_answers(self, actor: CurrentActor, request_id: UUID) -> list[MarketRequestAnswerResponse]:
        requester_id = None if actor.is_admin else actor.id
        return await self._repository.list_answers(request_id, requester_id)

    async def submit_request(self, actor: CurrentActor, request_id: UUID) -> MarketRequestResponse:
        return await self._repository.submit_request(request_id, actor.id)

    async def approve_request(
        self,
        actor: CurrentActor,
        request_id: UUID,
        review_notes: str | None,
    ) -> MarketRequestResponse:
        self._ensure_admin(actor)
        return await self._repository.review_request(request_id, actor.id, True, review_notes)

    async def reject_request(
        self,
        actor: CurrentActor,
        request_id: UUID,
        review_notes: str | None,
    ) -> MarketRequestResponse:
        self._ensure_admin(actor)
        return await self._repository.review_request(request_id, actor.id, False, review_notes)

    def _ensure_admin(self, actor: CurrentActor) -> None:
        if not actor.is_admin:
            raise ForbiddenError("Admin access is required")
