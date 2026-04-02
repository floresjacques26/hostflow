from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.testimonial import Testimonial

router = APIRouter(prefix="/testimonials", tags=["testimonials"])


class TestimonialCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    quote: str = Field(..., min_length=10, max_length=500)
    trigger_event: Optional[str] = None


@router.post("", status_code=201)
async def submit_testimonial(
    payload: TestimonialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Prevent duplicate submissions per trigger_event
    if payload.trigger_event:
        existing = await db.execute(
            select(Testimonial).where(
                Testimonial.user_id == current_user.id,
                Testimonial.trigger_event == payload.trigger_event,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Avaliação já enviada para este contexto")

    t = Testimonial(
        user_id=current_user.id,
        rating=payload.rating,
        quote=payload.quote,
        trigger_event=payload.trigger_event,
    )
    db.add(t)
    await db.commit()
    return {"id": t.id, "status": "pending"}


@router.get("/public")
async def public_testimonials(db: AsyncSession = Depends(get_db)):
    """Returns approved testimonials for the landing page."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Testimonial)
        .options(selectinload(Testimonial.user))
        .where(
            Testimonial.approved_for_public_use == True,
            Testimonial.status == "approved",
        )
        .order_by(Testimonial.created_at.desc())
        .limit(12)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "rating": r.rating,
            "quote": r.quote,
            "user_name": r.user.name if r.user else "Usuário",
            "created_at": r.created_at,
        }
        for r in rows
    ]
