"""Token-bucket rate limiting middleware.

Uses an in-memory sliding window per IP. In production, this should
be backed by Redis for multi-instance consistency.

Limits:
- General API: 100 requests per minute per IP
- Auth endpoints: 20 requests per minute per IP
- Trading endpoints: 50 requests per minute per IP
"""

import logging
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

GENERAL_LIMIT = 100
AUTH_LIMIT = 20
TRADING_LIMIT = 50
WINDOW_SECONDS = 60


class _SlidingWindow:
    __slots__ = ("timestamps",)

    def __init__(self):
        self.timestamps: list[float] = []

    def hit(self, now: float, limit: int, window: float) -> bool:
        cutoff = now - window
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        if len(self.timestamps) >= limit:
            return False
        self.timestamps.append(now)
        return True

    @property
    def count(self) -> int:
        return len(self.timestamps)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._windows: dict[str, _SlidingWindow] = defaultdict(_SlidingWindow)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        return request.client.host if request.client else "unknown"

    def _get_limit(self, path: str) -> int:
        if path.startswith("/api/v1/auth"):
            return AUTH_LIMIT
        if any(path.startswith(p) for p in (
            "/api/v1/orders", "/api/v1/trading", "/api/v1/transfers"
        )):
            return TRADING_LIMIT
        return GENERAL_LIMIT

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path.startswith("/health") or path == "/":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        limit = self._get_limit(path)
        bucket_key = f"{client_ip}:{limit}"

        now = time.monotonic()
        window = self._windows[bucket_key]

        if not window.hit(now, limit, WINDOW_SECONDS):
            remaining_time = int(WINDOW_SECONDS - (now - window.timestamps[0]))
            logger.warning(
                "Rate limit exceeded for %s on %s (%d/%d)",
                client_ip, path, window.count, limit,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after_seconds": max(remaining_time, 1),
                },
                headers={
                    "Retry-After": str(max(remaining_time, 1)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - window.count))
        return response
