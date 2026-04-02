from sqlalchemy import String, Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class UsageCounter(Base):
    """
    Tracks monthly usage per user.
    One row per (user_id, month). month format: 'YYYY-MM'.
    """
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("user_id", "month", name="uq_usage_user_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(7))   # e.g. "2025-04"
    ai_responses: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="usage_counters")
