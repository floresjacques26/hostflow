from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Plan & billing
    plan: Mapped[str] = mapped_column(String(20), default="free")
    subscription_status: Mapped[str] = mapped_column(String(30), default="free")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Onboarding
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0)  # 0=not started, 1,2,3=steps done
    onboarding_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Admin / tracking
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Acquisition / referral
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True, index=True)
    referred_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    partner_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    templates: Mapped[list["Template"]] = relationship(back_populates="user")
    properties: Mapped[list["Property"]] = relationship(back_populates="user")
    usage_counters: Mapped[list["UsageCounter"]] = relationship(back_populates="user")
    events: Mapped[list["UserEvent"]] = relationship(back_populates="user")

    # ── computed helpers ──────────────────────────────────────────────────────

    @property
    def effective_plan(self) -> str:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if self.subscription_status == "trialing":
            if self.trial_ends_at and self.trial_ends_at.replace(tzinfo=timezone.utc) > now:
                return self.plan
            return "free"
        if self.subscription_status in ("active", "past_due"):
            return self.plan
        return "free"

    @property
    def is_trial_active(self) -> bool:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        return (
            self.subscription_status == "trialing"
            and self.trial_ends_at is not None
            and self.trial_ends_at.replace(tzinfo=timezone.utc) > now
        )

    @property
    def trial_days_remaining(self) -> int:
        from datetime import timezone
        if not self.is_trial_active or not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
        return max(0, delta.days)
