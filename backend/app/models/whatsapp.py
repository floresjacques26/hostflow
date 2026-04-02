from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class WhatsAppCredential(Base):
    """
    Stores configuration for a user's connected WhatsApp Business account.
    One row per user (UNIQUE on user_id).
    Access tokens are stored encrypted at rest via Fernet (same key as Gmail).

    Provider abstraction:
      - provider='meta'     → Meta WhatsApp Business Cloud API
      - provider='360dialog' → future 360dialog gateway support
    """
    __tablename__ = "whatsapp_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    # Links to the user's WhatsApp channel record in the channels table
    channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
    )

    # Provider: meta | 360dialog
    provider: Mapped[str] = mapped_column(String(30), default="meta", nullable=False)

    # Phone number in E.164, e.g. +5511999990000 (display + matching)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=False)

    # Meta Graph API identifiers
    phone_number_id: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    business_account_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    # Fernet-encrypted permanent access token (Meta System User token)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)

    # Per-user webhook challenge secret — stored and matched during GET /webhook
    webhook_verify_token: Mapped[str] = mapped_column(String(100), nullable=False)

    # connected | disconnected | error | pending_verification
    status: Mapped[str] = mapped_column(String(30), default="pending_verification", nullable=False)

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
