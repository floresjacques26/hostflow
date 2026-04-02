from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    # Identification
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(40), default="apartamento")
    # guest_house | quarto_privativo | apartamento | casa | studio | kitnet
    address_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Check-in / check-out
    check_in_time: Mapped[str] = mapped_column(String(5), default="14:00")   # "HH:MM"
    check_out_time: Mapped[str] = mapped_column(String(5), default="11:00")

    # Pricing
    daily_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    half_day_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Policies (stored as short text for flexibility)
    early_checkin_policy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    late_checkout_policy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Amenities / flags
    accepts_pets: Mapped[bool] = mapped_column(Boolean, default=False)
    has_parking: Mapped[bool] = mapped_column(Boolean, default=False)
    parking_policy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # House rules (free text, sent to AI)
    house_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="properties")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="property")
    templates: Mapped[list["Template"]] = relationship(back_populates="property")
