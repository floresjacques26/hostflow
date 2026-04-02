"""
Background lifecycle scheduler.

Uses APScheduler AsyncIOScheduler — runs inside the same async event loop as FastAPI.
Each job creates its own DB session and is fully idempotent (lifecycle_service handles dedup).

Jobs run at UTC times. Adjust hours to match your target timezone if needed.

Setup:
    from app.services.scheduler import setup_scheduler
    scheduler = setup_scheduler()
    scheduler.start()   # in lifespan startup
    scheduler.shutdown()  # in lifespan teardown
"""
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services import lifecycle_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def job_trial_reminders() -> None:
    """
    Daily 09:00 UTC: send trial-ending-soon emails to users within 3 days of expiry.
    - 1 day left  → trial_ending_today email
    - 2-3 days left → trial_ending_3days email
    Both are deduped individually, so a user gets at most one of each.
    """
    logger.info("[scheduler] job_trial_reminders: starting")
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(User).where(
                User.subscription_status == "trialing",
                User.trial_ends_at.is_not(None),
                User.trial_ends_at >= now,                     # still active
                User.trial_ends_at <= now + timedelta(days=3), # within 3-day window
                User.is_active == True,
            )
        )
        users = result.scalars().all()
        logger.info("[scheduler] job_trial_reminders: %d users in window", len(users))
        for user in users:
            days_left = max(
                0,
                (user.trial_ends_at.replace(tzinfo=timezone.utc) - now).days + 1,
            )
            await lifecycle_service.send_trial_ending_soon(user, days_left, db)


async def job_trial_expired() -> None:
    """
    Daily 09:15 UTC: email users whose trial expired in the last 25 hours.
    25h window (not 24h) provides a small buffer against clock drift / job delays.
    """
    logger.info("[scheduler] job_trial_expired: starting")
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(User).where(
                User.subscription_status == "trialing",
                User.trial_ends_at.is_not(None),
                User.trial_ends_at < now,                          # already expired
                User.trial_ends_at >= now - timedelta(hours=25),   # not too long ago
                User.is_active == True,
            )
        )
        users = result.scalars().all()
        logger.info("[scheduler] job_trial_expired: %d users", len(users))
        for user in users:
            await lifecycle_service.send_trial_expired(user, db)


async def job_activation_reminders() -> None:
    """
    Daily 10:00 UTC: nudge users who signed up 7+ days ago but haven't activated
    (onboarding_step < 2 means they haven't created a property + generated a response).
    """
    logger.info("[scheduler] job_activation_reminders: starting")
    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(User).where(
                User.onboarding_step < 2,
                User.created_at <= cutoff,
                User.is_active == True,
            )
        )
        users = result.scalars().all()
        logger.info("[scheduler] job_activation_reminders: %d users", len(users))
        for user in users:
            await lifecycle_service.send_activation_reminder(user, db)


async def job_reactivation() -> None:
    """
    Daily 10:30 UTC: win-back users whose trial expired 14-21 days ago
    without converting to a paid plan.
    """
    logger.info("[scheduler] job_reactivation: starting")
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        window_end   = now - timedelta(days=14)  # expired at least 14 days ago
        window_start = now - timedelta(days=21)  # but not more than 21 days ago

        result = await db.execute(
            select(User).where(
                User.trial_ends_at.is_not(None),
                User.trial_ends_at >= window_start,
                User.trial_ends_at <= window_end,
                User.subscription_status.not_in(["active"]),  # never converted
                User.is_active == True,
            )
        )
        users = result.scalars().all()
        logger.info("[scheduler] job_reactivation: %d users", len(users))
        for user in users:
            if not user.is_trial_active:  # double-check: trial is truly over
                await lifecycle_service.send_reactivation(user, db)


async def job_gmail_sync() -> None:
    """
    Every 15 minutes: incremental Gmail sync for all connected users.
    Each user fetches messages newer than their last_sync_at (or last 7 days
    on first run). Idempotent — duplicate messages are never created.
    """
    logger.info("[scheduler] job_gmail_sync: starting")
    from app.services.gmail_sync_service import sync_all_users
    await sync_all_users()
    logger.info("[scheduler] job_gmail_sync: done")


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_scheduler() -> AsyncIOScheduler:
    """
    Register all lifecycle jobs on the shared scheduler instance.
    Returns the scheduler (not yet started — call .start() in lifespan).
    """
    scheduler.add_job(
        job_trial_reminders,
        CronTrigger(hour=9, minute=0),
        id="trial_reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1h window if server was down
    )
    scheduler.add_job(
        job_trial_expired,
        CronTrigger(hour=9, minute=15),
        id="trial_expired",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_activation_reminders,
        CronTrigger(hour=10, minute=0),
        id="activation_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_reactivation,
        CronTrigger(hour=10, minute=30),
        id="reactivation",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # Gmail sync every 15 minutes
    scheduler.add_job(
        job_gmail_sync,
        CronTrigger(minute="*/15"),
        id="gmail_sync",
        replace_existing=True,
        misfire_grace_time=300,  # 5-minute grace window
    )
    logger.info("[scheduler] registered %d jobs", len(scheduler.get_jobs()))
    return scheduler
