"""
Revenue and business metrics service.

MRR model:
  - Source of truth is local DB subscription data (plan + subscription_status)
  - Plan prices come from config (BRL cents) so they can be overridden per-env
  - When Stripe invoice data is available, real amounts can replace estimates

All monetary values are returned in BRL cents (integers) unless noted.
Divide by 100 for display.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.models.user import User
from app.models.usage import UsageCounter
from app.models.event import UserEvent
from app.core.config import settings


# ── MRR helpers ───────────────────────────────────────────────────────────────

def _plan_mrr_cents(plan: str, status: str) -> int:
    """Return estimated MRR in BRL cents for a single user's subscription."""
    if status not in ("active", "past_due"):
        return 0
    if plan == "pro":
        return settings.plan_price_pro_brl
    if plan == "business":
        return settings.plan_price_business_brl
    return 0


# ── Core revenue metrics ──────────────────────────────────────────────────────

async def compute_revenue_metrics(db: AsyncSession) -> dict:
    """
    Returns all business-level KPIs as a single dict.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # ── User counts by status ────────────────────────────────────────────────
    rows = (await db.execute(
        select(
            User.subscription_status,
            User.plan,
            User.is_active,
            func.count().label("n"),
        )
        .group_by(User.subscription_status, User.plan, User.is_active)
    )).all()

    total_users = 0
    active_users = 0
    trial_users = 0
    paying_users = 0
    past_due_users = 0
    canceled_users = 0
    free_users = 0
    pro_users = 0
    business_users = 0
    mrr_cents = 0

    for r in rows:
        total_users += r.n
        if r.is_active:
            active_users += r.n

        if r.subscription_status == "trialing":
            trial_users += r.n
        elif r.subscription_status == "active":
            paying_users += r.n
        elif r.subscription_status == "past_due":
            past_due_users += r.n
        elif r.subscription_status == "canceled":
            canceled_users += r.n
        else:
            free_users += r.n

        # MRR from active + past_due (past_due still has access)
        mrr_cents += _plan_mrr_cents(r.plan, r.subscription_status) * r.n

        # Plan breakdown (paying only)
        if r.subscription_status in ("active", "past_due"):
            if r.plan == "pro":
                pro_users += r.n
            elif r.plan == "business":
                business_users += r.n

    arr_cents = mrr_cents * 12

    # ── Activated users ──────────────────────────────────────────────────────
    activated_count = (await db.execute(
        select(func.count()).where(User.onboarding_step >= 2)
    )).scalar_one()

    # ── Cancellations last 30 days ───────────────────────────────────────────
    canceled_30d = (await db.execute(
        select(func.count()).where(
            User.subscription_status == "canceled",
            User.canceled_at >= thirty_days_ago,
        )
    )).scalar_one()

    # ── Payment failures (past_due) ──────────────────────────────────────────
    payment_failure_count = past_due_users

    # ── Trials expiring in next 7 days ───────────────────────────────────────
    trials_expiring_7d = (await db.execute(
        select(func.count()).where(
            User.subscription_status == "trialing",
            User.trial_ends_at >= now,
            User.trial_ends_at <= now + timedelta(days=7),
        )
    )).scalar_one()

    # ── New users last 30 days ────────────────────────────────────────────────
    new_users_30d = (await db.execute(
        select(func.count()).where(User.created_at >= thirty_days_ago)
    )).scalar_one()

    # ── ARPPU / ARPU ────────────────────────────────────────────────────────
    arppu_cents = mrr_cents // paying_users if paying_users else 0
    arpu_cents = mrr_cents // total_users if total_users else 0

    # ── Rates ────────────────────────────────────────────────────────────────
    activation_rate = round(activated_count / total_users * 100, 1) if total_users else 0.0

    # trial-to-paid: paying users / all users who ever started a trial
    ever_trialed = (await db.execute(
        select(func.count()).where(User.trial_ends_at.is_not(None))
    )).scalar_one()
    trial_conversion_rate = round(paying_users / ever_trialed * 100, 1) if ever_trialed else 0.0

    # churn rate: canceled last 30d / paying at start of period (approx: paying + canceled_30d)
    base_for_churn = paying_users + canceled_30d
    churn_rate = round(canceled_30d / base_for_churn * 100, 1) if base_for_churn else 0.0

    # ── Cohort helpers: upgrades + downgrades ─────────────────────────────────
    # Detect via user_events: users who have an "upgraded_plan" event in last 30 days
    upgrades_30d = (await db.execute(
        select(func.count(func.distinct(UserEvent.user_id))).where(
            UserEvent.event_name == "upgraded_plan",
            UserEvent.created_at >= thirty_days_ago,
        )
    )).scalar_one()

    return {
        # Users
        "total_users": total_users,
        "active_users": active_users,
        "activated_users": activated_count,
        "trial_users": trial_users,
        "paying_users": paying_users,
        "past_due_users": past_due_users,
        "canceled_users": canceled_users,
        "free_users": free_users,
        "new_users_30d": new_users_30d,
        # Plans
        "pro_users": pro_users,
        "business_users": business_users,
        # Revenue
        "mrr_cents": mrr_cents,
        "arr_cents": arr_cents,
        "arppu_cents": arppu_cents,
        "arpu_cents": arpu_cents,
        # Rates
        "activation_rate_pct": activation_rate,
        "trial_conversion_rate_pct": trial_conversion_rate,
        "churn_rate_pct": churn_rate,
        # Operations
        "payment_failure_count": payment_failure_count,
        "canceled_last_30d": canceled_30d,
        "trials_expiring_7d": trials_expiring_7d,
        "upgrades_last_30d": upgrades_30d,
    }


async def compute_cohort_data(db: AsyncSession) -> list[dict]:
    """
    Group users by signup month with conversion and activation breakdowns.
    Returns list sorted by month desc (most recent first).
    """
    rows = (await db.execute(
        select(
            func.to_char(User.created_at, "YYYY-MM").label("month"),
            func.count().label("signups"),
            func.sum(case((User.onboarding_step >= 2, 1), else_=0)).label("activated"),
            func.sum(case((User.subscription_status == "active", 1), else_=0)).label("converted"),
            func.sum(case((User.subscription_status == "trialing", 1), else_=0)).label("trialing"),
            func.sum(case((User.subscription_status == "canceled", 1), else_=0)).label("canceled"),
        )
        .group_by(func.to_char(User.created_at, "YYYY-MM"))
        .order_by(func.to_char(User.created_at, "YYYY-MM").desc())
        .limit(12)
    )).all()

    return [
        {
            "month": r.month,
            "signups": r.signups,
            "activated": r.activated,
            "converted": r.converted,
            "trialing": r.trialing,
            "canceled": r.canceled,
            "activation_rate": round(r.activated / r.signups * 100, 1) if r.signups else 0.0,
            "conversion_rate": round(r.converted / r.signups * 100, 1) if r.signups else 0.0,
        }
        for r in rows
    ]


async def mrr_by_plan(db: AsyncSession) -> list[dict]:
    """MRR breakdown by plan, for paying subscribers only."""
    rows = (await db.execute(
        select(User.plan, func.count().label("n"))
        .where(User.subscription_status.in_(["active", "past_due"]))
        .group_by(User.plan)
    )).all()

    return [
        {
            "plan": r.plan,
            "users": r.n,
            "mrr_cents": _plan_mrr_cents(r.plan, "active") * r.n,
        }
        for r in rows
    ]
