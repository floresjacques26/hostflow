from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.guards import guard_property_limit
from app.models.user import User
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyOut, PropertySummary
from app.services.onboarding_service import advance_onboarding
from app.services import event_service
from typing import List

router = APIRouter(prefix="/properties", tags=["properties"])


async def _get_owned_property(
    property_id: int, current_user: User, db: AsyncSession
) -> Property:
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.user_id == current_user.id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return prop


@router.get("/", response_model=List[PropertySummary])
async def list_properties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property)
        .where(Property.user_id == current_user.id)
        .order_by(Property.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=PropertyOut, status_code=201)
async def create_property(
    payload: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await guard_property_limit(current_user, db)

    prop = Property(**payload.model_dump(), user_id=current_user.id)
    db.add(prop)
    await db.flush()  # get prop.id

    await event_service.track(
        current_user, event_service.CREATED_PROPERTY, db,
        metadata={"property_name": prop.name, "property_type": prop.type},
    )
    await advance_onboarding(current_user, "property", db)

    await db.commit()
    await db.refresh(prop)
    return prop


@router.get("/{property_id}", response_model=PropertyOut)
async def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_owned_property(property_id, current_user, db)


@router.put("/{property_id}", response_model=PropertyOut)
async def update_property(
    property_id: int,
    payload: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prop = await _get_owned_property(property_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prop, field, value)
    await db.commit()
    await db.refresh(prop)
    return prop


@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prop = await _get_owned_property(property_id, current_user, db)
    await db.delete(prop)
    await db.commit()
