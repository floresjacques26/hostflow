"""
WhatsApp Business integration management routes.

Endpoints:
  POST   /whatsapp/connect        — save credentials (manual/admin-assisted onboarding)
  GET    /whatsapp/status         — current connection status
  POST   /whatsapp/test           — send a test message to verify connectivity
  DELETE /whatsapp/disconnect     — deactivate + clear credential
  POST   /inbox/{thread_id}/send-whatsapp — send a reply from a thread (in inbox.py)

WhatsApp Business Cloud API requires:
  - A verified Meta Business account with a WABA
  - A permanent System User token (not OAuth — user pastes it)
  - Phone number ID from the Meta App Dashboard

Onboarding in v1 is admin/manual: the user pastes their token and phone_number_id.
A self-serve OAuth-style embedded signup flow can be added in v2 with Meta's
Embedded Signup product.
"""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.channel import Channel
from app.models.media import MediaAttachment
from app.models.thread import MessageThread, MessageEntry
from app.models.user import User
from app.models.wa_template import WhatsAppMessageTemplate
from app.models.whatsapp import WhatsAppCredential
from app.services import whatsapp_service, sse_service
from app.services import media_service, wa_template_service
from app.services.whatsapp_service import encrypt_wa_token, decrypt_wa_token
from app.services.onboarding_service import advance_onboarding

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class WAConnectRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 phone number, e.g. +5511999990000")
    phone_number_id: str = Field(..., description="Meta phone_number_id from App Dashboard")
    access_token: str = Field(..., description="Permanent System User access token")
    business_account_id: str | None = Field(None, description="Optional WABA ID")
    provider: str = Field("meta", description="meta | 360dialog")


class WASendRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4096)
    sender_name: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _ensure_whatsapp_channel(
    user_id: int, phone_number: str, db: AsyncSession
) -> Channel:
    """Find or create the user's WhatsApp channel row."""
    result = await db.execute(
        select(Channel).where(
            Channel.user_id == user_id,
            Channel.type == "whatsapp",
        )
    )
    channel = result.scalar_one_or_none()
    if channel:
        channel.external_id = phone_number
        channel.status = "active"
        channel.name = f"WhatsApp · {phone_number}"
        return channel

    channel = Channel(
        user_id=user_id,
        type="whatsapp",
        name=f"WhatsApp · {phone_number}",
        external_id=phone_number,
        status="active",
    )
    db.add(channel)
    return channel


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/connect", status_code=201)
async def whatsapp_connect(
    payload: WAConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save WhatsApp credentials for the current user.
    Creates or updates the credential + channel row.
    Returns the webhook_verify_token the user must configure in the Meta App Dashboard.
    """
    # Check if phone_number_id is already taken by another user
    existing_pid = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.phone_number_id == payload.phone_number_id,
            WhatsAppCredential.user_id != current_user.id,
        )
    )
    if existing_pid.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Este phone_number_id já está conectado a outra conta HostFlow.",
        )

    now = datetime.now(timezone.utc)
    encrypted = encrypt_wa_token(payload.access_token)

    # Find existing credential (upsert)
    result = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.user_id == current_user.id
        )
    )
    cred = result.scalar_one_or_none()

    if cred is None:
        verify_token = secrets.token_urlsafe(32)
        cred = WhatsAppCredential(
            user_id=current_user.id,
            provider=payload.provider,
            phone_number=payload.phone_number,
            phone_number_id=payload.phone_number_id,
            business_account_id=payload.business_account_id,
            encrypted_access_token=encrypted,
            webhook_verify_token=verify_token,
            status="pending_verification",
            created_at=now,
            updated_at=now,
        )
        db.add(cred)
    else:
        cred.provider = payload.provider
        cred.phone_number = payload.phone_number
        cred.phone_number_id = payload.phone_number_id
        cred.business_account_id = payload.business_account_id
        cred.encrypted_access_token = encrypted
        cred.status = "pending_verification"
        cred.last_error = None
        cred.updated_at = now

    await db.flush()

    # Ensure channel exists
    channel = await _ensure_whatsapp_channel(current_user.id, payload.phone_number, db)
    await db.flush()
    cred.channel_id = channel.id

    await advance_onboarding(current_user, "integration", db)
    await db.commit()
    await db.refresh(cred)

    logger.info(
        "WhatsApp credentials saved for user %d (%s)", current_user.id, payload.phone_number
    )

    return {
        "connected": True,
        "status": cred.status,
        "phone_number": cred.phone_number,
        "phone_number_id": cred.phone_number_id,
        "channel_id": cred.channel_id,
        "webhook_verify_token": cred.webhook_verify_token,
        "webhook_url": f"{settings.app_url.rstrip('/')}/whatsapp/webhook",
        "instructions": (
            "Configure o webhook no Meta App Dashboard:\n"
            f"  URL do webhook: {settings.app_url.rstrip('/')}/whatsapp/webhook\n"
            f"  Token de verificação: {cred.webhook_verify_token}\n"
            "Selecione o campo 'messages' para assinar."
        ),
    }


@router.get("/status")
async def whatsapp_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current WhatsApp connection status for the authenticated user."""
    result = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.user_id == current_user.id
        )
    )
    cred = result.scalar_one_or_none()

    if cred is None:
        return {"connected": False}

    ch_result = await db.execute(
        select(Channel).where(Channel.id == cred.channel_id)
    ) if cred.channel_id else None
    channel = ch_result.scalar_one_or_none() if ch_result else None

    return {
        "connected": cred.status == "connected",
        "status": cred.status,
        "phone_number": cred.phone_number,
        "phone_number_id": cred.phone_number_id,
        "provider": cred.provider,
        "last_sync_at": cred.last_sync_at.isoformat() if cred.last_sync_at else None,
        "last_error": cred.last_error,
        "channel_id": cred.channel_id,
        "channel_status": channel.status if channel else None,
        "webhook_verify_token": cred.webhook_verify_token,
        "webhook_url": f"{settings.app_url.rstrip('/')}/whatsapp/webhook",
    }


@router.post("/test")
async def whatsapp_test(
    payload: WASendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a test message to the user's own phone number to verify connectivity.
    Uses the credential's phone_number as destination.
    """
    result = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.user_id == current_user.id
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="WhatsApp não configurado")

    try:
        access_token = decrypt_wa_token(cred.encrypted_access_token)
        response = await whatsapp_service.send_text_message(
            phone_number_id=cred.phone_number_id,
            access_token=access_token,
            to_phone=cred.phone_number,
            body=payload.body or "✅ HostFlow WhatsApp conectado com sucesso!",
            provider=cred.provider,
        )
        wamid = response.get("messages", [{}])[0].get("id", "")

        # Mark as connected if test succeeds
        if cred.status != "connected":
            cred.status = "connected"
            cred.last_error = None
            await db.commit()

        return {"ok": True, "wamid": wamid, "to": cred.phone_number}

    except Exception as exc:
        cred.status = "error"
        cred.last_error = str(exc)[:500]
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Falha no teste WhatsApp: {exc}")


@router.delete("/disconnect", status_code=204)
async def whatsapp_disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove WhatsApp credential and mark the channel as inactive.
    Existing threads are preserved (historical record).
    """
    result = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.user_id == current_user.id
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="WhatsApp não conectado")

    # Deactivate channel
    if cred.channel_id:
        ch_result = await db.execute(select(Channel).where(Channel.id == cred.channel_id))
        channel = ch_result.scalar_one_or_none()
        if channel:
            channel.status = "inactive"

    await db.delete(cred)
    await db.commit()
    logger.info("WhatsApp disconnected for user %d", current_user.id)


# ── Send reply from inbox thread ──────────────────────────────────────────────

@router.post("/inbox/{thread_id}/send", status_code=201)
async def send_whatsapp_reply(
    thread_id: int,
    payload: WASendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a WhatsApp reply from a thread in the HostFlow inbox.
    Validates the thread is a WhatsApp thread, loads the credential,
    sends via the provider, and creates an outbound MessageEntry.
    """
    from sqlalchemy.orm import selectinload

    # Load thread with entries
    result = await db.execute(
        select(MessageThread)
        .options(selectinload(MessageThread.entries))
        .where(MessageThread.id == thread_id, MessageThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    if thread.source_type != "whatsapp":
        raise HTTPException(
            status_code=400,
            detail="Este endpoint é exclusivo para conversas do WhatsApp. "
                   "Use POST /inbox/{thread_id}/entries para outros canais.",
        )

    if not thread.guest_contact:
        raise HTTPException(
            status_code=400,
            detail="Número de destino do hóspede não encontrado na conversa.",
        )

    # Load credential
    cred_result = await db.execute(
        select(WhatsAppCredential).where(
            WhatsAppCredential.user_id == current_user.id
        )
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(
            status_code=400,
            detail="WhatsApp não conectado. Configure em Integrações.",
        )

    if cred.status not in ("connected", "pending_verification"):
        raise HTTPException(
            status_code=400,
            detail=f"WhatsApp com status '{cred.status}'. Verifique a configuração.",
        )

    # Send via provider
    now = datetime.now(timezone.utc)
    delivery_status = "sent"
    wamid: str | None = None

    try:
        access_token = decrypt_wa_token(cred.encrypted_access_token)
        response = await whatsapp_service.send_text_message(
            phone_number_id=cred.phone_number_id,
            access_token=access_token,
            to_phone=thread.guest_contact,
            body=payload.body,
            provider=cred.provider,
        )
        wamid = response.get("messages", [{}])[0].get("id")

        # Mark as connected on first successful send
        if cred.status != "connected":
            cred.status = "connected"
            cred.last_error = None

    except Exception as exc:
        delivery_status = "failed"
        cred.status = "error"
        cred.last_error = str(exc)[:500]
        logger.error("WhatsApp send failed for thread %d: %s", thread_id, exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Falha ao enviar pelo WhatsApp: {exc}")

    # Create outbound entry
    entry = MessageEntry(
        thread_id=thread.id,
        direction="outbound",
        body=payload.body,
        sender_name=payload.sender_name or current_user.name,
        external_message_id=wamid,
        sent_via_provider=True,
        delivery_status=delivery_status,
        raw_payload={"wamid": wamid, "to": thread.guest_contact} if wamid else None,
    )
    db.add(entry)

    thread.last_message_at = now
    thread.updated_at = now
    thread.draft_status = "replied"
    thread.status = "pending"
    cred.last_sync_at = now

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
    await sse_service.publish(current_user.id, "thread_updated", {
        "id": thread.id,
        "status": thread.status,
        "draft_status": thread.draft_status,
        "last_message_at": now.isoformat(),
    })

    return {
        "id": entry.id,
        "direction": entry.direction,
        "body": entry.body,
        "sender_name": entry.sender_name,
        "external_message_id": entry.external_message_id,
        "sent_via_provider": entry.sent_via_provider,
        "delivery_status": entry.delivery_status,
        "created_at": entry.created_at.isoformat(),
    }


# ── WhatsApp message templates ────────────────────────────────────────────────

class WATemplateCreate(BaseModel):
    provider_template_name: str = Field(..., max_length=200)
    language_code: str = Field("pt_BR", max_length=10)
    category: str = Field("UTILITY")
    components_json: list | None = None
    active: bool = True


class WATemplateSendRequest(BaseModel):
    thread_id: int
    template_id: int
    variables: list[str] = Field(default_factory=list)


@router.get("/templates")
async def list_wa_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's WhatsApp message templates."""
    result = await db.execute(
        select(WhatsAppMessageTemplate)
        .where(WhatsAppMessageTemplate.user_id == current_user.id)
        .order_by(WhatsAppMessageTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return [
        {
            "id": t.id,
            "provider_template_name": t.provider_template_name,
            "language_code": t.language_code,
            "category": t.category,
            "components_json": t.components_json,
            "active": t.active,
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.post("/templates", status_code=201)
async def create_wa_template(
    payload: WATemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a WhatsApp message template record."""
    now = datetime.now(timezone.utc)
    t = WhatsAppMessageTemplate(
        user_id=current_user.id,
        provider_template_name=payload.provider_template_name,
        language_code=payload.language_code,
        category=payload.category,
        components_json=payload.components_json,
        active=payload.active,
        created_at=now,
        updated_at=now,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "provider_template_name": t.provider_template_name, "active": t.active}


@router.delete("/templates/{template_id}", status_code=204)
async def delete_wa_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WhatsAppMessageTemplate).where(
            WhatsAppMessageTemplate.id == template_id,
            WhatsAppMessageTemplate.user_id == current_user.id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    await db.delete(t)
    await db.commit()


@router.post("/templates/send", status_code=201)
async def send_wa_template(
    payload: WATemplateSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send an approved WhatsApp template message to the contact in a thread.
    Used when outside the 24-hour service window.
    """
    from sqlalchemy.orm import selectinload

    # Load thread
    thread_result = await db.execute(
        select(MessageThread)
        .options(selectinload(MessageThread.entries))
        .where(MessageThread.id == payload.thread_id, MessageThread.user_id == current_user.id)
    )
    thread = thread_result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    if thread.source_type != "whatsapp":
        raise HTTPException(status_code=400, detail="Templates só disponíveis para conversas WhatsApp")

    if not thread.guest_contact:
        raise HTTPException(status_code=400, detail="Número de destino não encontrado na conversa")

    # Load template
    tpl_result = await db.execute(
        select(WhatsAppMessageTemplate).where(
            WhatsAppMessageTemplate.id == payload.template_id,
            WhatsAppMessageTemplate.user_id == current_user.id,
            WhatsAppMessageTemplate.active == True,  # noqa: E712
        )
    )
    tpl = tpl_result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template não encontrado ou inativo")

    # Load WA credential
    cred_result = await db.execute(
        select(WhatsAppCredential).where(WhatsAppCredential.user_id == current_user.id)
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=400, detail="WhatsApp não configurado")

    now = datetime.now(timezone.utc)
    delivery_status = "sent"
    wamid: str | None = None

    try:
        access_token = decrypt_wa_token(cred.encrypted_access_token)
        response = await wa_template_service.send_template_message(
            phone_number_id=cred.phone_number_id,
            access_token=access_token,
            to_phone=thread.guest_contact,
            template_name=tpl.provider_template_name,
            language_code=tpl.language_code,
            variables=payload.variables,
        )
        wamid = response.get("messages", [{}])[0].get("id")
    except Exception as exc:
        delivery_status = "failed"
        logger.error("WA template send failed for thread %d: %s", payload.thread_id, exc)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar template: {exc}")

    # Build a readable body from template name + variables
    var_display = " · ".join(payload.variables) if payload.variables else ""
    body_text = f"[Template: {tpl.provider_template_name}]"
    if var_display:
        body_text += f"\n{var_display}"

    entry = MessageEntry(
        thread_id=thread.id,
        direction="outbound",
        body=body_text,
        sender_name=current_user.name,
        external_message_id=wamid,
        sent_via_provider=True,
        delivery_status=delivery_status,
        is_template_message=True,
        template_name=tpl.provider_template_name,
        raw_payload={"wamid": wamid, "template": tpl.provider_template_name, "variables": payload.variables},
    )
    db.add(entry)
    thread.last_message_at = now
    thread.updated_at = now
    thread.draft_status = "replied"
    thread.status = "pending"
    await db.commit()
    await db.refresh(entry)

    await sse_service.publish(current_user.id, "entry_added", {
        "thread_id": thread.id,
        "entry": {
            "id": entry.id,
            "direction": entry.direction,
            "body": entry.body,
            "is_template_message": entry.is_template_message,
            "delivery_status": entry.delivery_status,
            "created_at": entry.created_at.isoformat(),
        },
    })
    await sse_service.publish(current_user.id, "thread_updated", {
        "id": thread.id,
        "status": thread.status,
        "draft_status": thread.draft_status,
        "last_message_at": now.isoformat(),
    })

    return {
        "id": entry.id,
        "wamid": wamid,
        "template_name": tpl.provider_template_name,
        "delivery_status": delivery_status,
        "created_at": entry.created_at.isoformat(),
    }


# ── Media URL resolver ────────────────────────────────────────────────────────

@router.get("/media/{attachment_id}/url")
async def get_media_url(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a usable URL for a MediaAttachment.
    For local storage: returns direct URL.
    For S3 without CDN: returns a pre-signed URL valid for 1 hour.
    """
    from sqlalchemy.orm import selectinload

    att_result = await db.execute(
        select(MediaAttachment)
        .options(selectinload(MediaAttachment.entry))
        .where(MediaAttachment.id == attachment_id)
    )
    att = att_result.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment não encontrado")

    # Verify the attachment belongs to this user via thread ownership
    if att.entry and att.entry.thread_id:
        thread_result = await db.execute(
            select(MessageThread).where(
                MessageThread.id == att.entry.thread_id,
                MessageThread.user_id == current_user.id,
            )
        )
        if not thread_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Acesso negado")

    if att.status != "ready":
        return {"url": None, "status": att.status}

    url = await media_service.get_attachment_url(att)
    return {"url": url, "status": att.status, "media_type": att.media_type, "mime_type": att.mime_type}
