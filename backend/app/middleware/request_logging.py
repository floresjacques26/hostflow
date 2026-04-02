"""
Request / response logging middleware.

Logs one structured line per request with:
  method, path, status_code, duration_ms, client IP

Skips /health* endpoints to avoid log noise from platform health checks.
In production (JSON mode) these become queryable structured fields.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("hostflow.http")

# Paths that are checked frequently by load balancers / uptime monitors.
# Logging them every few seconds adds noise without value.
_SKIP_PATHS = {"/health", "/health/ready", "/health/info"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        level = logging.WARNING if response.status_code >= 500 else logging.INFO

        logger.log(
            level,
            "%s %s %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
            },
        )

        return response
