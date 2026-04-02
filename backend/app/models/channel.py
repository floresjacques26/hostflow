from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)

    # type: manual | email_forward | gmail | whatsapp | webhook
    type: Mapped[str] = mapped_column(String(30), default="manual")
    name: Mapped[str] = mapped_column(String(120))
    external_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # email addr, phone, etc.

    # status: active | inactive | error
    status: Mapped[str] = mapped_column(String(20), default="active")

    # provider-specific config stored as JSON
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    property: Mapped[Optional["Property"]] = relationship("Property", foreign_keys=[property_id])
    threads: Mapped[list["MessageThread"]] = relationship(back_populates="channel")
