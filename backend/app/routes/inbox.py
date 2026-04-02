import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession  # used in type hints for _bg_auto_send
from sqlalchemy import select, desc, or_, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.models.thread import MessageThread, MessageEntry
from app.schemas.inbox import (
    ThreadCreate, ThreadUpdate, ThreadOut, ThreadDetailOut,
    EntryCreate, EntryOut, BulkActionRequest,
)
from app.models.gmail import GmailCredential
from app.services import context_service, draft_service, sse_service, guest_service
from app.services import gmail_service, auto_send_service

router = APIRouter(prefix="/inbox", tags=["inbox"])

VALID_STATUSES = {"open", "pending", "resolved", "archived"}
_BULK_STATUS_MAP = {
    "resolve": "resolved",
    "archive": "archived",
    "pending": "pending",
    "open":    "open",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _load_thread(thread_id: int, user_id: int, db: AsyncSession) -> MessageThread:
    from app.models.media import MediaAttachment
    result = await db.execute(
        select(MessageThread)
        .options(
            selectinload(MessageThread.entries).selectinload(MessageEntry.attachments),
            selectinload(MessageThread.property),
            selectinload(MessageThread.channel),
        )
        .where(MessageThread.id == thread_id, MessageThread.user_id == user_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return thread


def _thread_event_data(thread: MessageThread) -> dict:
    """Minimal dict for SSE thread_updated / thread_created events."""
    return {
        "id": thread.id,
        "status": thread.status,
        "draft_status": thread.draft_status,
        "detected_context": thread.detected_context,
        "guest_name": thread.guest_name,
        "subject": thread.subject,
        "source_type": thread.source_type,
        "guest_profile_id": thread.guest_profile_id,
        "is_overdue": thread.is_overdue,
        "is_stale": thread.is_stale,
        "applied_template_id": thread.applied_template_id,
        "template_auto_applied": thread.template_auto_applied,
        "auto_send_decision": thread.auto_send_decision,
        "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
    }


async def _bg_draft_and_notify(thread_id: int, user_id: int) -> None:
    """Background: generate draft → evaluate auto-send → send or notify."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MessageThread)
            .options(selectinload(MessageThread.entries), selectinload(MessageThread.property))
            .where(MessageThread.id == thread_id, MessageThread.user_id == user_id)
        )
        thread = result.scalar_one_or_none()
        if not thread:
            return

        draft_text = await draft_service.generate_draft(thread, db)
        if not draft_text:
            return

        # ── Auto-send evaluation ──────────────────────────────────────────────
        # Grab the guest's original message for sentiment check
        inbound = [e for e in thread.entries if e.direction == "inbound"]
        guest_message = sorted(inbound, key=lambda e: e.created_at)[-1].body if inbound else ""

        decision = await auto_send_service.evaluate_auto_send(
            thread=thread,
            db=db,
            draft_body=draft_text,
            guest_message=guest_message,
        )
        await auto_send_service.log_decision(thread, decision, db)

        if decision.should_auto_send:
            # Execute send: Gmail or plain outbound entry
            await _bg_auto_send(thread, draft_text, user_id, db)
        else:
            await db.commit()

        # ── SSE notifications ─────────────────────────────────────────────────
        await sse_service.publish(user_id, "draft_ready", {
            "thread_id": thread_id,
            "draft": draft_text,
            "detected_context": thread.detected_context,
            "applied_template_id": thread.applied_template_id,
            "template_auto_applied": thread.template_auto_applied,
            "auto_send_decision": decision.decision,
            "auto_send_reason": decision.reason_code,
        })
        await sse_service.publish(user_id, "thread_updated", _thread_event_data(thread))


async def _bg_auto_send(
    thread: MessageThread,
    draft_text: str,
    user_id: int,
    db: AsyncSession,
) -> None:
    """
    Execute auto-send: Gmail API for gmail threads, plain outbound entry otherwise.
    Called only after evaluate_auto_send() returns should_auto_send=True.
    """
    from sqlalchemy import select as _select
    from app.models.gmail import GmailCredential as _GmailCred

    now = datetime.now(timezone.utc)

    if thread.source_type == "gmail" and thread.external_thread_id:
        cred_result = await db.execute(
            _select(_GmailCred).where(_GmailCred.user_id == user_id)
        )
        cred = cred_result.scalar_one_or_none()

        if cred:
            try:
                service = await gmail_service.get_gmail_service(cred, db)
                inbound_entries = [
                    e for e in sorted(thread.entries, key=lambda x: x.created_at)
                    if e.direction == "inbound" and e.external_message_id
                ]
                reply_to_msg_id = None
                references = None
                to_email = thread.guest_contact or ""
                if inbound_entries:
                    last = inbound_entries[-1]
                    if last.raw_payload:
                        reply_to_msg_id = last.raw_payload.get("message_id_header")
                        references = last.raw_payload.get("references")
                        if not to_email:
                            to_email = last.raw_payload.get("from", "")

                sent = await gmail_service.send_reply(
                    service=service,
                    to=to_email,
                    subject=thread.subject or "Re: (sem assunto)",
                    body=draft_text,
                    gmail_thread_id=thread.external_thread_id,
                    reply_to_message_id=reply_to_msg_id,
                    references=references,
                )
                entry = MessageEntry(
                    thread_id=thread.id,
                    direction="outbound",
                    body=draft_text,
                    sender_name="HostFlow IA (Auto)",
                    external_message_id=sent.get("id"),
                    sent_via_provider=True,
                    delivery_status="sent",
                )
                db.add(entry)
                thread.draft_status = "replied"
                thread.status = "pending"
                thread.last_message_at = now
                thread.updated_at = now
                await db.commit()
                logger.info("auto_send: Gmail reply sent for thread=%d", thread.id)
                return
            except Exception as exc:
                logger.error("auto_send: Gmail send failed for thread=%d: %s", thread.id, exc)
                # Fall through to create a draft entry (don't auto-send)
                thread.auto_send_decision = "blocked"
                await db.commit()
                return

    # Non-Gmail or Gmail fallback: create a plain outbound entry
    entry = MessageEntry(
        thread_id=thread.id,
        direction="outbound",
        body=draft_text,
        sender_name="HostFlow IA (Auto)",
        delivery_status="sent",
    )
    db.add(entry)
    thread.draft_status = "replied"
    thread.status = "pending"
    thread.last_message_at = now
    thread.updated_at = now
    await db.commit()
    logger.info("auto_send: outbound entry created for thread=%d", thread.id)


# ── List threads (with search) ────────────────────────────────────────────────

@router.get("", response_model=List[ThreadOut])
async def list_threads(
    status: Optional[str] = Query(None),
    context: Optional[str] = Query(None),
    property_id: Optional[int] = Query(None),
    channel_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="Full-text search across subject, guest, context, and message body"),
    limit: int = Query(60, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(MessageThread)
        .options(selectinload(MessageThread.property), selectinload(MessageThread.channel))
        .where(MessageThread.user_id == current_user.id)
    )

    if status:
        query = query.where(MessageThread.status == status)
    if context:
        query = query.where(MessageThread.detected_context == context)
    if property_id:
        query = query.where(MessageThread.property_id == property_id)
    if channel_id:
        query = query.where(MessageThread.channel_id == channel_id)

    # Full-text search using ILIKE (pg_trgm indexes make this fast)
    if q and q.strip():
        term = f"%{q.strip()}%"
        entry_subq = (
            select(MessageEntry.thread_id)
            .where(MessageEntry.body.ilike(term))
            .distinct()
            .scalar_subquery()
        )
        query = query.where(
            or_(
                MessageThread.subject.ilike(term),
                MessageThread.guest_name.ilike(term),
                MessageThread.guest_contact.ilike(term),
                MessageThread.detected_context.ilike(term),
                MessageThread.id.in_(entry_subq),
            )
        )

    query = query.order_by(
        desc(MessageThread.last_message_at.is_(None)),
        desc(MessageThread.last_message_at),
        desc(MessageThread.created_at),
    ).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# ── Create thread (manual) ────────────────────────────────────────────────────

@router.post("", response_model=ThreadDetailOut, status_code=201)
async def create_thread(
    payload: ThreadCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # Auto-match or create guest profile
    profile = await guest_service.find_or_create_profile(
        user_id=current_user.id,
        guest_contact=payload.guest_contact,
        guest_name=payload.guest_name,
        db=db,
    )

    thread = MessageThread(
        user_id=current_user.id,
        property_id=payload.property_id,
        channel_id=payload.channel_id,
        subject=payload.subject or payload.guest_message[:80],
        guest_name=payload.guest_name,
        guest_contact=payload.guest_contact,
        source_type=payload.source_type,
        tags=payload.tags,
        guest_profile_id=profile.id if profile else None,
        last_message_at=now,
        updated_at=now,
    )
    db.add(thread)
    await db.flush()

    entry = MessageEntry(
        thread_id=thread.id,
        direction="inbound",
        body=payload.guest_message,
        sender_name=payload.guest_name,
    )
    db.add(entry)
    await db.commit()

    thread = await _load_thread(thread.id, current_user.id, db)

    # Notify other sessions: new thread created
    await sse_service.publish(current_user.id, "thread_created", _thread_event_data(thread))

    # Draft generation in background (also publishes SSE when done)
    background_tasks.add_task(_bg_draft_and_notify, thread.id, current_user.id)

    return thread


# ── Get thread detail ─────────────────────────────────────────────────────────

@router.get("/{thread_id}", response_model=ThreadDetailOut)
async def get_thread(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _load_thread(thread_id, current_user.id, db)


# ── Update thread metadata / status ──────────────────────────────────────────

@router.patch("/{thread_id}", response_model=ThreadOut)
async def update_thread(
    thread_id: int,
    payload: ThreadUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MessageThread)
        .options(selectinload(MessageThread.property), selectinload(MessageThread.channel))
        .where(MessageThread.id == thread_id, MessageThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    if payload.status and payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {', '.join(VALID_STATUSES)}")

    for field in ("status", "property_id", "guest_name", "guest_contact",
                  "subject", "detected_context", "tags", "draft_status"):
        val = getattr(payload, field)
        if val is not None:
            setattr(thread, field, val)

    thread.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await sse_service.publish(current_user.id, "thread_updated", _thread_event_data(thread))
    return thread


# ── Bulk actions ──────────────────────────────────────────────────────────────

@router.post("/bulk")
async def bulk_action(
    payload: BulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_status = _BULK_STATUS_MAP[payload.action]
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(MessageThread).where(
            MessageThread.id.in_(payload.ids),
            MessageThread.user_id == current_user.id,
        )
    )
    threads = result.scalars().all()

    for thread in threads:
        thread.status = new_status
        thread.updated_at = now

    await db.commit()

    # Publish SSE for each changed thread
    for thread in threads:
        await sse_service.publish(
            current_user.id, "thread_updated",
            {"id": thread.id, "status": new_status, "updated_at": now.isoformat()},
        )

    return {"updated": len(threads), "status": new_status}


# ── Add entry (outbound / note) ───────────────────────────────────────────────

@router.post("/{thread_id}/entries", response_model=EntryOut, status_code=201)
async def add_entry(
    thread_id: int,
    payload: EntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MessageThread)
        .where(MessageThread.id == thread_id, MessageThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    now = datetime.now(timezone.utc)
    entry = MessageEntry(
        thread_id=thread.id,
        direction=payload.direction,
        body=payload.body,
        sender_name=payload.sender_name or current_user.name,
    )
    db.add(entry)

    thread.last_message_at = now
    thread.updated_at = now
    if payload.direction == "outbound":
        thread.draft_status = "replied"
        thread.status = "pending"

    await db.commit()
    await db.refresh(entry)

    # Notify: new entry in thread
    await sse_service.publish(current_user.id, "entry_added", {
        "thread_id": thread_id,
        "entry": {
            "id": entry.id,
            "direction": entry.direction,
            "body": entry.body,
            "sender_name": entry.sender_name,
            "created_at": entry.created_at.isoformat(),
        },
    })
    # Also update thread card in list
    await sse_service.publish(current_user.id, "thread_updated", _thread_event_data(thread))

    return entry


# ── Generate AI draft ─────────────────────────────────────────────────────────

class _DraftRequest(BaseModel):
    template_id: Optional[int] = None   # force a specific template
    skip_template: bool = False          # generate without any template grounding


@router.post("/{thread_id}/draft")
async def generate_draft(
    thread_id: int,
    payload: _DraftRequest = _DraftRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate (or regenerate) an AI draft for the thread.

    - Default: auto-apply template if a high-confidence match exists.
    - template_id: force a specific template as grounding (manual pick).
    - skip_template=true: generate without any template (pure AI).
    """
    thread = await _load_thread(thread_id, current_user.id, db)
    draft_text = await draft_service.generate_draft(
        thread, db,
        force_template_id=payload.template_id,
        skip_template=payload.skip_template,
    )
    if not draft_text:
        raise HTTPException(status_code=502, detail="Erro ao gerar rascunho com IA")

    thread = await _load_thread(thread_id, current_user.id, db)

    await sse_service.publish(current_user.id, "draft_ready", {
        "thread_id": thread_id,
        "draft": draft_text,
        "detected_context": thread.detected_context,
        "applied_template_id": thread.applied_template_id,
        "template_auto_applied": thread.template_auto_applied,
    })

    return {
        "draft": draft_text,
        "detected_context": thread.detected_context,
        "draft_status": thread.draft_status,
        "applied_template_id": thread.applied_template_id,
        "template_auto_applied": thread.template_auto_applied,
    }


# ── Send reply via Gmail ──────────────────────────────────────────────────────

@router.post("/{thread_id}/send", response_model=EntryOut, status_code=201)
async def send_gmail_reply(
    thread_id: int,
    payload: EntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a reply via the Gmail API for Gmail-sourced threads.
    Creates an outbound MessageEntry with sent_via_provider=True.

    For non-Gmail threads, raises 400 — use POST /entries instead.
    """
    thread = await _load_thread(thread_id, current_user.id, db)

    if thread.source_type != "gmail" or not thread.external_thread_id:
        raise HTTPException(
            status_code=400,
            detail="Este endpoint é exclusivo para conversas do Gmail. "
                   "Use POST /inbox/{thread_id}/entries para outros canais.",
        )

    # Load Gmail credentials
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=400, detail="Gmail não conectado. Conecte sua conta em Integrações.")

    # Build Gmail service (auto-refreshes token)
    try:
        service = await gmail_service.get_gmail_service(cred, db)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Erro de autenticação Gmail: {exc}")

    # Find the last inbound message to use as In-Reply-To
    inbound_entries = [
        e for e in sorted(thread.entries, key=lambda x: x.created_at)
        if e.direction == "inbound" and e.external_message_id
    ]
    reply_to_message_id = None
    references_header = None
    to_email = thread.guest_contact or ""

    if inbound_entries:
        last_inbound = inbound_entries[-1]
        reply_to_message_id = last_inbound.raw_payload.get("message_id_header") if last_inbound.raw_payload else None
        references_header = last_inbound.raw_payload.get("references") if last_inbound.raw_payload else None
        if not to_email and last_inbound.raw_payload:
            to_email = last_inbound.raw_payload.get("from", "")

    if not to_email:
        raise HTTPException(status_code=400, detail="Endereço de destino do hóspede não encontrado.")

    # Send via Gmail API
    now = datetime.now(timezone.utc)
    delivery_status = "sent"
    sent_message_id: str | None = None

    try:
        sent = await gmail_service.send_reply(
            service=service,
            to=to_email,
            subject=thread.subject or "Re: (sem assunto)",
            body=payload.body,
            gmail_thread_id=thread.external_thread_id,
            reply_to_message_id=reply_to_message_id,
            references=references_header,
        )
        sent_message_id = sent.get("id")
    except Exception as exc:
        delivery_status = "failed"
        logger.error("Gmail send failed for thread %s: %s", thread_id, exc)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar pelo Gmail: {exc}")

    # Create outbound entry
    entry = MessageEntry(
        thread_id=thread.id,
        direction="outbound",
        body=payload.body,
        sender_name=payload.sender_name or current_user.name,
        external_message_id=sent_message_id,
        sent_via_provider=True,
        delivery_status=delivery_status,
    )
    db.add(entry)

    thread.last_message_at = now
    thread.updated_at = now
    thread.draft_status = "replied"
    thread.status = "pending"

    await db.commit()
    await db.refresh(entry)

    # SSE notifications
    await sse_service.publish(current_user.id, "entry_added", {
        "thread_id": thread_id,
        "entry": {
            "id": entry.id,
            "direction": entry.direction,
            "body": entry.body,
            "sender_name": entry.sender_name,
            "sent_via_provider": entry.sent_via_provider,
            "delivery_status": entry.delivery_status,
            "created_at": entry.created_at.isoformat(),
        },
    })
    await sse_service.publish(current_user.id, "thread_updated", _thread_event_data(thread))

    return entry


# ── Delete thread ─────────────────────────────────────────────────────────────

@router.delete("/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MessageThread)
        .where(MessageThread.id == thread_id, MessageThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    await db.delete(thread)
    await db.commit()
