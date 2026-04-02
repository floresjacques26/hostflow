from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class MediaAttachment(Base):
    """
    Stores metadata for a media file attached to a MessageEntry.

    The actual binary is stored externally (local disk or S3/R2).
    storage_key is the object key; public_url is set for CDN-served files,
    otherwise a signed URL is generated on demand.

    Lifecycle:
      1. Row created with status='download_pending' when webhook arrives
      2. Background task downloads binary from provider (Meta Graph API etc.)
      3. Binary uploaded to storage → storage_key set → status='ready'
      4. On error → status='error'
    """
    __tablename__ = "media_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("message_entries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # whatsapp | gmail | upload
    provider: Mapped[str] = mapped_column(String(30), default="whatsapp", nullable=False)

    # image | audio | document | video | sticker | unknown
    media_type: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)

    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Provider media ID (Meta wamid for media, etc.)
    external_media_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)

    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Storage object key — e.g. "media/2024/01/{uuid}.jpg"
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Non-null = permanent CDN URL; null = generate signed URL on demand
    public_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Future AI enrichment hooks
    transcript_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # download_pending | downloaded | ready | error | upload_failed
    status: Mapped[str] = mapped_column(String(20), default="download_pending", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    entry: Mapped["MessageEntry"] = relationship("MessageEntry", back_populates="attachments")
