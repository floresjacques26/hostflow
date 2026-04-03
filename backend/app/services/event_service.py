"""
Lightweight event tracking service.
Fire-and-forget style — never block user-facing operations.
"""
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event import UserEvent
from app.models.user import User

logger = logging.getLogger(__name__)

# Canonical event names — use these constants everywhere
SIGNUP = "signup"
ONBOARDING_STARTED = "onboarding_started"
ONBOARDING_COMPLETED = "onboarding_completed"
ONBOARDING_SKIPPED = "onboarding_skipped"
CREATED_PROPERTY = "created_property"
GENERATED_RESPONSE = "generated_response"
USED_CALCULATOR = "used_calculator"
CREATED_TEMPLATE = "created_template"
STARTED_TRIAL = "started_trial"
UPGRADED_PLAN = "upgraded_plan"
OPENED_BILLING = "opened_billing"
LOGIN = "login"
HIT_USAGE_LIMIT = "hit_usage_limit"


async def track(
    user: User,
    event_name: str,
    db: AsyncSession,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Append an event to the log. Never raises — errors are logged only.
    """
    try:
        event = UserEvent(
            user_id=user.id,
            event_name=event_name,
            event_data=metadata,
        )
        db.add(event)
        # We do NOT commit here — caller owns the transaction boundary
    except Exception as exc:
        logger.warning("track_event failed: event=%s user=%s error=%s", event_name, user.id, exc)
