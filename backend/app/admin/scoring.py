"""
Health score and churn risk scoring for users.

Design goals:
  - Fully deterministic: same inputs → same output, no randomness
  - Transparent: each sub-score is named and weighted explicitly
  - Easy to tune: change weights at the top of the file
  - No ML required — pure rule-based logic on existing model fields + DB queries

Outputs:
  health_score : int 0–100
  churn_risk   : "low" | "medium" | "high"
"""
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.user import User

# ── Weight table (all weights must sum to 100 in each section) ────────────────
#
# Health score components (positive signals):
_H = {
    "activated":           25,   # created property + generated response
    "active_7d":           20,   # any event in last 7 days
    "active_30d":          10,   # any event in last 30 days (partial credit)
    "has_property":        15,   # at least one property
    "ai_responses_month":  15,   # used responses this month
    "paying_subscriber":   15,   # active subscription (not trialing/free)
}
# Total = 100 ✓


def compute_health_score(
    user: User,
    ai_responses_month: int,
    last_event_at: datetime | None,
    properties_count: int,
) -> int:
    """
    Returns health_score 0–100.
    All inputs are pre-queried to avoid N+1 in list endpoints.
    """
    score = 0
    now = datetime.now(timezone.utc)

    # 1. Activation (completed steps 1+2: property + ai_response)
    if user.onboarding_step >= 2:
        score += _H["activated"]

    # 2. Recency
    if last_event_at:
        age_days = (now - last_event_at.replace(tzinfo=timezone.utc)).days
        if age_days <= 7:
            score += _H["active_7d"]
        elif age_days <= 30:
            score += _H["active_30d"]

    # 3. Property setup
    if properties_count >= 1:
        score += _H["has_property"]

    # 4. AI usage this month (tiered)
    if ai_responses_month >= 20:
        score += _H["ai_responses_month"]
    elif ai_responses_month >= 5:
        score += int(_H["ai_responses_month"] * 0.6)
    elif ai_responses_month >= 1:
        score += int(_H["ai_responses_month"] * 0.2)

    # 5. Paying subscriber
    if user.effective_plan != "free" and user.subscription_status == "active":
        score += _H["paying_subscriber"]

    return min(100, score)


def compute_churn_risk(
    user: User,
    ai_responses_month: int,
    last_event_at: datetime | None,
    properties_count: int,
) -> str:
    """
    Returns "low" | "medium" | "high".
    Uses additive risk points — higher total = higher risk bucket.
    """
    risk = 0
    now = datetime.now(timezone.utc)

    # Hard blockers
    if user.subscription_status == "canceled":
        risk += 40

    if user.subscription_status == "past_due":
        risk += 35

    # Trial about to expire without activation
    if user.is_trial_active and user.trial_days_remaining <= 3:
        if user.onboarding_step < 2:
            risk += 30  # trial ending + not activated = high risk
        else:
            risk += 15  # trial ending but activated

    # No activity
    if last_event_at is None:
        risk += 25  # never active
    else:
        age_days = (now - last_event_at.replace(tzinfo=timezone.utc)).days
        if age_days >= 30:
            risk += 25
        elif age_days >= 14:
            risk += 15
        elif age_days >= 7:
            risk += 8

    # Trial expired without converting
    if (
        user.subscription_status == "trialing"
        and user.trial_ends_at is not None
        and user.trial_ends_at.replace(tzinfo=timezone.utc) < now
    ):
        risk += 30

    # Not activated after signup (7+ days old)
    if (
        user.onboarding_step < 2
        and (now - user.created_at.replace(tzinfo=timezone.utc)).days >= 7
    ):
        risk += 15

    # Low usage despite having subscription
    if user.subscription_status == "active" and ai_responses_month == 0:
        risk += 20  # paying but not using → real churn signal

    # Healthy offset: activated + using regularly
    if user.onboarding_step >= 2 and ai_responses_month >= 10:
        risk -= 20

    risk = max(0, risk)

    if risk >= 50:
        return "high"
    if risk >= 20:
        return "medium"
    return "low"


def recommended_action(
    user: User,
    churn_risk: str,
    health_score: int,
    ai_responses_month: int,
) -> str:
    """
    Returns a single recommended admin action string.
    """
    if user.subscription_status == "past_due":
        return "Pagamento pendente — acionar recuperação"
    if user.subscription_status == "canceled":
        return "Assinatura cancelada — candidato a win-back"
    if churn_risk == "high" and user.is_trial_active and user.onboarding_step < 2:
        return "Trial em risco: não ativado — indicado para contato direto"
    if churn_risk == "high":
        return "Alto risco de churn — intervenção recomendada"
    if user.is_trial_active and user.trial_days_remaining <= 3 and user.onboarding_step >= 2:
        return "Trial expirando — alta chance de conversão, acionar desconto"
    if user.subscription_status == "active" and ai_responses_month == 0:
        return "Assinante inativo — risco de cancelamento no próximo ciclo"
    if health_score >= 70 and user.subscription_status == "active":
        return "Usuário saudável — potencial para upsell Business"
    if user.onboarding_step >= 2 and user.subscription_status in ("free", "trialing"):
        return "Ativado no plano Free/Trial — alto potencial de conversão"
    if user.onboarding_step < 1:
        return "Usuário não iniciou onboarding — enviar lembrete de ativação"
    return "Monitorar"
