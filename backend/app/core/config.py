from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HostFlow API"
    debug: bool = False

    # Deployment environment — controls logging format, SQL echo, error verbosity
    # Values: local | staging | production
    environment: Literal["local", "staging", "production"] = "local"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/hostflow"

    # Auth
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # CORS
    # Comma-separated list of allowed origins.
    # Example (production): https://app.hostflow.com.br,https://hostflow.com.br
    # Example (local):       http://localhost:5173
    frontend_url: str = "http://localhost:5173"

    # ── Email (Resend) ────────────────────────────────────────────────────────
    resend_api_key: str = ""
    email_from: str = "HostFlow <noreply@hostflow.com.br>"
    # Public URL of the backend — used in email links and webhook setup hints.
    # Production: https://api.hostflow.com.br
    app_url: str = "http://localhost:8000"

    # ── SLA thresholds ────────────────────────────────────────────────────────
    sla_open_overdue_hours: int = 4    # open thread → overdue after N hours
    sla_pending_stale_hours: int = 24  # pending thread → stale after N hours

    # ── Stripe ────────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_business_monthly: str = ""

    # Plan pricing (BRL cents) — used for estimated MRR when Stripe is not connected
    plan_price_pro_brl: int = 4900        # R$ 49,00
    plan_price_business_brl: int = 12900  # R$ 129,00

    # ── Google / Gmail OAuth ──────────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    # Must exactly match the URI registered in Google Cloud Console.
    # Production: https://api.hostflow.com.br/api/v1/gmail/callback
    gmail_redirect_uri: str = "http://localhost:8000/api/v1/gmail/callback"
    # Fernet key for encrypting OAuth tokens at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    gmail_encryption_key: str = ""
    # Max Gmail threads to fetch per sync run per user (tune for API quota)
    gmail_sync_max_threads: int = 30

    # ── File Storage ──────────────────────────────────────────────────────────
    # Provider: local | s3
    # local: saves to storage_local_root directory, served via /media/ static route
    # s3:    uses S3-compatible API (AWS S3 or Cloudflare R2) — required in production
    storage_provider: str = "local"
    storage_local_root: str = "media"
    storage_local_url_base: str = "http://localhost:8000/media"
    # S3 / Cloudflare R2
    storage_s3_bucket: str = ""
    storage_s3_region: str = "auto"          # "auto" for R2
    storage_s3_endpoint_url: str = ""        # e.g. https://<account>.r2.cloudflarestorage.com
    storage_s3_access_key_id: str = ""
    storage_s3_secret_access_key: str = ""
    storage_s3_public_base_url: str = ""     # CDN base URL for public buckets; empty = signed URLs

    # ── WhatsApp Business Cloud API (Meta) ────────────────────────────────────
    whatsapp_access_token: str = ""
    whatsapp_app_secret: str = ""            # used to verify X-Hub-Signature-256
    whatsapp_api_version: str = "v19.0"

    # ── Scheduler ─────────────────────────────────────────────────────────────
    # Set False in test environments to skip background jobs.
    # NOTE: scheduler runs in-process (same uvicorn worker). Keep workers=1 in
    # production to avoid duplicate job executions.
    scheduler_enabled: bool = True

    # ── Observability ─────────────────────────────────────────────────────────
    # Sentry DSN for error tracking. Leave empty to disable.
    # Get from: https://sentry.io → Project → Settings → Client Keys
    sentry_dsn: str = ""
    # traces_sample_rate: fraction of transactions to trace (0.0–1.0).
    # 0.1 = 10% — good default for production; 0.0 disables performance monitoring.
    sentry_traces_sample_rate: float = 0.1
    # Log level: DEBUG | INFO | WARNING | ERROR
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @property
    def allowed_origins(self) -> list[str]:
        """
        CORS origins derived from frontend_url.
        Always includes localhost:5173 in non-production environments.
        """
        origins = [o.strip() for o in self.frontend_url.split(",") if o.strip()]
        if not self.is_production:
            if "http://localhost:5173" not in origins:
                origins.append("http://localhost:5173")
        return origins

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
