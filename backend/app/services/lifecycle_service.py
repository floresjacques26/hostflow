"""
Lifecycle email service.

All public functions are fire-safe:
  - check dedup before sending
  - write EmailLog after each attempt
  - never raise exceptions to the caller

Dedup strategy: before sending, query email_logs for the same
(user_id, email_type) within a configurable window. This prevents
duplicate emails from scheduler retries, multiple webhooks, or race conditions.

Usage:
    from app.services import lifecycle_service
    await lifecycle_service.send_welcome(user, db)
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.email_log import EmailLog
from app.models.user import User
from app.services import email_service, email_templates
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Email type constants ───────────────────────────────────────────────────────

WELCOME               = "welcome"
TRIAL_STARTED         = "trial_started"
TRIAL_ENDING_3DAYS    = "trial_ending_3days"
TRIAL_ENDING_TODAY    = "trial_ending_today"
TRIAL_EXPIRED         = "trial_expired"
UPGRADE_CONFIRMATION  = "upgrade_confirmation"
PAYMENT_FAILED        = "payment_failed"
SUBSCRIPTION_CANCELED = "subscription_canceled"
ACTIVATION_REMINDER   = "activation_reminder"
REACTIVATION          = "reactivation"

# How many days back to look for a duplicate send.
# None = only send once ever (no window — any prior send blocks it).
_DEDUP_WINDOWS: dict[str, int | None] = {
    WELCOME:               None,   # once per account, ever
    TRIAL_STARTED:         90,     # once per 90-day window (handles re-subscribing)
    TRIAL_ENDING_3DAYS:    7,
    TRIAL_ENDING_TODAY:    2,
    TRIAL_EXPIRED:         14,
    UPGRADE_CONFIRMATION:  90,
    PAYMENT_FAILED:        3,      # 3-day grace before re-alerting
    SUBSCRIPTION_CANCELED: 90,
    ACTIVATION_REMINDER:   14,
    REACTIVATION:          30,
}


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _already_sent(user_id: int, email_type: str, db: AsyncSession) -> bool:
    """Return True if this email type was already sent (within dedup window)."""
    window_days = _DEDUP_WINDOWS.get(email_type)
    query = (
        select(EmailLog)
        .where(
            EmailLog.user_id == user_id,
            EmailLog.email_type == email_type,
            EmailLog.status == "sent",
        )
    )
    if window_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        query = query.where(EmailLog.created_at >= cutoff)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def _send(
    user: User,
    email_type: str,
    subject: str,
    html: str,
    text: str,
    db: AsyncSession,
) -> bool:
    """Send via provider, write EmailLog, commit. Returns True on success."""
    provider = email_service.get_provider()
    success = await provider.send(to=user.email, subject=subject, html=html, text=text)
    log = EmailLog(
        user_id=user.id,
        email_type=email_type,
        subject=subject,
        provider=type(provider).__name__,
        status="sent" if success else "failed",
        sent_at=datetime.now(timezone.utc) if success else None,
        metadata={"user_name": user.name},
    )
    db.add(log)
    await db.commit()
    if success:
        logger.info("lifecycle email sent type=%s user=%s", email_type, user.id)
    else:
        logger.warning("lifecycle email failed type=%s user=%s", email_type, user.id)
    return success


# ── Public send functions ─────────────────────────────────────────────────────

async def send_welcome(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, WELCOME, db):
            return
        subject, html, text = email_templates.welcome(user.name, settings.app_url)
        await _send(user, WELCOME, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_welcome failed user=%s: %s", user.id, exc)


async def send_trial_started(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, TRIAL_STARTED, db):
            return
        from app.core.plans import PLANS
        days = PLANS["pro"].trial_days
        subject, html, text = email_templates.trial_started(user.name, days, settings.app_url)
        await _send(user, TRIAL_STARTED, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_trial_started failed user=%s: %s", user.id, exc)


async def send_trial_ending_soon(user: User, days_left: int, db: AsyncSession) -> None:
    try:
        email_type = TRIAL_ENDING_TODAY if days_left <= 1 else TRIAL_ENDING_3DAYS
        if await _already_sent(user.id, email_type, db):
            return
        subject, html, text = email_templates.trial_ending_soon(user.name, days_left, settings.app_url)
        await _send(user, email_type, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_trial_ending_soon failed user=%s days_left=%s: %s", user.id, days_left, exc)


async def send_trial_expired(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, TRIAL_EXPIRED, db):
            return
        subject, html, text = email_templates.trial_expired(user.name, settings.app_url)
        await _send(user, TRIAL_EXPIRED, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_trial_expired failed user=%s: %s", user.id, exc)


async def send_upgrade_confirmation(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, UPGRADE_CONFIRMATION, db):
            return
        subject, html, text = email_templates.upgrade_confirmation(
            user.name, user.plan, settings.app_url
        )
        await _send(user, UPGRADE_CONFIRMATION, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_upgrade_confirmation failed user=%s: %s", user.id, exc)


async def send_payment_failed(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, PAYMENT_FAILED, db):
            return
        subject, html, text = email_templates.payment_failed(user.name, settings.app_url)
        await _send(user, PAYMENT_FAILED, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_payment_failed failed user=%s: %s", user.id, exc)


async def send_subscription_canceled(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, SUBSCRIPTION_CANCELED, db):
            return
        subject, html, text = email_templates.subscription_canceled(user.name, settings.app_url)
        await _send(user, SUBSCRIPTION_CANCELED, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_subscription_canceled failed user=%s: %s", user.id, exc)


async def send_activation_reminder(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, ACTIVATION_REMINDER, db):
            return
        subject, html, text = email_templates.activation_reminder(
            user.name, user.onboarding_step, settings.app_url
        )
        await _send(user, ACTIVATION_REMINDER, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_activation_reminder failed user=%s: %s", user.id, exc)


async def send_reactivation(user: User, db: AsyncSession) -> None:
    try:
        if await _already_sent(user.id, REACTIVATION, db):
            return
        subject, html, text = email_templates.reactivation(user.name, settings.app_url)
        await _send(user, REACTIVATION, subject, html, text, db)
    except Exception as exc:
        logger.warning("send_reactivation failed user=%s: %s", user.id, exc)
