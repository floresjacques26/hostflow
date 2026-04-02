from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.property import Property
from app.models.usage import UsageCounter
from app.models.event import UserEvent
from app.models.email_log import EmailLog
from app.schemas.analytics import (
    FunnelMetrics, DashboardStats, EventStatsOut, EventFrequency, DailyCount,
    EmailStatsOut, EmailStatEntry,
)
from app.services.usage_service import get_usage_summary
from app.services.onboarding_service import is_user_activated

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard-stats", response_model=DashboardStats)
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    usage = await get_usage_summary(current_user.id, db)

    total_result = await db.execute(
        select(func.sum(UsageCounter.ai_responses)).where(UsageCounter.user_id == current_user.id)
    )
    total_responses = int(total_result.scalar_one() or 0)

    prop_result = await db.execute(
        select(func.count()).where(Property.user_id == current_user.id)
    )
    properties_count = prop_result.scalar_one()

    month_responses = usage["ai_responses"]
    minutes_per_response = 2

    return DashboardStats(
        ai_responses_month=month_responses,
        ai_responses_total=total_responses,
        minutes_saved_month=month_responses * minutes_per_response,
        minutes_saved_total=total_responses * minutes_per_response,
        properties_count=properties_count,
        is_activated=is_user_activated(current_user),
        trial_days_remaining=current_user.trial_days_remaining,
    )


@router.get("/funnel", response_model=FunnelMetrics)
async def funnel_metrics(
    _current_user: User = Depends(get_current_user),  # auth required; add admin check later
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    activated = (
        await db.execute(select(func.count()).where(User.onboarding_step >= 2))
    ).scalar_one()

    trial = (
        await db.execute(select(func.count()).where(User.subscription_status == "trialing"))
    ).scalar_one()

    paying = (
        await db.execute(select(func.count()).where(User.subscription_status == "active"))
    ).scalar_one()

    activation_rate = round(activated / total * 100, 1) if total else 0.0
    trial_conv = round(paying / trial * 100, 1) if trial else 0.0

    return FunnelMetrics(
        total_users=total,
        activated_users=activated,
        trial_users=trial,
        paying_users=paying,
        activation_rate_pct=activation_rate,
        trial_conversion_rate_pct=trial_conv,
    )


@router.get("/event-stats", response_model=EventStatsOut)
async def event_stats(
    days: int = 30,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin-oriented endpoint: top event frequencies + daily time series.
    `days` controls the window for daily series (default 30).
    """
    # 1. Top events by frequency (all time)
    freq_rows = (await db.execute(
        select(UserEvent.event_name, func.count().label("count"))
        .group_by(UserEvent.event_name)
        .order_by(func.count().desc())
        .limit(15)
    )).all()
    top_events = [EventFrequency(event_name=r.event_name, count=r.count) for r in freq_rows]

    # 2. Daily signups (users.created_at) over the last `days` days
    signup_rows = (await db.execute(
        text(
            "SELECT DATE(created_at) AS date, COUNT(*) AS count "
            "FROM users "
            "WHERE created_at >= NOW() - INTERVAL ':days days' "
            "GROUP BY DATE(created_at) "
            "ORDER BY date"
        ).bindparams(days=days)
    )).all()
    daily_signups = [DailyCount(date=str(r.date), count=r.count) for r in signup_rows]

    # 3. Daily activations: date of each user's first generated_response event
    activation_rows = (await db.execute(
        text(
            "SELECT DATE(first_response) AS date, COUNT(*) AS count "
            "FROM ( "
            "  SELECT user_id, MIN(created_at) AS first_response "
            "  FROM user_events "
            "  WHERE event_name = 'generated_response' "
            "  GROUP BY user_id "
            ") sub "
            "WHERE first_response >= NOW() - INTERVAL ':days days' "
            "GROUP BY DATE(first_response) "
            "ORDER BY date"
        ).bindparams(days=days)
    )).all()
    daily_activations = [DailyCount(date=str(r.date), count=r.count) for r in activation_rows]

    return EventStatsOut(
        top_events=top_events,
        daily_signups=daily_signups,
        daily_activations=daily_activations,
    )


@router.get("/email-stats", response_model=EmailStatsOut)
async def email_stats(
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin-only: outbound lifecycle email performance by type.
    """
    rows = (await db.execute(
        select(
            EmailLog.email_type,
            func.sum(
                func.cast(EmailLog.status == "sent", func.Integer())
            ).label("sent"),
            func.sum(
                func.cast(EmailLog.status == "failed", func.Integer())
            ).label("failed"),
        )
        .group_by(EmailLog.email_type)
        .order_by(func.sum(
            func.cast(EmailLog.status == "sent", func.Integer())
        ).desc())
    )).all()

    by_type = [EmailStatEntry(email_type=r.email_type, sent=r.sent or 0, failed=r.failed or 0)
               for r in rows]
    total_sent = sum(e.sent for e in by_type)
    total_failed = sum(e.failed for e in by_type)

    return EmailStatsOut(by_type=by_type, total_sent=total_sent, total_failed=total_failed)
