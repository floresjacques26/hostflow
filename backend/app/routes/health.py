"""
Health check endpoints.

  GET /health        — liveness probe (always 200 if process is up)
  GET /health/ready  — readiness probe (checks DB connection)
  GET /health/info   — diagnostics (non-sensitive config summary)

Platform usage:
  - Railway / Fly / Render use /health or /health/ready for deployment health gates.
  - Uptime monitors (BetterStack, UptimeRobot) should target /health.
  - /health/info is useful for debugging deployed config without exposing secrets.
"""
import logging
import time
from importlib.metadata import version as pkg_version

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

_START_TIME = time.time()


@router.get("/health", include_in_schema=False)
async def liveness():
    """
    Liveness probe — returns 200 if the process is running.
    Never checks external dependencies (DB, third-party APIs).
    If this fails, the process itself is broken and should be restarted.
    """
    return {"status": "ok", "app": settings.app_name}


@router.get("/health/ready")
async def readiness():
    """
    Readiness probe — returns 200 only when the service can handle traffic.
    Checks: database connectivity.

    Returns 503 if any critical dependency is unavailable.
    """
    checks: dict[str, dict] = {}
    healthy = True

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        logger.error("Readiness check: database unreachable — %s", exc)
        checks["database"] = {"status": "error", "detail": str(exc)}
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )


@router.get("/health/info")
async def info():
    """
    Diagnostics endpoint — non-sensitive config summary for debugging.

    Shows which integrations are configured (without exposing secrets).
    Access should be restricted behind auth in production if preferred,
    but the info is non-sensitive by design.
    """
    uptime_seconds = round(time.time() - _START_TIME)

    def _masked(value: str) -> str:
        """Return 'configured' / 'not set' — never the actual value."""
        return "configured" if value else "not set"

    integrations = {
        "stripe":    _masked(settings.stripe_secret_key),
        "resend":    _masked(settings.resend_api_key),
        "gmail":     _masked(settings.google_client_id),
        "whatsapp":  _masked(settings.whatsapp_access_token),
        "sentry":    _masked(settings.sentry_dsn),
    }

    storage = {
        "provider": settings.storage_provider,
        "s3_bucket": settings.storage_s3_bucket or "not set"
        if settings.storage_provider == "s3"
        else "n/a",
    }

    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "uptime_seconds": uptime_seconds,
        "scheduler_enabled": settings.scheduler_enabled,
        "integrations": integrations,
        "storage": storage,
        "python_deps": {
            "fastapi": _safe_version("fastapi"),
            "sqlalchemy": _safe_version("sqlalchemy"),
            "pydantic": _safe_version("pydantic"),
        },
    }


def _safe_version(package: str) -> str:
    try:
        return pkg_version(package)
    except Exception:
        return "unknown"
