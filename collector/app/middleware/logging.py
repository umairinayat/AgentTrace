"""Request/response logging middleware."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("agenttrace.collector")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every incoming request with method, path, status, and latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        start = time.monotonic()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            latency = (time.monotonic() - start) * 1000
            status = response.status_code if response else 500
            logger.info(
                "%s %s %d %.1fms",
                request.method,
                request.url.path,
                status,
                latency,
            )
