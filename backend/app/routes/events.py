"""
Conversion event tracking endpoint.

POST /events/track  — fire-and-forget, auth optional.

Anonymous callers (public pricing page, pre-login): event is logged to
structured logs only. Authenticated callers: event is also persisted to
user_events table so admin analytics can surface funnel data.

Design goals:
  - Never block or error out — tracking must be invisible to the user.
  - Minimal payload: name + optional JSON properties.
  - Works both logged-in and logged-out (pricing page fires events before signup).
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_optional
from app.models.event import UserEvent

router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger("hostflow.events")

# Allowlist of accepted event names.
# Reject anything outside this set to prevent event log pollution.
_ALLOWED_EVENTS = {
    "viewed_pricing_page",
    "clicked_plan_cta",
    "started_checkout",
    "checkout_completed",
    "checkout_canceled",
    "viewed_success_page",
    "upgraded_in_app",
    "started_trial",
    "clicked_comparison",
    # Re-export existing app events that the frontend may also want to track
    "opened_billing",
    "hit_usage_limit",
}


class TrackEventRequest(BaseModel):
    name: str
    properties: Optional[dict[str, Any]] = None


@router.post("/track", status_code=204, include_in_schema=False)
async def track_event(
    payload: TrackEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    Track a conversion/funnel event. Auth is optional.

    - Authenticated: persisted to user_events + logged.
    - Anonymous: logged to structured logs only.
    Returns 204 No Content always (errors are swallowed silently).
    """
    try:
        if payload.name not in _ALLOWED_EVENTS:
            # Silently discard unknown events rather than surfacing an error
            return JSONResponse(status_code=204, content=None)

        props = payload.properties or {}

        logger.info(
            "conversion_event: %s",
            payload.name,
            extra={
                "event": payload.name,
                "user_id": current_user.id if current_user else None,
                **{f"prop_{k}": v for k, v in props.items()},
            },
        )

        if current_user is not None:
            db.add(UserEvent(
                user_id=current_user.id,
                event_name=payload.name,
                metadata=props or None,
            ))
            await db.commit()

    except Exception:
        # Tracking must never raise — swallow all errors
        logger.debug("track_event: swallowed error for '%s'", payload.name, exc_info=True)

    return JSONResponse(status_code=204, content=None)
