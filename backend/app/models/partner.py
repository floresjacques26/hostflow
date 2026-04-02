from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
from app.core.database import Base


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # commission — informational, not auto-applied
    commission_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)   # pct | flat
    commission_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)     # cents or pct×100

    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
