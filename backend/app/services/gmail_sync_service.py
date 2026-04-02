"""
Gmail incremental sync service.

Design principles:
  - Idempotent: safe to run multiple times; duplicates never created.
  - Incremental: only fetches messages newer than last_sync_at.
  - Per-user: each user's credential is independent.
  - Safe: errors on one user/thread never crash the whole job.

Entry points:
  sync_all_users()   — called by the APScheduler job every 15 minutes
  sync_user(user_id) — called on-demand (manual "Sync Now" from UI)
"""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.channel import Channel
from app.models.gmail import GmailCredential
from app.models.guest import GuestProfile
from app.models.thread import MessageThread, MessageEntry
from app.services import gmail_service, guest_service, context_service, sse_service

logger = logging.getLogger(__name__)

# How far back to sync when there is no last_sync_at (first sync)
INITIAL_SYNC_DAYS = 7
# Maximum threads to process per sync run per user
MAX_THREADS_PER_RUN = 30


# ── Channel helpers ───────────────────────────────────────────────────────────

async def _ensure_gmail_channel(user_id: int, gmail_email: str, db: AsyncSession) -> Channel:
    """Find or create the Gmail channel for this user/account."""
    result = await db.execute(
        select(Channel).where(
            Channel.user_id == user_id,
            Channel.type == "gmail",
            Channel.external_id == gmail_email,
        )
    )
    channel = result.scalar_one_or_none()
    if channel:
        if channel.status != "active":
            channel.status = "active"
            await db.flush()
        return channel

    channel = Channel(
        user_id=user_id,
        type="gmail",
        name=f"Gmail · {gmail_email}",
        external_id=gmail_email,
        status="active",
    )
    db.add(channel)
    await db.flush()
    return channel


# ── Thread / entry deduplication ─────────────────────────────────────────────

async def _find_thread_by_external(
    user_id: int, gmail_thread_id: str, db: AsyncSession
) -> MessageThread | None:
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.user_id == user_id,
            MessageThread.external_thread_id == gmail_thread_id,
        )
    )
    return result.scalar_one_or_none()


async def _entry_exists(external_message_id: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(MessageEntry.id).where(
            MessageEntry.external_message_id == external_message_id
        )
    )
    return result.scalar_one_or_none() is not None


# ── Core sync for a single Gmail thread ──────────────────────────────────────

async def _sync_gmail_thread(
    gmail_thread_id: str,
    user_id: int,
    channel: Channel,
    service,
    db: AsyncSession,
) -> bool:
    """
    Sync one Gmail thread into HostFlow.
    Returns True if anything was created/updated.
    """
    messages = gmail_service.get_thread_messages(service, gmail_thread_id)
    if not messages:
        return False

    now = datetime.utcnow()

    # Check if HostFlow thread already exists for this Gmail thread
    hf_thread = await _find_thread_by_external(user_id, gmail_thread_id, db)

    if hf_thread is None:
        # First message in the thread determines metadata
        first = messages[0]

        # Auto-match or create guest profile
        profile: GuestProfile | None = None
        if first.sender_email:
            profile = await guest_service.find_or_create_profile(
                user_id=user_id,
                guest_contact=first.sender_email,
                guest_name=first.sender_name,
                db=db,
            )

        hf_thread = MessageThread(
            user_id=user_id,
            channel_id=channel.id,
            source_type="gmail",
            external_thread_id=gmail_thread_id,
            external_source_id=channel.external_id,
            sync_status="synced",
            last_synced_at=now,
            subject=(first.subject or "")[:255] or "Gmail",
            guest_name=(first.sender_name or "")[:120] or None,
            guest_contact=(first.sender_email or "")[:200] or None,
            guest_profile_id=profile.id if profile else None,
            last_message_at=first.sent_at or now,
            updated_at=now,
        )
        db.add(hf_thread)
        await db.flush()  # get hf_thread.id
        logger.debug("Created HostFlow thread for Gmail thread %s", gmail_thread_id)
    else:
        # Update sync housekeeping
        hf_thread.sync_status = "synced"
        hf_thread.last_synced_at = now

    new_entries = 0
    latest_sent_at = hf_thread.last_message_at

    for msg in messages:
        if await _entry_exists(msg.gmail_message_id, db):
            continue  # already ingested

        # Determine direction: inbound = from guest, outbound = sent by us
        # We detect "ours" by checking if the sender is the connected Gmail account
        our_email = channel.external_id or ""
        direction = "outbound" if our_email.lower() in (msg.sender_email or "").lower() else "inbound"

        entry = MessageEntry(
            thread_id=hf_thread.id,
            direction=direction,
            body=msg.body or msg.snippet,
            sender_name=msg.sender_name,
            external_message_id=msg.gmail_message_id,
            sent_via_provider=(direction == "outbound"),
            delivery_status="sent" if direction == "outbound" else None,
            raw_payload={
                "gmail_message_id": msg.gmail_message_id,
                "gmail_thread_id": msg.gmail_thread_id,
                "message_id_header": msg.message_id_header,
                "references": msg.references_header,
                "subject": msg.subject,
                "from": msg.sender_email,
                "to": msg.to_email,
            },
        )
        db.add(entry)
        new_entries += 1

        if msg.sent_at and (latest_sent_at is None or msg.sent_at > latest_sent_at):
            latest_sent_at = msg.sent_at

    if new_entries > 0:
        hf_thread.last_message_at = latest_sent_at or now
        hf_thread.updated_at = now
        await db.flush()

        # Run context detection on the thread if not yet classified
        if not hf_thread.detected_context:
            result = await db.execute(
                select(MessageThread)
                .options(selectinload(MessageThread.entries))
                .where(MessageThread.id == hf_thread.id)
            )
            thread_with_entries = result.scalar_one_or_none()
            if thread_with_entries:
                detected = await context_service.detect_context(thread_with_entries)
                if detected:
                    hf_thread.detected_context = detected

    return new_entries > 0


# ── Per-user sync ─────────────────────────────────────────────────────────────

async def sync_user(user_id: int, db: AsyncSession | None = None) -> dict:
    """
    Sync all recent Gmail threads for a single user.
    Returns a summary dict.
    Can be called with an existing session (from tests) or creates its own.
    """
    own_session = db is None
    if own_session:
        db = AsyncSessionLocal()

    summary = {
        "user_id": user_id,
        "threads_processed": 0,
        "new_entries": 0,
        "errors": 0,
        "status": "ok",
    }

    try:
        cred_result = await db.execute(
            select(GmailCredential).where(
                GmailCredential.user_id == user_id,
                GmailCredential.sync_enabled == True,  # noqa: E712
            )
        )
        cred = cred_result.scalar_one_or_none()
        if not cred:
            summary["status"] = "no_credentials"
            return summary

        # Build Gmail API service (refreshes token if needed)
        try:
            service = await gmail_service.get_gmail_service(cred, db)
        except RuntimeError as exc:
            logger.error("Gmail auth failed for user %s: %s", user_id, exc)
            cred.sync_error = str(exc)
            cred.updated_at = datetime.utcnow()
            # Mark channel as error
            channel_result = await db.execute(
                select(Channel).where(
                    Channel.user_id == user_id,
                    Channel.type == "gmail",
                )
            )
            ch = channel_result.scalar_one_or_none()
            if ch:
                ch.status = "error"
            await db.commit()
            summary["status"] = "auth_error"
            summary["errors"] = 1
            return summary

        channel = await _ensure_gmail_channel(user_id, cred.gmail_email, db)

        after_date = cred.last_sync_at
        if after_date is None:
            after_date = datetime.utcnow() - timedelta(days=INITIAL_SYNC_DAYS)

        thread_ids = gmail_service.list_thread_ids(
            service, after_date=after_date, max_results=MAX_THREADS_PER_RUN
        )
        logger.info(
            "Gmail sync user=%s: found %d threads after %s",
            user_id, len(thread_ids), after_date.isoformat(),
        )

        for gmail_thread_id in thread_ids:
            try:
                had_new = await _sync_gmail_thread(
                    gmail_thread_id, user_id, channel, service, db
                )
                summary["threads_processed"] += 1
                if had_new:
                    summary["new_entries"] += 1
            except Exception as exc:
                logger.exception(
                    "Error syncing Gmail thread %s for user %s: %s",
                    gmail_thread_id, user_id, exc,
                )
                summary["errors"] += 1

        await db.commit()

        # Update last_sync_at after successful commit
        now = datetime.utcnow()
        cred.last_sync_at = now
        cred.sync_error = None
        cred.updated_at = now
        await db.commit()

        # SSE: notify user's sessions that threads may have changed
        if summary["new_entries"] > 0:
            await sse_service.publish(user_id, "gmail_synced", {
                "threads_processed": summary["threads_processed"],
                "new_entries": summary["new_entries"],
            })

        logger.info(
            "Gmail sync complete user=%s threads=%d new=%d errors=%d",
            user_id,
            summary["threads_processed"],
            summary["new_entries"],
            summary["errors"],
        )

    except Exception as exc:
        logger.exception("Gmail sync crashed for user %s: %s", user_id, exc)
        summary["status"] = "crashed"
        summary["errors"] += 1
        try:
            await db.rollback()
        except Exception:
            pass
    finally:
        if own_session:
            await db.close()

    return summary


# ── Global sync (all users with active credentials) ───────────────────────────

async def sync_all_users() -> None:
    """Run sync for every user with active Gmail credentials. Called by scheduler."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(GmailCredential.user_id).where(
                GmailCredential.sync_enabled == True  # noqa: E712
            )
        )
        user_ids = result.scalars().all()

    logger.info("[gmail_sync] Starting sync for %d users", len(user_ids))
    for uid in user_ids:
        await sync_user(uid)
    logger.info("[gmail_sync] Done")
