from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)
    channel_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)

    # guest metadata
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    guest_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    guest_contact: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # source_type: manual | email_forward | gmail | whatsapp | webhook
    source_type: Mapped[str] = mapped_column(String(30), default="manual")

    # status: open | pending | resolved | archived
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)

    # AI classification
    detected_context: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)

    # draft workflow: none | draft_generated | awaiting_review | replied
    draft_status: Mapped[str] = mapped_column(String(30), default="none")

    # lightweight tagging (comma-separated)
    tags: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Guest profile link (set automatically on thread creation)
    guest_profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("guest_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )

    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    # Timestamp of the latest INBOUND (customer) message — used for WhatsApp 24h window
    last_inbound_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # ── Template matching ─────────────────────────────────────────────────────
    # Which template grounded the current AI draft (FK → templates.id)
    applied_template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    # True when the template was auto-applied (not manually selected by user)
    template_auto_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Auto-send ─────────────────────────────────────────────────────────────
    # Decision taken by the auto-send engine after draft generation
    # Values: sent | blocked | manual_review | None (not yet evaluated)
    auto_send_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    auto_send_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("auto_send_rules.id", ondelete="SET NULL"), nullable=True
    )

    # ── External provider linkage (Gmail, etc.) ───────────────────────────────
    # external_thread_id: Gmail threadId; unique per user — used for dedup/reply
    external_thread_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # external_source_id: e.g. the channel-level account identifier
    external_source_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # sync_status: none | synced | error
    sync_status: Mapped[str] = mapped_column(String(20), default="none")
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    property: Mapped[Optional["Property"]] = relationship("Property", foreign_keys=[property_id])
    channel: Mapped[Optional["Channel"]] = relationship("Channel", back_populates="threads", foreign_keys=[channel_id])
    guest_profile: Mapped[Optional["GuestProfile"]] = relationship(
        "GuestProfile", back_populates="threads", foreign_keys=[guest_profile_id]
    )
    entries: Mapped[list["MessageEntry"]] = relationship(back_populates="thread", order_by="MessageEntry.created_at")

    # ── SLA computed helpers ──────────────────────────────────────────────────

    @property
    def wa_window_open(self) -> bool:
        """
        WhatsApp 24-hour service window.
        True when the last inbound customer message arrived within the past 24 hours.
        Always True for non-WhatsApp threads (no restriction applies).
        """
        if self.source_type != "whatsapp":
            return True
        if not self.last_inbound_at:
            return False
        from datetime import timezone, timedelta
        ref = self.last_inbound_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - ref <= timedelta(hours=24)

    @property
    def is_overdue(self) -> bool:
        """Open thread with no reply for > 4 hours."""
        from datetime import timezone, timedelta
        if self.status != "open":
            return False
        ref = self.created_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - ref > timedelta(hours=4)

    @property
    def is_stale(self) -> bool:
        """Pending thread with no update for > 24 hours."""
        from datetime import timezone, timedelta
        if self.status != "pending":
            return False
        ref = self.last_message_at or self.updated_at or self.created_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - ref > timedelta(hours=24)


class MessageEntry(Base):
    __tablename__ = "message_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("message_threads.id", ondelete="CASCADE"), index=True)

    # direction: inbound | outbound | ai_draft | note
    direction: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)

    # original raw payload (email JSON, webhook body, etc.)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    sender_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # ── WhatsApp template send tracking ──────────────────────────────────────
    is_template_message: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ── External provider linkage ─────────────────────────────────────────────
    # Gmail messageId — used as In-Reply-To when sending replies
    external_message_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # True when this entry was actually sent via Gmail API (not just recorded)
    sent_via_provider: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # pending | sent | failed | delivered
    delivery_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    thread: Mapped["MessageThread"] = relationship(back_populates="entries")
    attachments: Mapped[list["MediaAttachment"]] = relationship(
        "MediaAttachment", back_populates="entry", cascade="all, delete-orphan"
    )
