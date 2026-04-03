"""
Admin CRM: user list, user detail, and CSV exports.
All routes require is_admin=True.
"""
import csv
import io
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, asc
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_admin_user
from app.models.user import User
from app.models.property import Property
from app.models.template import Template
from app.models.usage import UsageCounter
from app.models.event import UserEvent
from app.models.email_log import EmailLog
from app.admin.scoring import compute_health_score, compute_churn_risk, recommended_action
from app.services.usage_service import _current_month

router = APIRouter(prefix="/admin/users", tags=["admin"])


# ── Shared query helpers ──────────────────────────────────────────────────────

async def _enrich_user(user: User, db: AsyncSession) -> dict:
    """
    Run all per-user sub-queries needed for scoring + CRM display.
    Call this per-user only — use bulk loaders for list endpoints.
    """
    month = _current_month()

    usage_row = (await db.execute(
        select(UsageCounter).where(
            UsageCounter.user_id == user.id,
            UsageCounter.month == month,
        )
    )).scalar_one_or_none()
    ai_month = usage_row.ai_responses if usage_row else 0

    last_event = (await db.execute(
        select(UserEvent.created_at)
        .where(UserEvent.user_id == user.id)
        .order_by(desc(UserEvent.created_at))
        .limit(1)
    )).scalar_one_or_none()

    prop_count = (await db.execute(
        select(func.count()).where(Property.user_id == user.id)
    )).scalar_one()

    tmpl_count = (await db.execute(
        select(func.count()).where(
            Template.user_id == user.id,
            Template.is_default == False,
        )
    )).scalar_one()

    health = compute_health_score(user, ai_month, last_event, prop_count)
    risk = compute_churn_risk(user, ai_month, last_event, prop_count)
    action = recommended_action(user, risk, health, ai_month)

    return {
        "ai_responses_month": ai_month,
        "last_event_at": last_event,
        "properties_count": prop_count,
        "templates_count": tmpl_count,
        "health_score": health,
        "churn_risk": risk,
        "recommended_action": action,
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserListItem(BaseModel):
    id: int
    name: str
    email: str
    plan: str
    effective_plan: str
    subscription_status: str
    is_trial_active: bool
    trial_ends_at: Optional[datetime]
    trial_days_remaining: int
    current_period_end: Optional[datetime]
    canceled_at: Optional[datetime]
    onboarding_completed: bool
    onboarding_step: int
    created_at: datetime
    last_login_at: Optional[datetime]
    # enriched
    ai_responses_month: int
    properties_count: int
    templates_count: int
    last_event_at: Optional[datetime]
    health_score: int
    churn_risk: str
    recommended_action: str

    model_config = {"from_attributes": True}


class EventItem(BaseModel):
    event_name: str
    created_at: datetime
    metadata: Optional[dict]


class EmailItem(BaseModel):
    email_type: str
    subject: str
    status: str
    sent_at: Optional[datetime]
    created_at: datetime


class UserDetail(UserListItem):
    recent_events: List[EventItem]
    recent_emails: List[EmailItem]


class UserListPage(BaseModel):
    items: List[UserListItem]
    total: int
    page: int
    page_size: int
    pages: int


# ── List endpoint ─────────────────────────────────────────────────────────────

@router.get("", response_model=UserListPage)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    churn_risk: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|last_login_at|name|plan|subscription_status)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)

    if search:
        term = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(User.name).like(term),
                func.lower(User.email).like(term),
            )
        )
    if plan:
        query = query.where(User.plan == plan)
    if status:
        query = query.where(User.subscription_status == status)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Sorting
    col = getattr(User, sort_by, User.created_at)
    order = desc(col) if sort_dir == "desc" else asc(col)
    query = query.order_by(order)

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    users = (await db.execute(query)).scalars().all()

    # Bulk-fetch enrichment data (parallel queries per user — acceptable for admin use)
    items = []
    for user in users:
        enriched = await _enrich_user(user, db)
        # Filter by churn_risk after computation (can't do in SQL without storing it)
        if churn_risk and enriched["churn_risk"] != churn_risk:
            continue
        items.append(UserListItem(
            id=user.id,
            name=user.name,
            email=user.email,
            plan=user.plan,
            effective_plan=user.effective_plan,
            subscription_status=user.subscription_status,
            is_trial_active=user.is_trial_active,
            trial_ends_at=user.trial_ends_at,
            trial_days_remaining=user.trial_days_remaining,
            current_period_end=user.current_period_end,
            canceled_at=user.canceled_at,
            onboarding_completed=user.onboarding_completed,
            onboarding_step=user.onboarding_step,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            **enriched,
        ))

    pages = max(1, -(-total // page_size))  # ceiling div

    return UserListPage(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ── Detail endpoint ───────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: int,
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    enriched = await _enrich_user(user, db)

    recent_events = (await db.execute(
        select(UserEvent)
        .where(UserEvent.user_id == user_id)
        .order_by(desc(UserEvent.created_at))
        .limit(20)
    )).scalars().all()

    recent_emails = (await db.execute(
        select(EmailLog)
        .where(EmailLog.user_id == user_id)
        .order_by(desc(EmailLog.created_at))
        .limit(10)
    )).scalars().all()

    return UserDetail(
        id=user.id,
        name=user.name,
        email=user.email,
        plan=user.plan,
        effective_plan=user.effective_plan,
        subscription_status=user.subscription_status,
        is_trial_active=user.is_trial_active,
        trial_ends_at=user.trial_ends_at,
        trial_days_remaining=user.trial_days_remaining,
        current_period_end=user.current_period_end,
        canceled_at=user.canceled_at,
        onboarding_completed=user.onboarding_completed,
        onboarding_step=user.onboarding_step,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        recent_events=[
            EventItem(
                event_name=e.event_name,
                created_at=e.created_at,
                metadata=e.event_data,
            )
            for e in recent_events
        ],
        recent_emails=[
            EmailItem(
                email_type=el.email_type,
                subject=el.subject,
                status=el.status,
                sent_at=el.sent_at,
                created_at=el.created_at,
            )
            for el in recent_emails
        ],
        **enriched,
    )


# ── CSV export ────────────────────────────────────────────────────────────────

_EXPORT_SEGMENTS = {
    "all":       None,
    "trial":     {"subscription_status": "trialing"},
    "paying":    {"subscription_status": "active"},
    "canceled":  {"subscription_status": "canceled"},
    "past_due":  {"subscription_status": "past_due"},
}


@router.get("/export/{segment}")
async def export_users_csv(
    segment: str,
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    if segment not in _EXPORT_SEGMENTS and segment != "high_risk":
        raise HTTPException(status_code=400, detail=f"Segmento inválido: {segment}")

    query = select(User)
    filter_kv = _EXPORT_SEGMENTS.get(segment)
    if filter_kv:
        for col, val in filter_kv.items():
            query = query.where(getattr(User, col) == val)

    users = (await db.execute(query.order_by(desc(User.created_at)))).scalars().all()

    # Enrich all users for high_risk export
    rows = []
    for user in users:
        enriched = await _enrich_user(user, db)
        if segment == "high_risk" and enriched["churn_risk"] != "high":
            continue
        rows.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan": user.plan,
            "effective_plan": user.effective_plan,
            "subscription_status": user.subscription_status,
            "trial_ends_at": user.trial_ends_at.isoformat() if user.trial_ends_at else "",
            "current_period_end": user.current_period_end.isoformat() if user.current_period_end else "",
            "onboarding_step": user.onboarding_step,
            "onboarding_completed": user.onboarding_completed,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else "",
            "ai_responses_month": enriched["ai_responses_month"],
            "properties_count": enriched["properties_count"],
            "health_score": enriched["health_score"],
            "churn_risk": enriched["churn_risk"],
            "recommended_action": enriched["recommended_action"],
        })

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("no data\n")

    output.seek(0)
    filename = f"hostflow_users_{segment}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
