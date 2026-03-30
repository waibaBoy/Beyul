from uuid import UUID

from app.core.actor import CurrentActor
from app.repositories.base import ProfileRepository
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UserWalletResponse,
    WalletCreateRequest,
    WalletUpdateRequest,
)


class ProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    async def get_my_profile(self, actor: CurrentActor) -> ProfileResponse:
        return await self._repository.get_current_profile(
            actor_id=actor.id,
            username=actor.username,
            display_name=actor.display_name,
            is_admin=actor.is_admin,
        )

    async def update_my_profile(self, actor: CurrentActor, payload: ProfileUpdateRequest) -> ProfileResponse:
        return await self._repository.update_current_profile(
            actor_id=actor.id,
            username=actor.username,
            display_name=actor.display_name,
            is_admin=actor.is_admin,
            payload=payload,
        )

    async def get_profile(self, username: str) -> ProfileResponse:
        return await self._repository.get_profile_by_username(username)

    async def list_wallets(self, actor: CurrentActor) -> list[UserWalletResponse]:
        return await self._repository.list_wallets(actor.id)

    async def create_wallet(self, actor: CurrentActor, payload: WalletCreateRequest) -> UserWalletResponse:
        return await self._repository.create_wallet(actor.id, payload)

    async def update_wallet(
        self,
        actor: CurrentActor,
        wallet_id: UUID,
        payload: WalletUpdateRequest,
    ) -> UserWalletResponse:
        return await self._repository.update_wallet(actor.id, wallet_id, payload)

    async def delete_wallet(self, actor: CurrentActor, wallet_id: UUID) -> None:
        await self._repository.delete_wallet(actor.id, wallet_id)
