"""
Media ingestion service.

Responsibilities:
  - Download media binaries from WhatsApp (Meta Graph API)
  - Detect MIME type and map to extension
  - Upload to storage provider
  - Create / update MediaAttachment records
  - Idempotent: skips if external_media_id already processed

Flow (called in background after webhook entry creation):
  1. Receive InboundWAMessage with media_id + message_type
  2. GET /media/{media_id} → media URL + mime_type
  3. Download binary via media URL
  4. Generate storage key
  5. Upload to storage
  6. Update MediaAttachment → status='ready'

Error isolation: failures are logged and status='error' — they never bubble up
to break webhook processing.
"""
import logging
import mimetypes
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaAttachment
from app.models.thread import MessageEntry
from app.services.storage_service import get_storage, make_media_key

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com"

# Map WhatsApp message_type → storage folder prefix
MEDIA_TYPE_FOLDER = {
    "image":    "images",
    "audio":    "audio",
    "document": "documents",
    "video":    "video",
    "sticker":  "stickers",
}

# Fallback extensions when mime_type is unavailable
MEDIA_TYPE_DEFAULT_EXT = {
    "image":    "jpg",
    "audio":    "ogg",
    "document": "bin",
    "video":    "mp4",
    "sticker":  "webp",
}


# ── Meta Graph API helpers ────────────────────────────────────────────────────

async def _fetch_media_metadata(media_id: str, access_token: str, api_version: str) -> dict:
    """
    GET /media/{media_id} → {url, mime_type, file_size, sha256, messaging_product}
    """
    url = f"{META_API_BASE}/{api_version}/{media_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.json()


async def _download_media_binary(media_url: str, access_token: str) -> bytes:
    """Download media binary from the CDN URL returned by the metadata endpoint."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(media_url, headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.content


# ── Extension resolution ──────────────────────────────────────────────────────

def _ext_from_mime(mime_type: str | None, media_type: str) -> str:
    if mime_type:
        ext = mimetypes.guess_extension(mime_type.split(";")[0].strip())
        if ext:
            return ext.lstrip(".")
    return MEDIA_TYPE_DEFAULT_EXT.get(media_type, "bin")


# ── Public API ────────────────────────────────────────────────────────────────

async def process_wa_media(
    entry_id: int,
    media_id: str,
    media_type: str,
    file_name: str | None,
    access_token: str,
    api_version: str,
    db: AsyncSession,
) -> MediaAttachment | None:
    """
    Download WhatsApp media and store it.
    Returns the MediaAttachment on success, None on failure.
    Idempotent: returns existing record if already processed.
    """
    # ── Idempotency check ─────────────────────────────────────────────────────
    existing = await db.execute(
        select(MediaAttachment).where(
            MediaAttachment.external_media_id == media_id
        )
    )
    att = existing.scalar_one_or_none()
    if att and att.status == "ready":
        logger.debug("media_service: already processed media_id=%s, skipping", media_id)
        return att

    # Create or reuse the attachment record
    if att is None:
        att = MediaAttachment(
            entry_id=entry_id,
            provider="whatsapp",
            media_type=media_type,
            file_name=file_name,
            external_media_id=media_id,
            status="download_pending",
        )
        db.add(att)
        await db.flush()  # get att.id

    try:
        # ── Step 1: fetch metadata ────────────────────────────────────────────
        meta = await _fetch_media_metadata(media_id, access_token, api_version)
        media_url = meta.get("url")
        mime_type = meta.get("mime_type")
        file_size = meta.get("file_size")

        att.mime_type = mime_type
        att.file_size = file_size
        att.status = "downloaded"

        if not media_url:
            raise ValueError("Meta returned no media URL")

        # ── Step 2: download binary ───────────────────────────────────────────
        data = await _download_media_binary(media_url, access_token)
        att.file_size = len(data)

        # ── Step 3: generate storage key and upload ───────────────────────────
        ext = _ext_from_mime(mime_type, media_type)
        storage_key = make_media_key(MEDIA_TYPE_FOLDER.get(media_type, "other"), ext)

        storage = get_storage()
        await storage.upload(data=data, key=storage_key, content_type=mime_type or "application/octet-stream")

        att.storage_key = storage_key
        att.status = "ready"
        await db.commit()

        logger.info(
            "media_service: processed media_id=%s type=%s size=%d key=%s",
            media_id, media_type, len(data), storage_key,
        )
        return att

    except Exception as exc:
        logger.error("media_service: failed to process media_id=%s: %s", media_id, exc)
        att.status = "error"
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return att


async def get_attachment_url(att: MediaAttachment) -> str | None:
    """Resolve a usable URL for a MediaAttachment."""
    if not att.storage_key:
        return att.public_url  # may be None
    if att.public_url:
        return att.public_url
    storage = get_storage()
    return await storage.get_url(att.storage_key)
