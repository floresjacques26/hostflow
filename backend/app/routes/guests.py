from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.guest import GuestProfile
from app.models.thread import MessageThread
from app.services.guest_service import get_profile_stats

router = APIRouter(prefix="/guests", tags=["guests"])


class GuestProfileOut(BaseModel):
    id: int
    name: Optional[str]
    primary_email: Optional[str]
    primary_phone: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class GuestProfileUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None


class GuestProfileDetail(GuestProfileOut):
    thread_count: int = 0
    common_contexts: List[str] = []
    properties: List[dict] = []
    last_contact_at: Optional[datetime] = None
    recent_threads: List[dict] = []


@router.get("", response_model=List[GuestProfileOut])
async def list_guests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GuestProfile)
        .where(GuestProfile.user_id == current_user.id)
        .order_by(GuestProfile.updated_at.desc())
        .limit(200)
    )
    return result.scalars().all()


@router.get("/{guest_id}", response_model=GuestProfileDetail)
async def get_guest(
    guest_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GuestProfile).where(
            GuestProfile.id == guest_id,
            GuestProfile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Hóspede não encontrado")

    stats = await get_profile_stats(guest_id, db)

    # Recent threads (last 5)
    threads_result = await db.execute(
        select(MessageThread)
        .where(MessageThread.guest_profile_id == guest_id)
        .order_by(MessageThread.last_message_at.desc().nullsfirst())
        .limit(5)
    )
    recent_threads = [
        {
            "id": t.id,
            "subject": t.subject,
            "status": t.status,
            "detected_context": t.detected_context,
            "created_at": t.created_at,
        }
        for t in threads_result.scalars().all()
    ]

    return GuestProfileDetail(
        id=profile.id,
        name=profile.name,
        primary_email=profile.primary_email,
        primary_phone=profile.primary_phone,
        notes=profile.notes,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        **stats,
        recent_threads=recent_threads,
    )


@router.patch("/{guest_id}", response_model=GuestProfileOut)
async def update_guest(
    guest_id: int,
    payload: GuestProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GuestProfile).where(
            GuestProfile.id == guest_id,
            GuestProfile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Hóspede não encontrado")

    from datetime import timezone
    if payload.name is not None:
        profile.name = payload.name
    if payload.notes is not None:
        profile.notes = payload.notes
    profile.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(profile)
    return profile
