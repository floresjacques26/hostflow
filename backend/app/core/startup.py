"""
Startup validation — runs once during FastAPI lifespan before accepting traffic.

Checks performed:
  1. Required environment variables are non-empty
  2. Database is reachable (simple SELECT 1)
  3. Soft warnings for optional but recommended variables

Fail-fast philosophy: if a critical config is missing, the server refuses to
start with a clear error message rather than crashing at runtime.
"""
import logging
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ── Required variables ────────────────────────────────────────────────────────
# The server will NOT start if any of these are missing / still at default.

_REQUIRED: list[tuple[str, str, str]] = [
    # (settings attribute, env var name, hint)
    (
        "database_url",
        "DATABASE_URL",
        "PostgreSQL connection string. "
        "Example: postgresql+asyncpg://postgres:password@localhost:5432/hostflow",
    ),
    (
        "secret_key",
        "SECRET_KEY",
        "JWT signing key. Generate with: "
        "python -c \"import secrets; print(secrets.token_hex(32))\"",
    ),
    (
        "openai_api_key",
        "OPENAI_API_KEY",
        "OpenAI API key. Get one at https://platform.openai.com/api-keys",
    ),
]

# Default placeholder values that indicate the variable was never filled in
_UNSAFE_DEFAULTS = {
    "change-this-secret-key-in-production",
    "change-this-to-a-strong-random-secret-in-production",
    "sk-...",
    "sk_test_...",
}

# ── Production-only requirements — fail if environment=production and missing ─

_REQUIRED_IN_PRODUCTION: list[tuple[str, str, str]] = [
    (
        "stripe_secret_key",
        "STRIPE_SECRET_KEY",
        "Stripe live key required in production. Get from https://dashboard.stripe.com/apikeys",
    ),
    (
        "stripe_webhook_secret",
        "STRIPE_WEBHOOK_SECRET",
        "Stripe webhook secret required in production. "
        "Register endpoint at https://dashboard.stripe.com/webhooks",
    ),
    (
        "resend_api_key",
        "RESEND_API_KEY",
        "Resend API key required in production. Get from https://resend.com/api-keys",
    ),
    (
        "gmail_encryption_key",
        "GMAIL_ENCRYPTION_KEY",
        "Fernet encryption key required in production for Gmail OAuth token storage. "
        "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
    ),
    (
        "sentry_dsn",
        "SENTRY_DSN",
        "Sentry DSN strongly recommended in production for error tracking. "
        "Get from https://sentry.io → Project → Settings → Client Keys. "
        "Set to 'disabled' to explicitly opt out.",
    ),
]

# ── Optional variables — warn if missing ──────────────────────────────────────

_OPTIONAL: list[tuple[str, str]] = [
    ("stripe_secret_key",    "STRIPE_SECRET_KEY    — needed for billing features"),
    ("resend_api_key",       "RESEND_API_KEY       — needed for transactional emails"),
    ("gmail_encryption_key", "GMAIL_ENCRYPTION_KEY — needed for Gmail integration"),
]


def _check_env() -> list[str]:
    """Return list of critical error messages. Empty = all good."""
    errors: list[str] = []

    for attr, env_name, hint in _REQUIRED:
        value = getattr(settings, attr, "")
        if not value or value in _UNSAFE_DEFAULTS:
            errors.append(
                f"  ✗  {env_name} is not set.\n"
                f"     {hint}"
            )

    # Production: enforce additional required variables
    if settings.is_production:
        for attr, env_name, hint in _REQUIRED_IN_PRODUCTION:
            value = getattr(settings, attr, "")
            # Allow explicit opt-out with the literal string "disabled"
            if value == "disabled":
                continue
            if not value or value in _UNSAFE_DEFAULTS:
                errors.append(
                    f"  ✗  {env_name} is not set (required in production).\n"
                    f"     {hint}"
                )

    # Production: reject obviously unsafe defaults
    if settings.is_production and settings.storage_provider == "local":
        errors.append(
            "  ✗  STORAGE_PROVIDER=local is not suitable for production.\n"
            "     Set STORAGE_PROVIDER=s3 and configure S3/R2 credentials."
        )

    return errors


def _warn_optional() -> None:
    """Log warnings for missing optional variables."""
    for attr, description in _OPTIONAL:
        value = getattr(settings, attr, "")
        if not value or value in _UNSAFE_DEFAULTS:
            logger.warning("Optional variable not set: %s", description)


async def _check_db() -> str | None:
    """Try a simple query against the database. Returns error string or None."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return None
    except Exception as exc:
        return (
            f"  ✗  Cannot connect to the database.\n"
            f"     DATABASE_URL: {settings.database_url!r}\n"
            f"     Error: {exc}\n"
            f"     Ensure PostgreSQL is running and the URL is correct."
        )


async def run_startup_checks() -> None:
    """
    Run all startup checks. Logs a summary and exits with code 1 on failure.
    Call this inside FastAPI's lifespan, before create_tables().
    """
    logger.info("Running startup checks...")

    # ── Env var checks (synchronous) ──────────────────────────────────────────
    env_errors = _check_env()

    # ── Database check (async) ────────────────────────────────────────────────
    db_error = await _check_db()
    if db_error:
        env_errors.append(db_error)

    # ── Report ────────────────────────────────────────────────────────────────
    if env_errors:
        border = "─" * 70
        print(f"\n{border}", file=sys.stderr)
        print("  HostFlow failed to start — fix the following issues:", file=sys.stderr)
        print(border, file=sys.stderr)
        for err in env_errors:
            print(f"\n{err}", file=sys.stderr)
        print(f"\n{border}\n", file=sys.stderr)
        sys.exit(1)

    # ── Optional variable warnings ────────────────────────────────────────────
    _warn_optional()

    logger.info("Startup checks passed.")
