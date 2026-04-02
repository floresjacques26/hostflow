from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referred_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    referral_code: Mapped[str] = mapped_column(String(20))

    # reward
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending | activated | rewarded
    reward_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)   # trial_days
    reward_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)     # e.g. 7
    rewarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    referrer: Mapped["User"] = relationship("User", foreign_keys=[referrer_user_id])
    referred: Mapped["User"] = relationship("User", foreign_keys=[referred_user_id])
