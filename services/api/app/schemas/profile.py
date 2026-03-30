from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str
    bio: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class UserWalletResponse(BaseModel):
    id: UUID
    chain_name: str
    wallet_address: str
    is_primary: bool


class WalletCreateRequest(BaseModel):
    chain_name: str
    wallet_address: str
    is_primary: bool = False


class WalletUpdateRequest(BaseModel):
    is_primary: bool
