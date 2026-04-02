"""
Auto-send decision engine with safety guardrails.

Flow (called after draft is generated):
  1. Find matching AutoSendRule for this thread
  2. Run guardrail checks (in order — first failure blocks)
  3. Return AutoSendDecision
  4. Caller writes AutoSendDecisionLog + optionally triggers send
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.thread import MessageThread, MessageEntry
from app.models.auto_send import AutoSendRule, AutoSendDecisionLog

logger = logging.getLogger(__name__)

# ── Safety constants ──────────────────────────────────────────────────────────

# Hard-blocked context categories — never auto-send regardless of rules
BLOCKED_CATEGORIES: set[str] = {
    "pricing_negotiation",
    "billing",
    "payment",
    "complaint",
    "cancellation_conflict",
    "refund",
    "legal",
    "safety",
    "custom_deal",
    "unclear_mixed",
}

# Risky keyword patterns — block if any match the draft body
_RISKY_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"\brefund\b", r"\breembolso\b",
    r"\bcancel(?:lation|ar|amento)\b",
    r"\badvogado\b", r"\blawyer\b", r"\blegal\b",
    r"\bpolícia\b", r"\bpolice\b",
    r"\bprocesso\b", r"\blawsuit\b",
    r"\bnão vou pagar\b", r"\bi won['']t pay\b",
    r"\bdanificad[oa]\b", r"\bdamag(?:ed|e)\b",
    r"\bemergência\b", r"\bemergency\b",
    r"\bnegocia(?:r|ção)\b", r"\bnegotiat\b",
    r"\bcompensação\b", r"\bcompensation\b",
    r"\bdesconto especial\b", r"\bspecial discount\b",
    r"\bpreço diferente\b",
]]

# Complaint / conflict sentiment cues in the guest's message
_COMPLAINT_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"\binsatisfeit[oa]\b", r"\bunsatisfied\b",
    r"\bpessim[oa]\b", r"\bterr[íi]vel\b", r"\bhorr[íi]vel\b",
    r"\bdecepcionad[oa]\b", r"\bdisappoint\b",
    r"\bescândalo\b", r"\boutrage\b",
    r"\bvou reclamar\b", r"\bi['']ll complain\b",
    r"\bavaliaç[aã]o negativa\b", r"\bbad review\b", r"\bnegative review\b",
    r"\bdesgastante\b",
]]

# Maximum safe draft length (characters) — very long replies signal ambiguity
MAX_SAFE_DRAFT_CHARS = 1_200

# Minimum confidence required regardless of rule (absolute floor)
ABSOLUTE_MIN_CONFIDENCE = 0.60


# ── Return types ──────────────────────────────────────────────────────────────

@dataclass
class AutoSendDecision:
    should_auto_send: bool
    # sent | blocked | manual_review
    decision: str
    reason_code: str
    reason_message: str
    matched_rule_id: Optional[int]
    matched_rule: Optional[AutoSendRule]


# ── Rule matching ─────────────────────────────────────────────────────────────

async def _find_matching_rule(
    thread: MessageThread,
    db: AsyncSession,
) -> Optional[AutoSendRule]:
    """
    Return the most-specific active rule matching this thread, or None.

    Specificity: rules with property_id + context_key + channel_type beat
    rules with fewer constraints.  We order by specificity DESC and take the
    first match.
    """
    result = await db.execute(
        select(AutoSendRule)
        .where(
            AutoSendRule.user_id == thread.user_id,
            AutoSendRule.active == True,  # noqa: E712
        )
        .order_by(
            # Prefer rules that have the most specific filters first
            (AutoSendRule.property_id.is_not(None)).desc(),
            (AutoSendRule.context_key.is_not(None)).desc(),
            (AutoSendRule.channel_type.is_not(None)).desc(),
        )
    )
    rules = result.scalars().all()

    channel_type = None
    if thread.channel_id:
        # We'll resolve channel_type from the thread source_type as a proxy
        channel_type = thread.source_type  # e.g. "gmail", "manual"

    for rule in rules:
        # Property filter
        if rule.property_id is not None and rule.property_id != thread.property_id:
            continue
        # Context filter
        if rule.context_key is not None and rule.context_key != thread.detected_context:
            continue
        # Channel-type filter
        if rule.channel_type is not None and rule.channel_type != channel_type:
            continue
        return rule

    return None


# ── Guardrail checks (each returns (passed, reason_code, reason_message)) ────

def _check_blocked_category(thread: MessageThread):
    ctx = (thread.detected_context or "").lower()
    if ctx in BLOCKED_CATEGORIES:
        return False, "blocked_category", f"Context '{ctx}' is in the blocked-category list"
    return True, "ok", ""


def _check_risky_keywords(draft_body: str):
    for pat in _RISKY_PATTERNS:
        m = pat.search(draft_body)
        if m:
            return False, "risky_keyword", f"Draft contains risky keyword pattern: '{m.group()}'"
    return True, "ok", ""


def _check_complaint_sentiment(guest_message: str):
    for pat in _COMPLAINT_PATTERNS:
        m = pat.search(guest_message)
        if m:
            return False, "complaint_sentiment", f"Guest message shows complaint/conflict cue: '{m.group()}'"
    return True, "ok", ""


def _check_draft_length(draft_body: str):
    if len(draft_body) > MAX_SAFE_DRAFT_CHARS:
        return (
            False,
            "message_too_long",
            f"Draft is {len(draft_body)} chars — exceeds safe auto-send limit of {MAX_SAFE_DRAFT_CHARS}",
        )
    return True, "ok", ""


def _check_confidence(confidence: float, min_confidence: float):
    if confidence < ABSOLUTE_MIN_CONFIDENCE:
        return (
            False,
            "low_confidence",
            f"Confidence {confidence:.2f} below absolute floor {ABSOLUTE_MIN_CONFIDENCE}",
        )
    if confidence < min_confidence:
        return (
            False,
            "low_confidence",
            f"Confidence {confidence:.2f} below rule threshold {min_confidence}",
        )
    return True, "ok", ""


def _check_time_window(rule: AutoSendRule):
    if rule.allowed_start_hour is None or rule.allowed_end_hour is None:
        return True, "ok", ""
    now_hour = datetime.now(timezone.utc).hour
    start, end = rule.allowed_start_hour, rule.allowed_end_hour
    if start <= end:
        in_window = start <= now_hour <= end
    else:
        # Wraps midnight
        in_window = now_hour >= start or now_hour <= end
    if not in_window:
        return (
            False,
            "outside_time_window",
            f"Current hour {now_hour}h UTC is outside allowed window {start}h–{end}h",
        )
    return True, "ok", ""


def _check_template_required(rule: AutoSendRule, thread: MessageThread):
    if rule.require_template_match and not thread.applied_template_id:
        return False, "no_template", "Rule requires a template match but none was applied"
    return True, "ok", ""


# ── Public API ────────────────────────────────────────────────────────────────

async def evaluate_auto_send(
    thread: MessageThread,
    db: AsyncSession,
    draft_body: str = "",
    guest_message: str = "",
    confidence: float = 1.0,
) -> AutoSendDecision:
    """
    Evaluate whether the auto-send pipeline should fire for this thread.

    Parameters
    ----------
    thread
        The MessageThread (must already have detected_context + applied_template_id set).
    db
        Async DB session (read-only in this function).
    draft_body
        The AI-generated draft text (for length + risky-keyword checks).
    guest_message
        Original guest message (for complaint-sentiment check).
    confidence
        Float 0–1 representing the AI model's estimated confidence.
        If unavailable, caller can pass 1.0 to skip the check.

    Returns
    -------
    AutoSendDecision
    """
    # ── Step 1: find a matching rule ──────────────────────────────────────────
    rule = await _find_matching_rule(thread, db)
    if rule is None:
        return AutoSendDecision(
            should_auto_send=False,
            decision="manual_review",
            reason_code="no_rule",
            reason_message="No active auto-send rule matched this thread",
            matched_rule_id=None,
            matched_rule=None,
        )

    # ── Step 2: run guardrails in priority order ──────────────────────────────
    checks = [
        _check_blocked_category(thread),
        _check_complaint_sentiment(guest_message),
        _check_risky_keywords(draft_body),
        _check_draft_length(draft_body),
        _check_confidence(confidence, float(rule.min_confidence)),
        _check_time_window(rule),
        _check_template_required(rule, thread),
    ]

    for passed, reason_code, reason_message in checks:
        if not passed:
            logger.info(
                "auto_send BLOCKED thread=%d rule=%d: %s — %s",
                thread.id, rule.id, reason_code, reason_message,
            )
            return AutoSendDecision(
                should_auto_send=False,
                decision="blocked",
                reason_code=reason_code,
                reason_message=reason_message,
                matched_rule_id=rule.id,
                matched_rule=rule,
            )

    # ── All checks passed → approved ─────────────────────────────────────────
    logger.info(
        "auto_send APPROVED thread=%d rule=%d context=%s",
        thread.id, rule.id, thread.detected_context,
    )
    return AutoSendDecision(
        should_auto_send=True,
        decision="sent",
        reason_code="ok",
        reason_message="All guardrails passed",
        matched_rule_id=rule.id,
        matched_rule=rule,
    )


async def log_decision(
    thread: MessageThread,
    decision: AutoSendDecision,
    db: AsyncSession,
) -> AutoSendDecisionLog:
    """Persist the decision to the audit log and update thread fields."""
    log_entry = AutoSendDecisionLog(
        user_id=thread.user_id,
        thread_id=thread.id,
        template_id=thread.applied_template_id,
        matched_rule_id=decision.matched_rule_id,
        decision=decision.decision,
        reason_code=decision.reason_code,
        reason_message=decision.reason_message,
    )
    db.add(log_entry)

    # Update thread
    thread.auto_send_decision = decision.decision
    thread.auto_send_rule_id = decision.matched_rule_id

    return log_entry
