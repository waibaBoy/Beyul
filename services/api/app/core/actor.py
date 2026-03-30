from dataclasses import dataclass
from uuid import UUID


@dataclass
class CurrentActor:
    id: UUID
    username: str
    display_name: str
    is_admin: bool
