"""
WhatsApp Business Cloud API webhook endpoints.

Registered WITHOUT /api/v1 prefix so Meta can reach:
  GET  /whatsapp/webhook   — hub challenge verification
  POST /whatsapp/webhook   — inbound messages + status updates

Security:
  - GET  is verified against per-credential webhook_verify_token
  - POST is verified against HMAC-SHA256 (X-Hub-Signature-256) using app_secret

Idempotency:
  - Inbound messages: dedup by external_message_id (MessageEntry)
  - Status updates: dedup by external_message_id + new status (only if changed)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.models.channel import Channel
from app.models.media import MediaAttachment
from app.models.thread import MessageThread, MessageEntry
from app.models.whatsapp import WhatsAppCredential
from app.services import whatsapp_service, sse_service, guest_service, draft_service
from app.services import media_service
from app.services.whatsapp_service import parse_webhook, verify_webhook_signature, decrypt_wa_token

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhook"])
logger = logging.getLogger(__name__)


# ── GET: Meta hub challenge verification ──────────────────────────────────────

@router.get("/webhook")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Meta sends this GET to verify that the webhook URL is reachable.
    We look up the credential whose webhook_verify_token matches,
    then echo back the hub.challenge.
    """
    if hub_mode != "subscribe":
        raise HTTPException(status_code=403, detail="Invalid hub.mode")

    result = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.webhook_verify_token == hub_verify_token
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        logger.warning("WhatsApp webhook verify: unknown verify_token '%s'", hub_verify_token)
        raise HTTPException(status_code=403, detail="Invalid verify token")

    # Mark as connected on first successful verification
    if cred.status == "pending_verification":
        cred.status = "connected"
        await db.commit()
        logger.info("WhatsApp credential %d verified and marked connected", cred.id)

    return Response(content=hub_challenge, media_type="text/plain")


# ── POST: Receive inbound messages + status updates ───────────────────────────

@router.post("/webhook", status_code=200)
async def whatsapp_webhook_receive(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Meta calls this for every event (inbound message, delivery status, etc.).
    Must return 200 quickly — heavy processing runs in-process but is awaited.
    Meta will retry on non-200 responses.
    """
    raw_body = await request.body()

    # ── Signature verification ────────────────────────────────────────────────
    sig = request.headers.get("X-Hub-Signature-256")
    if not verify_webhook_signature(raw_body, sig):
        logger.warning("WhatsApp webhook: invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Quick object-type check (Meta sends test pings with {"object": "whatsapp_business_account"})
    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    messages, statuses = parse_webhook(payload)

    # Process in a dedicated session (not the request session which closes after response)
    for msg in messages:
        await _process_inbound(msg)

    for st in statuses:
        await _process_status(st)

    # Always return 200 so Meta doesn't retry
    return {"status": "ok"}


# ── Internal: process one inbound message ─────────────────────────────────────

async def _process_inbound(msg) -> None:
    """Persist inbound WhatsApp message, create/update thread, trigger draft."""
    async with AsyncSessionLocal() as db:
        try:
            # ── Find credential by phone_number_id ────────────────────────────
            cred_result = await db.execute(
                select(WhatsAppCredential).where(
                    WhatsAppCredential.phone_number_id == msg.phone_number_id
                )
            )
            cred = cred_result.scalar_one_or_none()
            if not cred:
                logger.warning(
                    "WhatsApp inbound: no credential for phone_number_id=%s", msg.phone_number_id
                )
                return

            # ── Idempotency: skip if we already have this message ─────────────
            dup = await db.execute(
                select(MessageEntry).where(
                    MessageEntry.external_message_id == msg.wa_message_id
                )
            )
            if dup.scalar_one_or_none():
                logger.debug("WhatsApp: duplicate message id=%s, skipping", msg.wa_message_id)
                return

            # ── Find or create thread for this contact ────────────────────────
            # Use from_phone as the stable contact identifier
            thread = await _get_or_create_thread(msg, cred, db)

            # ── Create inbound entry ──────────────────────────────────────────
            now = datetime.utcnow()
            entry = MessageEntry(
                thread_id=thread.id,
                direction="inbound",
                body=msg.body,
                sender_name=msg.display_name or msg.from_phone,
                external_message_id=msg.wa_message_id,
                raw_payload={
                    "wa_message_id": msg.wa_message_id,
                    "from_phone": msg.from_phone,
                    "display_name": msg.display_name,
                    "message_type": msg.message_type,
                    "timestamp": msg.timestamp,
                    "media_id": msg.media_id,
                    "file_name": msg.file_name,
                },
            )
            db.add(entry)
            await db.flush()  # get entry.id before creating attachments

            # ── Create placeholder MediaAttachment for non-text messages ──────
            if msg.media_id and msg.message_type != "text":
                attachment = MediaAttachment(
                    entry_id=entry.id,
                    provider="whatsapp",
                    media_type=msg.message_type,
                    file_name=msg.file_name,
                    external_media_id=msg.media_id,
                    status="download_pending",
                )
                db.add(attachment)

            # ── Update thread timestamps ──────────────────────────────────────
            thread.last_message_at = now
            thread.last_inbound_at = now  # 24h window tracking
            thread.updated_at = now
            thread.sync_status = "synced"
            thread.last_synced_at = now

            cred.last_sync_at = now
            cred.last_error = None

            await db.commit()
            logger.info(
                "WhatsApp inbound: thread=%d from=%s wa_id=%s type=%s",
                thread.id, msg.from_phone, msg.wa_message_id, msg.message_type,
            )

            # ── SSE: notify frontend ──────────────────────────────────────────
            await sse_service.publish(cred.user_id, "thread_updated", {
                "id": thread.id,
                "status": thread.status,
                "draft_status": thread.draft_status,
                "source_type": thread.source_type,
                "guest_name": thread.guest_name,
                "last_message_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "wa_window_open": True,  # just received a message, window is open
            })

            # ── Background: media download (non-text only) ────────────────────
            if msg.media_id and msg.message_type != "text":
                access_token = decrypt_wa_token(cred.encrypted_access_token)
                await _bg_download_media(
                    media_id=msg.media_id,
                    media_type=msg.message_type,
                    file_name=msg.file_name,
                    entry_id=entry.id,
                    access_token=access_token,
                )

            # ── Background: context detection + draft generation ──────────────
            await _bg_draft(thread.id, cred.user_id)

        except Exception as exc:
            logger.exception("WhatsApp _process_inbound failed: %s", exc)
            await db.rollback()


async def _get_or_create_thread(msg, cred: WhatsAppCredential, db: AsyncSession) -> MessageThread:
    """
    Find existing open thread for this WhatsApp contact, or create a new one.
    We use (user_id, source_type='whatsapp', external_contact_id=from_phone)
    to group messages from the same sender into one ongoing thread.
    We only start a new thread when the previous one is resolved/archived.
    """
    # Look for an open/pending thread from this contact
    result = await db.execute(
        select(MessageThread)
        .where(
            MessageThread.user_id == cred.user_id,
            MessageThread.source_type == "whatsapp",
            MessageThread.external_thread_id == msg.from_phone,
            MessageThread.status.in_(["open", "pending"]),
        )
        .order_by(MessageThread.created_at.desc())
        .limit(1)
    )
    thread = result.scalar_one_or_none()

    if thread:
        return thread

    # Create guest profile if possible
    profile = await guest_service.find_or_create_profile(
        user_id=cred.user_id,
        guest_contact=msg.from_phone,
        guest_name=msg.display_name or None,
        db=db,
    )

    # Load the WhatsApp channel
    channel = None
    if cred.channel_id:
        ch_result = await db.execute(select(Channel).where(Channel.id == cred.channel_id))
        channel = ch_result.scalar_one_or_none()

    now = datetime.utcnow()
    thread = MessageThread(
        user_id=cred.user_id,
        channel_id=cred.channel_id,
        source_type="whatsapp",
        status="open",
        # Use from_phone as subject seed — agent can update later
        subject=f"WhatsApp · {msg.display_name or msg.from_phone}",
        guest_name=msg.display_name or msg.from_phone,
        guest_contact=msg.from_phone,
        guest_profile_id=profile.id if profile else None,
        # external_thread_id = from_phone (groups by contact)
        external_thread_id=msg.from_phone,
        external_source_id=msg.phone_number_id,
        sync_status="synced",
        last_message_at=now,
        last_inbound_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(thread)
    await db.flush()
    return thread


async def _bg_download_media(
    media_id: str,
    media_type: str,
    file_name: str | None,
    entry_id: int,
    access_token: str,
) -> None:
    """Download and store a WhatsApp media attachment in a dedicated session."""
    async with AsyncSessionLocal() as db:
        try:
            await media_service.process_wa_media(
                entry_id=entry_id,
                media_id=media_id,
                media_type=media_type,
                file_name=file_name,
                access_token=access_token,
                api_version=settings.whatsapp_api_version,
                db=db,
            )
        except Exception as exc:
            logger.error("_bg_download_media failed for media_id=%s: %s", media_id, exc)


async def _bg_draft(thread_id: int, user_id: int) -> None:
    """Generate draft in a separate session and publish SSE."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy.orm import selectinload as sil
        result = await db.execute(
            select(MessageThread)
            .options(sil(MessageThread.entries), sil(MessageThread.related_property))
            .where(MessageThread.id == thread_id, MessageThread.user_id == user_id)
        )
        thread = result.scalar_one_or_none()
        if not thread:
            return

        draft_text = await draft_service.generate_draft(thread, db)
        if not draft_text:
            return

        await sse_service.publish(user_id, "draft_ready", {
            "thread_id": thread_id,
            "draft": draft_text,
            "detected_context": thread.detected_context,
            "applied_template_id": thread.applied_template_id,
            "template_auto_applied": thread.template_auto_applied,
        })
        await sse_service.publish(user_id, "thread_updated", {
            "id": thread.id,
            "status": thread.status,
            "draft_status": thread.draft_status,
            "detected_context": thread.detected_context,
            "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
        })


# ── Internal: process one status update ───────────────────────────────────────

async def _process_status(st) -> None:
    """Update delivery_status on the matching outbound MessageEntry."""
    if not st.wa_message_id:
        return

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(MessageEntry).where(
                    MessageEntry.external_message_id == st.wa_message_id
                )
            )
            entry = result.scalar_one_or_none()
            if not entry:
                logger.debug("WhatsApp status: unknown wamid=%s", st.wa_message_id)
                return

            # Only update if status actually changed
            if entry.delivery_status == st.status:
                return

            entry.delivery_status = st.status

            if st.status == "failed" and st.error_title:
                # Record the failure reason on the thread for visibility
                thread_result = await db.execute(
                    select(MessageThread).where(MessageThread.id == entry.thread_id)
                )
                thread = thread_result.scalar_one_or_none()
                if thread:
                    thread.sync_status = "error"

            await db.commit()
            logger.info(
                "WhatsApp status: wamid=%s → %s", st.wa_message_id, st.status
            )

            # Notify frontend via SSE
            if entry.thread_id:
                thread_result = await db.execute(
                    select(MessageThread).where(MessageThread.id == entry.thread_id)
                )
                thread = thread_result.scalar_one_or_none()
                if thread:
                    await sse_service.publish(thread.user_id, "entry_status_updated", {
                        "thread_id": entry.thread_id,
                        "entry_id": entry.id,
                        "delivery_status": st.status,
                    })

        except Exception as exc:
            logger.exception("WhatsApp _process_status failed: %s", exc)
            await db.rollback()
