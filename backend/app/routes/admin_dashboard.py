"""
Admin revenue dashboard endpoints.
All routes require is_admin=True via get_admin_user dependency.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_admin_user
from app.admin.metrics import compute_revenue_metrics, compute_cohort_data, mrr_by_plan

router = APIRouter(prefix="/admin/dashboard", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RevenueMetrics(BaseModel):
    # User counts
    total_users: int
    active_users: int
    activated_users: int
    trial_users: int
    paying_users: int
    past_due_users: int
    canceled_users: int
    free_users: int
    new_users_30d: int
    pro_users: int
    business_users: int
    # Revenue (BRL cents)
    mrr_cents: int
    arr_cents: int
    arppu_cents: int
    arpu_cents: int
    # Rates
    activation_rate_pct: float
    trial_conversion_rate_pct: float
    churn_rate_pct: float
    # Operations
    payment_failure_count: int
    canceled_last_30d: int
    trials_expiring_7d: int
    upgrades_last_30d: int


class CohortRow(BaseModel):
    month: str
    signups: int
    activated: int
    converted: int
    trialing: int
    canceled: int
    activation_rate: float
    conversion_rate: float


class MrrByPlanRow(BaseModel):
    plan: str
    users: int
    mrr_cents: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=RevenueMetrics)
async def get_metrics(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    data = await compute_revenue_metrics(db)
    return RevenueMetrics(**data)


@router.get("/cohorts", response_model=List[CohortRow])
async def get_cohorts(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await compute_cohort_data(db)
    return [CohortRow(**r) for r in rows]


@router.get("/mrr-by-plan", response_model=List[MrrByPlanRow])
async def get_mrr_by_plan(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await mrr_by_plan(db)
    return [MrrByPlanRow(**r) for r in rows]
