"""Browser push notification scaffolding.

Manages push subscription registration and notification dispatch.
Uses Web Push protocol (VAPID). In development mode, falls back to
storing notifications for polling.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)


class PushSubscription:
    def __init__(self, profile_id: UUID, endpoint: str, p256dh: str, auth: str, created_at: datetime):
        self.profile_id = profile_id
        self.endpoint = endpoint
        self.p256dh = p256dh
        self.auth = auth
        self.created_at = created_at


class PushNotificationService:
    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory
        self._subscriptions: dict[str, PushSubscription] = {}

    async def register_subscription(
        self,
        profile_id: UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
    ) -> dict:
        sub = PushSubscription(
            profile_id=profile_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            created_at=datetime.now(timezone.utc),
        )
        key = f"{profile_id}:{endpoint}"
        self._subscriptions[key] = sub
        logger.info("Push subscription registered for %s", profile_id)
        return {"status": "registered", "endpoint": endpoint}

    async def unregister_subscription(self, profile_id: UUID, endpoint: str) -> dict:
        key = f"{profile_id}:{endpoint}"
        self._subscriptions.pop(key, None)
        logger.info("Push subscription removed for %s", profile_id)
        return {"status": "unregistered"}

    async def send_push(self, profile_id: UUID, title: str, body: str, url: str | None = None) -> int:
        """Send push notification to all subscriptions for a user.

        Returns number of notifications attempted. In production this
        would use the Web Push protocol (pywebpush). For now it logs
        the notification for development purposes.
        """
        sent = 0
        for key, sub in self._subscriptions.items():
            if sub.profile_id != profile_id:
                continue
            logger.info(
                "PUSH [%s] -> %s: %s - %s (url=%s)",
                profile_id, sub.endpoint[:50], title, body, url,
            )
            sent += 1
        return sent

    async def broadcast_push(self, profile_ids: list[UUID], title: str, body: str, url: str | None = None) -> int:
        total = 0
        for pid in profile_ids:
            total += await self.send_push(pid, title, body, url)
        return total

    def get_stats(self) -> dict:
        profiles = set()
        for sub in self._subscriptions.values():
            profiles.add(sub.profile_id)
        return {
            "total_subscriptions": len(self._subscriptions),
            "unique_profiles": len(profiles),
        }
