"""
WhatsApp Business Cloud API service layer.

Responsibilities:
  - Token encryption / decryption (reuses gmail_service Fernet key)
  - Send text messages via Meta Graph API
  - Parse inbound webhook payload into clean dataclasses
  - Webhook signature verification (X-Hub-Signature-256)
  - Provider abstraction (meta first; 360dialog extensible via provider param)

Dependencies (add to requirements.txt):
    httpx>=0.27.0
    cryptography>=42.0.0   (already present)
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.core.config import settings
from app.services.gmail_service import encrypt_token, decrypt_token  # reuse Fernet helpers

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com"


# ── Token helpers (delegates to Fernet from gmail_service) ────────────────────

def encrypt_wa_token(plain: str) -> str:
    return encrypt_token(plain)


def decrypt_wa_token(cipher: str) -> str:
    return decrypt_token(cipher)


# ── Webhook signature verification ────────────────────────────────────────────

def verify_webhook_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """
    Validate X-Hub-Signature-256 header.
    Returns True if signature matches or if app_secret is not configured
    (to allow easier local development without secrets).
    """
    if not settings.whatsapp_app_secret:
        logger.warning("whatsapp_app_secret not set — skipping signature verification")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        key=settings.whatsapp_app_secret.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


# ── Parsed inbound message ────────────────────────────────────────────────────

@dataclass
class InboundWAMessage:
    """Normalized representation of one WhatsApp inbound message."""
    wa_message_id: str          # WhatsApp message ID (wamid.xxx)
    phone_number_id: str        # receiving phone_number_id (routes to a credential)
    from_phone: str             # sender's E.164 phone number
    display_name: str           # sender's display name (may be empty)
    body: str                   # text content (or placeholder for media)
    timestamp: int              # Unix epoch from WhatsApp
    message_type: str = "text"  # text | image | audio | document | video | sticker
    media_id: Optional[str] = None   # Meta media object ID for download
    file_name: Optional[str] = None  # original filename (documents only)
    raw: dict = field(default_factory=dict)


@dataclass
class WAStatusUpdate:
    """A delivery/read status update for an outbound message."""
    wa_message_id: str          # wamid of the outbound message
    phone_number_id: str
    recipient_phone: str
    status: str                 # sent | delivered | read | failed
    error_code: Optional[int] = None
    error_title: Optional[str] = None


# ── Webhook payload parser ────────────────────────────────────────────────────

def parse_webhook(payload: dict) -> tuple[list[InboundWAMessage], list[WAStatusUpdate]]:
    """
    Parse a Meta WhatsApp Cloud API webhook payload.
    Returns (messages, status_updates).
    Only 'text' messages are parsed in v1; other types create a placeholder.
    """
    messages: list[InboundWAMessage] = []
    statuses: list[WAStatusUpdate] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")

            # ── Inbound messages ──────────────────────────────────────────────
            for msg in value.get("messages", []):
                msg_type = msg.get("type", "unknown")
                wa_id = msg.get("id", "")
                from_phone = msg.get("from", "")
                timestamp = int(msg.get("timestamp", 0))

                # Try to resolve display name from contacts list
                display_name = ""
                for contact in value.get("contacts", []):
                    if contact.get("wa_id") == from_phone:
                        display_name = contact.get("profile", {}).get("name", "")
                        break

                media_id: Optional[str] = None
                file_name: Optional[str] = None

                if msg_type == "text":
                    body = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    body = "[Imagem recebida via WhatsApp]"
                    media_id = msg.get("image", {}).get("id")
                elif msg_type == "audio":
                    body = "[Áudio recebido via WhatsApp]"
                    media_id = msg.get("audio", {}).get("id")
                elif msg_type == "document":
                    doc = msg.get("document", {})
                    file_name = doc.get("filename", "documento")
                    body = f"[Documento: {file_name}]"
                    media_id = doc.get("id")
                elif msg_type == "video":
                    body = "[Vídeo recebido via WhatsApp]"
                    media_id = msg.get("video", {}).get("id")
                elif msg_type == "sticker":
                    body = "[Sticker recebido]"
                    media_id = msg.get("sticker", {}).get("id")
                else:
                    body = f"[Mensagem tipo '{msg_type}' recebida]"

                messages.append(InboundWAMessage(
                    wa_message_id=wa_id,
                    phone_number_id=phone_number_id,
                    from_phone=from_phone,
                    display_name=display_name,
                    body=body,
                    timestamp=timestamp,
                    message_type=msg_type,
                    media_id=media_id,
                    file_name=file_name,
                    raw=msg,
                ))

            # ── Delivery/read statuses ────────────────────────────────────────
            for st in value.get("statuses", []):
                err = st.get("errors", [{}])[0] if st.get("errors") else {}
                statuses.append(WAStatusUpdate(
                    wa_message_id=st.get("id", ""),
                    phone_number_id=phone_number_id,
                    recipient_phone=st.get("recipient_id", ""),
                    status=st.get("status", "unknown"),
                    error_code=err.get("code"),
                    error_title=err.get("title"),
                ))

    return messages, statuses


# ── Outbound send ─────────────────────────────────────────────────────────────

async def send_text_message(
    phone_number_id: str,
    access_token: str,
    to_phone: str,
    body: str,
    provider: str = "meta",
    api_version: str | None = None,
) -> dict:
    """
    Send a text message via the WhatsApp Business Cloud API.
    Returns the raw API response dict with 'messages[0].id' on success.

    Parameters
    ----------
    phone_number_id
        Meta phone_number_id for the sending account.
    access_token
        Decrypted permanent access token.
    to_phone
        Recipient's E.164 phone number (without leading +).
    body
        UTF-8 message text (max 4096 chars for WhatsApp).
    provider
        'meta' (future: '360dialog')
    api_version
        Meta Graph API version string, e.g. 'v19.0'. Falls back to settings.
    """
    if provider == "meta":
        return await _meta_send_text(phone_number_id, access_token, to_phone, body, api_version)
    raise NotImplementedError(f"WhatsApp provider '{provider}' not implemented")


async def _meta_send_text(
    phone_number_id: str,
    access_token: str,
    to_phone: str,
    body: str,
    api_version: str | None,
) -> dict:
    version = api_version or settings.whatsapp_api_version
    url = f"{META_API_BASE}/{version}/{phone_number_id}/messages"

    # Normalize: strip leading + (Meta expects without)
    normalized = to_phone.lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalized,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if resp.status_code not in (200, 201):
        logger.error(
            "WhatsApp send failed: status=%d body=%s",
            resp.status_code, resp.text[:500],
        )
        raise RuntimeError(
            f"WhatsApp API error {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    logger.info(
        "WhatsApp sent to=%s via phone_number_id=%s → wamid=%s",
        normalized, phone_number_id,
        data.get("messages", [{}])[0].get("id", "?"),
    )
    return data
