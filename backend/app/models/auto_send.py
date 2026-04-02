from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Numeric, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class AutoSendRule(Base):
    __tablename__ = "auto_send_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Scope filters — NULL means "match any"
    property_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    channel_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    context_key: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Require a specific template to be matched before auto-send (optional)
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )

    # Confidence gate: 0.0–1.0 (default 0.85)
    min_confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.85)

    # Block auto-send when no template was matched
    require_template_match: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Time-window gate in UTC hours (None = any hour)
    allowed_start_hour: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_end_hour: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class AutoSendDecisionLog(Base):
    __tablename__ = "auto_send_decision_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("message_threads.id", ondelete="CASCADE"), index=True
    )
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    matched_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("auto_send_rules.id", ondelete="SET NULL"), nullable=True
    )

    # sent | blocked | manual_review
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    # no_rule | low_confidence | no_template | risky_keyword | blocked_category |
    # message_too_long | complaint_sentiment | outside_time_window | ok
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
