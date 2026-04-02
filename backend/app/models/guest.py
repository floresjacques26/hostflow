from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class GuestProfile(Base):
    __tablename__ = "guest_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    primary_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    primary_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    threads: Mapped[list["MessageThread"]] = relationship(
        "MessageThread",
        back_populates="guest_profile",
        foreign_keys="[MessageThread.guest_profile_id]",
    )
