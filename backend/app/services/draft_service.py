"""
Generates AI draft responses for inbox threads.

Flow:
  1. Detect message context (fast, cheap classifier call)
  2. Find best matching template via template_match_service
     - If auto_apply=True and score >= threshold → auto-apply
     - Otherwise → record as suggestion only (frontend can override)
  3. Call ai_service.generate_response with optional template_hint
  4. Save ai_draft MessageEntry + update thread state
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.thread import MessageThread, MessageEntry
from app.models.property import Property
from app.services.ai_service import generate_response
from app.services.context_service import detect_context
from app.services import template_match_service

logger = logging.getLogger(__name__)


async def _get_thread_guest_message(thread: MessageThread) -> str:
    """Return the body of the latest inbound entry in the thread."""
    inbound = [e for e in thread.entries if e.direction == "inbound"]
    if not inbound:
        return ""
    return sorted(inbound, key=lambda e: e.created_at)[-1].body


async def generate_draft(
    thread: MessageThread,
    db: AsyncSession,
    force_template_id: Optional[int] = None,
    skip_template: bool = False,
) -> str:
    """
    Detect context → match template → generate AI draft → save entry.
    Returns the draft text. Never raises — on failure returns empty string.

    Parameters
    ----------
    force_template_id
        When set, use this specific template as grounding (user manually chose it).
        Overrides auto_apply logic.
    skip_template
        When True, generate without any template (pure AI, no grounding).
    """
    try:
        guest_message = await _get_thread_guest_message(thread)
        if not guest_message:
            return ""

        # ── Step 1: Context detection ────────────────────────────────────────
        if not thread.detected_context:
            context = await detect_context(guest_message)
            thread.detected_context = context

        # ── Step 2: Load property ─────────────────────────────────────────────
        prop = None
        if thread.property_id:
            result = await db.execute(select(Property).where(Property.id == thread.property_id))
            prop = result.scalar_one_or_none()

        # ── Step 3: Template matching ─────────────────────────────────────────
        applied_template = None
        template_auto_applied = False
        template_hint: str | None = None

        if not skip_template and thread.user_id:
            if force_template_id is not None:
                # User explicitly selected a template — fetch it directly
                from app.models.template import Template
                t_result = await db.execute(
                    select(Template).where(Template.id == force_template_id, Template.active == True)  # noqa: E712
                )
                t = t_result.scalar_one_or_none()
                if t:
                    applied_template = t
                    template_hint = t.content
                    template_auto_applied = False
                    logger.debug(
                        "Draft: manual template=%d (%s) for thread=%d",
                        t.id, t.title, thread.id,
                    )
            else:
                # Auto-apply: check for a high-confidence context match
                auto_match = await template_match_service.best_auto_apply(
                    thread, thread.user_id, db
                )
                if auto_match:
                    applied_template = auto_match.template
                    template_hint = auto_match.template.content
                    template_auto_applied = True
                    logger.info(
                        "Draft: auto-applied template=%d (%s) for thread=%d context=%s score=%d",
                        auto_match.template.id, auto_match.template.title,
                        thread.id, thread.detected_context, auto_match.score,
                    )

        # ── Step 4: Generate AI draft ─────────────────────────────────────────
        ai_response, detected = await generate_response(
            guest_message=guest_message,
            property=prop,
            template_hint=template_hint,
        )

        # Update context if not yet set or still generic
        if not thread.detected_context or thread.detected_context == "general":
            _map = {
                "checkin": "checkin", "checkout": "checkout",
                "complaint": "complaint", "charge": "charge",
                "question": "question", "other": "general",
            }
            thread.detected_context = _map.get(detected, thread.detected_context or "general")

        # ── Step 5: Save draft entry ──────────────────────────────────────────
        entry = MessageEntry(
            thread_id=thread.id,
            direction="ai_draft",
            body=ai_response,
            sender_name="HostFlow IA",
        )
        db.add(entry)

        # ── Step 6: Update thread state ───────────────────────────────────────
        now = datetime.utcnow()
        thread.draft_status = "draft_generated"
        thread.last_message_at = now
        thread.updated_at = now

        if applied_template is not None:
            thread.applied_template_id = applied_template.id
            thread.template_auto_applied = template_auto_applied
        elif skip_template:
            # User asked to regenerate without template — clear previous
            thread.applied_template_id = None
            thread.template_auto_applied = False

        await db.commit()
        return ai_response

    except Exception as exc:
        logger.warning("draft_service.generate_draft failed for thread=%s: %s", thread.id, exc)
        await db.rollback()
        return ""
