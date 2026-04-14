import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

_BLOCKED: set[str] = set()
_INITIALIZED = False


def _get_blocked_set() -> set[str]:
    global _BLOCKED, _INITIALIZED
    if not _INITIALIZED:
        raw = settings.blocked_jurisdictions or ""
        _BLOCKED = {code.strip().upper() for code in raw.split(",") if code.strip()}
        if _BLOCKED:
            logger.info("Jurisdiction gating active — blocked: %s", _BLOCKED)
        _INITIALIZED = True
    return _BLOCKED


class JurisdictionGateMiddleware(BaseHTTPMiddleware):
    """Block requests from jurisdictions listed in BLOCKED_JURISDICTIONS.

    Uses the CF-IPCountry header (set by Cloudflare/CDN) or X-Country-Code
    header (set by reverse proxy). Health endpoints are always allowed.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        blocked = _get_blocked_set()
        if not blocked:
            return await call_next(request)

        path = request.url.path
        if path.startswith("/health") or path == "/":
            return await call_next(request)

        country = (
            request.headers.get("cf-ipcountry")
            or request.headers.get("x-country-code")
            or ""
        ).strip().upper()

        if country and country in blocked:
            logger.warning("Blocked request from jurisdiction %s to %s", country, path)
            return JSONResponse(
                status_code=451,
                content={
                    "detail": "This service is not available in your jurisdiction.",
                    "jurisdiction": country,
                },
            )

        return await call_next(request)
