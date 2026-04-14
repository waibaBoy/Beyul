from pydantic import BaseModel


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushSubscribeResponse(BaseModel):
    status: str
    endpoint: str


class PushStatsResponse(BaseModel):
    total_subscriptions: int
    unique_profiles: int
