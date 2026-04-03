"""
Inbound email webhook endpoint.
Called by the email provider (Postmark, Mailgun, etc.) when a forwarded
email arrives at inbox+{referral_code}@in.hostflow.io.

Security model:
- No auth header (called by email provider)
- Validated by resolving the inbox token to a user — unguessable
- Responds 200 quickly; heavy work (draft generation) runs in background
"""
import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from app.core.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.channel import Channel
from app.models.thread import MessageThread, MessageEntry
from app.services.ingestion_service import parse_inbound_email
from app.services import draft_service

router = APIRouter(prefix="/inbound", tags=["inbound"])
logger = logging.getLogger(__name__)


async def _find_or_create_email_channel(user: User, db: AsyncSession) -> Channel:
    """Find the user's email_forward channel or create one."""
    result = await db.execute(
        select(Channel).where(
            Channel.user_id == user.id,
            Channel.type == "email_forward",
        )
    )
    channel = result.scalar_one_or_none()
    if channel:
        return channel

    channel = Channel(
        user_id=user.id,
        type="email_forward",
        name="Email encaminhado",
        status="active",
    )
    db.add(channel)
    await db.flush()
    return channel


async def _process_inbound_email(thread_id: int, user_id: int) -> None:
    """Background task: generate draft for newly ingested thread."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MessageThread)
            .options(selectinload(MessageThread.entries), selectinload(MessageThread.related_property))
            .where(MessageThread.id == thread_id, MessageThread.user_id == user_id)
        )
        thread = result.scalar_one_or_none()
        if thread:
            await draft_service.generate_draft(thread, db)


@router.post("/email", include_in_schema=True)
async def receive_email(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receives a parsed inbound email from an email provider webhook.
    The inbox token (user's referral_code) must appear in the To address.
    """
    try:
        payload = await request.json()
    except Exception:
        # Some providers send form-encoded
        try:
            form = await request.form()
            payload = dict(form)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

    parsed = parse_inbound_email(payload)

    if not parsed.inbox_token:
        logger.warning("Inbound email: no inbox token found in To address")
        return {"received": True, "processed": False, "reason": "no_token"}

    if not parsed.body.strip():
        logger.warning("Inbound email: empty body, skipping")
        return {"received": True, "processed": False, "reason": "empty_body"}

    async with AsyncSessionLocal() as db:
        # Resolve user by referral_code
        result = await db.execute(
            select(User).where(User.referral_code == parsed.inbox_token)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("Inbound email: no user for token=%s", parsed.inbox_token)
            return {"received": True, "processed": False, "reason": "user_not_found"}

        # Find or create the email_forward channel
        channel = await _find_or_create_email_channel(user, db)

        now = datetime.utcnow()

        # Create thread
        thread = MessageThread(
            user_id=user.id,
            channel_id=channel.id,
            source_type="email_forward",
            subject=parsed.subject[:255] if parsed.subject else "Email recebido",
            guest_name=parsed.sender_name[:120] if parsed.sender_name else None,
            guest_contact=parsed.sender_email[:200] if parsed.sender_email else None,
            last_message_at=now,
            updated_at=now,
        )
        db.add(thread)
        await db.flush()

        # Create inbound entry
        entry = MessageEntry(
            thread_id=thread.id,
            direction="inbound",
            body=parsed.body,
            sender_name=parsed.sender_name,
            raw_payload=parsed.raw,
        )
        db.add(entry)
        await db.commit()

        thread_id = thread.id
        user_id = user.id

    # Generate draft in background (after DB session closes)
    background_tasks.add_task(_process_inbound_email, thread_id, user_id)

    logger.info("Inbound email processed: user=%s thread=%s", user_id, thread_id)
    return {"received": True, "processed": True, "thread_id": thread_id}
