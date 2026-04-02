from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class WhatsAppMessageTemplate(Base):
    """
    A WhatsApp Business approved message template (HSM).

    These are required for proactive outbound messages and for re-engaging
    contacts after the 24-hour customer service window has elapsed.

    Templates are created and approved in Meta Business Manager.
    HostFlow stores them here so users can pick and send without knowing the API.

    components_json follows the Meta API structure:
      [
        {"type": "HEADER", "format": "TEXT", "text": "Olá {{1}}"},
        {"type": "BODY",   "text": "Seu check-in é em {{2}}."},
        {"type": "FOOTER", "text": "HostFlow"}
      ]
    Variables are filled at send time.
    """
    __tablename__ = "wa_message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Exact template name as registered in Meta (lowercase, underscores)
    provider_template_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # BCP 47, e.g. pt_BR, en_US
    language_code: Mapped[str] = mapped_column(String(10), default="pt_BR", nullable=False)

    # AUTHENTICATION | MARKETING | UTILITY
    category: Mapped[str] = mapped_column(String(30), default="UTILITY", nullable=False)

    # Full components array from Meta (or manually authored)
    components_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
