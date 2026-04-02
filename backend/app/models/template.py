from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=True
    )
    # None = global user template; set = scoped to a specific property
    property_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Smart-match fields ───────────────────────────────────────────────────
    # context_key: one of CONTEXT_TYPES (early_checkin, pets, etc.) or None = generic
    context_key: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    # channel_type: gmail | email_forward | manual | whatsapp | webhook | None = any
    channel_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # language: pt | en | es | None = any
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # tone: friendly | formal | brief | None = default
    tone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # priority: higher value wins ties; user-controlled
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # auto_apply: use this template automatically when context matches (no user action needed)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # active: soft-disable without deleting
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="templates")
    property: Mapped[Optional["Property"]] = relationship(back_populates="templates")
