import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import create_tables, AsyncSessionLocal
from app.core.logging_config import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.services.seed import seed_default_templates
from app.routes import (
    auth, messages, calculator, templates, properties, billing, webhooks,
    onboarding, analytics, admin_dashboard, admin_users, referrals, testimonials,
    admin_acquisition, channels, inbox, inbound, admin_inbox, sse, guests, gmail,
    auto_send, whatsapp, events,
)
from app.routes import whatsapp_webhook
from app.routes import health as health_router

# Import models so SQLAlchemy registers them before create_tables()
from app.models import (  # noqa: F401
    user, conversation, template, property, usage, event, email_log,
    referral, partner, testimonial, channel, thread, guest, gmail as gmail_model,
    auto_send as auto_send_model, whatsapp as whatsapp_model,
    media, wa_template,
)

# ── Logging ───────────────────────────────────────────────────────────────────
# Configure early so startup checks and lifespan events are captured.
configure_logging(
    level=settings.log_level,
    json_logs=settings.is_production,
)

# ── Sentry ────────────────────────────────────────────────────────────────────
if settings.sentry_dsn and settings.sentry_dsn != "disabled":
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        # Never send raw SQL query values or request bodies to Sentry
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.startup import run_startup_checks
    await run_startup_checks()

    await create_tables()
    async with AsyncSessionLocal() as db:
        await seed_default_templates(db)

    if settings.scheduler_enabled:
        from app.services.scheduler import setup_scheduler
        sched = setup_scheduler()
        sched.start()
        yield
        sched.shutdown(wait=False)
    else:
        yield


# ── Docs visibility ───────────────────────────────────────────────────────────
# Hide /docs and /redoc in production — they expose your full API surface.
# Remove this if you want public docs.
_docs_url = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"

app = FastAPI(
    title=settings.app_name,
    version="0.5.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(calculator.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(properties.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(admin_dashboard.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(admin_acquisition.router, prefix="/api/v1")
app.include_router(referrals.router, prefix="/api/v1")
app.include_router(testimonials.router, prefix="/api/v1")
app.include_router(channels.router, prefix="/api/v1")
# SSE must be registered before inbox so /inbox/events is not swallowed by /inbox/{thread_id}
app.include_router(sse.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(guests.router, prefix="/api/v1")
app.include_router(gmail.router, prefix="/api/v1")
app.include_router(auto_send.router, prefix="/api/v1")
app.include_router(whatsapp.router, prefix="/api/v1")
app.include_router(admin_inbox.router, prefix="/api/v1")
# Inbound email webhook — no /api/v1 prefix (called by email providers)
app.include_router(inbound.router)
# Stripe webhook — no /api/v1 prefix (raw body required)
app.include_router(webhooks.router)
# WhatsApp webhook — no /api/v1 prefix (Meta calls this directly)
app.include_router(whatsapp_webhook.router)


# Serve local media files in development
if settings.storage_provider == "local":
    _media_root = settings.storage_local_root
    os.makedirs(_media_root, exist_ok=True)
    app.mount("/media", StaticFiles(directory=_media_root), name="media")


