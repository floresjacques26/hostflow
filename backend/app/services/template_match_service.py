"""
Template matching engine.

Deterministic scoring: selects the best template(s) for a given thread context
without any ML — purely rule-based, fully explainable, easy to tune.

Scoring weights (additive):
  +20  context_key matches thread.detected_context   — strongest signal
  +10  property_id matches thread.property_id        — property-specific wins over generic
  +5   channel_type matches thread.source_type       — channel specificity bonus
  +3   language matches                              — language preference
  +2   tone is set (non-null)                        — indicates the template is tailored
  + template.priority                                — user-controlled tiebreaker (can be negative)

Disqualification (template is never returned):
  - active == False
  - belongs to wrong user (not is_default and user_id != requesting user)

Fallback:
  If no template scores above MINIMUM_MATCH_SCORE (i.e. no context_key match),
  the function still returns generic templates (context_key IS NULL) ranked by
  property → channel → priority.  The caller decides whether to use them.

Usage:
    from app.services.template_match_service import match_templates, TemplateMatch

    matches = await match_templates(thread, user_id, db)
    if matches:
        best = matches[0]
        print(best.template.title, best.score, best.reasons)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template
from app.models.thread import MessageThread

logger = logging.getLogger(__name__)

# Minimum score for a match to be considered "context-specific"
# (i.e. the template was actually matched on context, not just returned as fallback)
MINIMUM_CONTEXT_SCORE = 20

# Score weights — adjust here to tune the engine without touching logic
W_CONTEXT   = 20
W_PROPERTY  = 10
W_CHANNEL   = 5
W_LANGUAGE  = 3
W_TONE      = 2


@dataclass
class TemplateMatch:
    template: Template
    score: int
    reasons: list[str] = field(default_factory=list)
    is_context_specific: bool = False  # True if scored >= MINIMUM_CONTEXT_SCORE

    @property
    def match_label(self) -> str:
        """Human-readable summary of why this template was selected."""
        if not self.reasons:
            return "Genérico"
        return " · ".join(self.reasons)


def _score_template(
    template: Template,
    context_key: Optional[str],
    property_id: Optional[int],
    channel_type: Optional[str],
    language: Optional[str],
) -> tuple[int, list[str]]:
    """
    Return (score, reasons) for a single template against the given thread signals.
    Pure function — no I/O.
    """
    score = 0
    reasons: list[str] = []

    # Context match — most impactful
    if template.context_key and template.context_key == context_key:
        score += W_CONTEXT
        reasons.append(f"Contexto: {template.context_key}")

    # Property match
    if template.property_id and template.property_id == property_id:
        score += W_PROPERTY
        reasons.append("Imóvel específico")

    # Channel match
    if template.channel_type and template.channel_type == channel_type:
        score += W_CHANNEL
        reasons.append(f"Canal: {template.channel_type}")

    # Language match
    if template.language and template.language == language:
        score += W_LANGUAGE
        reasons.append(f"Idioma: {template.language}")

    # Tone is set (template is tailored, not generic)
    if template.tone:
        score += W_TONE
        reasons.append(f"Tom: {template.tone}")

    # User priority boost (can be negative to demote)
    score += template.priority

    return score, reasons


async def match_templates(
    thread: MessageThread,
    user_id: int,
    db: AsyncSession,
    language: Optional[str] = None,
    limit: int = 10,
) -> list[TemplateMatch]:
    """
    Return templates ranked by match score for the given thread.

    The list always starts with context-specific matches (score >= MINIMUM_CONTEXT_SCORE),
    followed by generic fallbacks, all sorted by score descending.

    Parameters
    ----------
    thread      Active MessageThread (must have id, detected_context, property_id, source_type).
    user_id     The requesting user — used to scope template access.
    db          Async SQLAlchemy session.
    language    Optional ISO-639-1 language code (e.g. 'pt', 'en').
    limit       Maximum templates to return.
    """
    # Fetch all eligible templates for this user in one query:
    # system defaults + user's own templates (global + property-scoped)
    result = await db.execute(
        select(Template).where(
            Template.active == True,  # noqa: E712
            or_(
                Template.is_default == True,  # noqa: E712
                and_(
                    Template.user_id == user_id,
                    Template.is_default == False,  # noqa: E712
                ),
            ),
        )
    )
    all_templates = result.scalars().all()

    context_key  = thread.detected_context
    property_id  = thread.property_id
    channel_type = thread.source_type

    scored: list[TemplateMatch] = []
    for t in all_templates:
        score, reasons = _score_template(t, context_key, property_id, channel_type, language)
        is_ctx = score >= MINIMUM_CONTEXT_SCORE
        scored.append(TemplateMatch(
            template=t,
            score=score,
            reasons=reasons,
            is_context_specific=is_ctx,
        ))

    # Sort: context-specific first (highest score first), then generic
    scored.sort(key=lambda m: (-m.score, -m.template.priority, m.template.id))

    return scored[:limit]


async def best_auto_apply(
    thread: MessageThread,
    user_id: int,
    db: AsyncSession,
) -> Optional[TemplateMatch]:
    """
    Return the single best auto-apply template for this thread, or None.
    Only returns a match when:
      - auto_apply=True on the template
      - score >= MINIMUM_CONTEXT_SCORE (a genuine context match exists)
    This ensures auto-apply is never triggered on a generic fallback.
    """
    matches = await match_templates(thread, user_id, db, limit=20)
    for m in matches:
        if m.template.auto_apply and m.is_context_specific:
            logger.debug(
                "Auto-apply: template=%d (%s) for thread=%d context=%s score=%d",
                m.template.id, m.template.title, thread.id,
                thread.detected_context, m.score,
            )
            return m
    return None


async def get_suggestions(
    thread: MessageThread,
    user_id: int,
    db: AsyncSession,
    limit: int = 5,
) -> list[TemplateMatch]:
    """
    Convenience wrapper: return top `limit` matches for the UI suggestion panel.
    Includes context-specific and generic fallbacks together.
    """
    return await match_templates(thread, user_id, db, limit=limit)
