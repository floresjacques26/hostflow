from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class Testimonial(Base):
    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    rating: Mapped[int] = mapped_column(Integer)           # 1-5
    quote: Mapped[str] = mapped_column(String(500))
    trigger_event: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # onboarding | upgrade | responses_10

    # moderation
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending | approved | rejected
    approved_for_public_use: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
