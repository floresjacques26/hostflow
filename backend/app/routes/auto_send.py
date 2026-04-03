"""
CRUD for AutoSendRule + read-only audit log viewer.

Endpoints:
  GET    /auto-send/rules              — list user's rules
  POST   /auto-send/rules              — create rule
  PATCH  /auto-send/rules/{rule_id}    — update rule
  DELETE /auto-send/rules/{rule_id}    — delete rule
  GET    /auto-send/logs               — paginated audit log
  GET    /auto-send/stats              — summary stats for settings page
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from datetime import datetime, timezone
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.auto_send import AutoSendRule, AutoSendDecisionLog
from app.models.template import Template

router = APIRouter(prefix="/auto-send", tags=["auto-send"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    property_id: Optional[int] = None
    channel_type: Optional[str] = Field(None, max_length=30)
    context_key: Optional[str] = Field(None, max_length=40)
    template_id: Optional[int] = None
    min_confidence: float = Field(0.85, ge=0.0, le=1.0)
    require_template_match: bool = True
    allowed_start_hour: Optional[int] = Field(None, ge=0, le=23)
    allowed_end_hour: Optional[int] = Field(None, ge=0, le=23)
    active: bool = True


class RuleUpdate(BaseModel):
    property_id: Optional[int] = None
    channel_type: Optional[str] = Field(None, max_length=30)
    context_key: Optional[str] = Field(None, max_length=40)
    template_id: Optional[int] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    require_template_match: Optional[bool] = None
    allowed_start_hour: Optional[int] = Field(None, ge=0, le=23)
    allowed_end_hour: Optional[int] = Field(None, ge=0, le=23)
    active: Optional[bool] = None


class RuleOut(BaseModel):
    id: int
    property_id: Optional[int]
    channel_type: Optional[str]
    context_key: Optional[str]
    template_id: Optional[int]
    min_confidence: float
    require_template_match: bool
    allowed_start_hour: Optional[int]
    allowed_end_hour: Optional[int]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LogOut(BaseModel):
    id: int
    thread_id: int
    template_id: Optional[int]
    matched_rule_id: Optional[int]
    decision: str
    reason_code: str
    reason_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Rule endpoints ────────────────────────────────────────────────────────────

@router.get("/rules", response_model=List[RuleOut])
async def list_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AutoSendRule)
        .where(AutoSendRule.user_id == current_user.id)
        .order_by(AutoSendRule.created_at.desc())
    )
    return result.scalars().all()


@router.post("/rules", response_model=RuleOut, status_code=201)
async def create_rule(
    payload: RuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.template_id is not None:
        t = await db.get(Template, payload.template_id)
        if not t or t.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Template não encontrado")

    rule = AutoSendRule(
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AutoSendRule).where(
            AutoSendRule.id == rule_id,
            AutoSendRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Regra não encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AutoSendRule).where(
            AutoSendRule.id == rule_id,
            AutoSendRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    await db.delete(rule)
    await db.commit()


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=List[LogOut])
async def list_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    decision: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AutoSendDecisionLog)
        .where(AutoSendDecisionLog.user_id == current_user.id)
        .order_by(AutoSendDecisionLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if decision:
        query = query.where(AutoSendDecisionLog.decision == decision)
    result = await db.execute(query)
    return result.scalars().all()


# ── Summary stats ─────────────────────────────────────────────────────────────

@router.get("/stats")
async def auto_send_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick stats for the settings page dashboard panel."""
    totals = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((AutoSendDecisionLog.decision == "sent", 1), else_=0)).label("sent"),
            func.sum(case((AutoSendDecisionLog.decision == "blocked", 1), else_=0)).label("blocked"),
            func.sum(case((AutoSendDecisionLog.decision == "manual_review", 1), else_=0)).label("manual_review"),
        ).where(AutoSendDecisionLog.user_id == current_user.id)
    )
    t = totals.one()

    # Top block reasons
    reasons = await db.execute(
        select(
            AutoSendDecisionLog.reason_code,
            func.count().label("count"),
        )
        .where(
            AutoSendDecisionLog.user_id == current_user.id,
            AutoSendDecisionLog.decision == "blocked",
        )
        .group_by(AutoSendDecisionLog.reason_code)
        .order_by(func.count().desc())
        .limit(10)
    )

    active_rules = await db.execute(
        select(func.count()).where(
            AutoSendRule.user_id == current_user.id,
            AutoSendRule.active == True,  # noqa: E712
        )
    )

    total = t.total or 0
    sent = t.sent or 0
    return {
        "total_evaluations": total,
        "auto_sent": sent,
        "blocked": t.blocked or 0,
        "manual_review": t.manual_review or 0,
        "auto_send_rate_pct": round(sent / total * 100, 1) if total else 0.0,
        "active_rules": active_rules.scalar() or 0,
        "top_block_reasons": [
            {"reason_code": r.reason_code, "count": r.count}
            for r in reasons.all()
        ],
    }
