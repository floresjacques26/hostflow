from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
from app.core.database import Base


class EmailLog(Base):
    """
    Append-only log of all outbound lifecycle emails.
    Used for dedup, debugging, and lifecycle analytics.
    """
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    email_type: Mapped[str] = mapped_column(String(80), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(40), default="logging")
    status: Mapped[str] = mapped_column(String(20), default="sent")   # sent | failed | skipped
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
