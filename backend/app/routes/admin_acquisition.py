from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text
from app.core.database import get_db
from app.core.security import get_admin_user
from app.models.user import User
from app.models.referral import Referral
from app.models.testimonial import Testimonial

router = APIRouter(prefix="/admin/acquisition", tags=["admin-acquisition"])


@router.get("/overview")
async def acquisition_overview(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Users by utm_source
    by_source = await db.execute(
        select(
            func.coalesce(User.utm_source, "direct").label("source"),
            func.count().label("total"),
            func.sum(case((User.onboarding_completed == True, 1), else_=0)).label("activated"),
            func.sum(case((User.subscription_status.in_(["active", "past_due"]), 1), else_=0)).label("paying"),
        )
        .group_by(text("1"))
        .order_by(func.count().desc())
    )
    sources = [
        {
            "source": r.source,
            "total": r.total,
            "activated": r.activated,
            "paying": r.paying,
            "activation_rate": round(r.activated / r.total * 100, 1) if r.total else 0,
            "conversion_rate": round(r.paying / r.total * 100, 1) if r.total else 0,
        }
        for r in by_source.all()
    ]

    # Referral stats
    referral_stats = await db.execute(
        select(
            func.count().label("total_referrals"),
            func.sum(case((Referral.status == "rewarded", 1), else_=0)).label("rewarded"),
            func.sum(case((Referral.status == "pending", 1), else_=0)).label("pending"),
        )
    )
    rs = referral_stats.one()

    # Top referrers
    top_ref = await db.execute(
        select(
            User.id,
            User.name,
            User.email,
            func.count(Referral.id).label("referral_count"),
            func.sum(case((Referral.status == "rewarded", 1), else_=0)).label("rewarded_count"),
        )
        .join(Referral, Referral.referrer_user_id == User.id)
        .group_by(User.id, User.name, User.email)
        .order_by(func.count(Referral.id).desc())
        .limit(10)
    )
    top_referrers = [
        {
            "user_id": r.id,
            "name": r.name,
            "email": r.email,
            "referral_count": r.referral_count,
            "rewarded_count": r.rewarded_count,
        }
        for r in top_ref.all()
    ]

    # Users from partner codes
    partner_stats = await db.execute(
        select(
            func.coalesce(User.partner_code, "none").label("partner_code"),
            func.count().label("total"),
            func.sum(case((User.subscription_status.in_(["active", "past_due"]), 1), else_=0)).label("paying"),
        )
        .where(User.partner_code.isnot(None))
        .group_by(text("1"))
        .order_by(func.count().desc())
    )
    partners = [
        {"partner_code": r.partner_code, "total": r.total, "paying": r.paying}
        for r in partner_stats.all()
    ]

    # Testimonial stats
    test_stats = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((Testimonial.status == "approved", 1), else_=0)).label("approved"),
            func.sum(case((Testimonial.status == "pending", 1), else_=0)).label("pending"),
            func.avg(Testimonial.rating).label("avg_rating"),
        )
    )
    ts = test_stats.one()

    return {
        "by_source": sources,
        "referrals": {
            "total": rs.total_referrals or 0,
            "rewarded": rs.rewarded or 0,
            "pending": rs.pending or 0,
        },
        "top_referrers": top_referrers,
        "by_partner": partners,
        "testimonials": {
            "total": ts.total or 0,
            "approved": ts.approved or 0,
            "pending": ts.pending or 0,
            "avg_rating": round(float(ts.avg_rating), 1) if ts.avg_rating else 0.0,
        },
    }


@router.get("/testimonials")
async def admin_testimonials(
    status: str = "pending",
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.status == status)
        .order_by(Testimonial.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "rating": r.rating,
            "quote": r.quote,
            "trigger_event": r.trigger_event,
            "status": r.status,
            "approved_for_public_use": r.approved_for_public_use,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.patch("/testimonials/{testimonial_id}")
async def update_testimonial(
    testimonial_id: int,
    payload: dict,
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(Testimonial).where(Testimonial.id == testimonial_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Não encontrado")

    if "status" in payload:
        t.status = payload["status"]
    if "approved_for_public_use" in payload:
        t.approved_for_public_use = payload["approved_for_public_use"]

    await db.commit()
    return {"id": t.id, "status": t.status, "approved_for_public_use": t.approved_for_public_use}
