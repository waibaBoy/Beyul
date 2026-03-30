from pydantic import BaseModel, Field

from app.schemas.market_request import MarketRequestResponse
from app.schemas.post import PostResponse


class ReviewQueueResponse(BaseModel):
    pending_posts: list[PostResponse] = Field(default_factory=list)
    pending_market_requests: list[MarketRequestResponse] = Field(default_factory=list)
