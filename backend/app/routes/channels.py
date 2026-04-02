from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.schemas.inbox import ChannelCreate, ChannelOut

router = APIRouter(prefix="/channels", tags=["channels"])

VALID_TYPES = {"manual", "email_forward", "gmail", "whatsapp", "webhook"}


@router.get("", response_model=List[ChannelOut])
async def list_channels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Channel)
        .where(Channel.user_id == current_user.id)
        .order_by(Channel.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(
    payload: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(VALID_TYPES)}")

    channel = Channel(
        user_id=current_user.id,
        property_id=payload.property_id,
        type=payload.type,
        name=payload.name,
        external_id=payload.external_id,
        config_json=payload.config_json,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.patch("/{channel_id}", response_model=ChannelOut)
async def update_channel(
    channel_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.user_id == current_user.id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Canal não encontrado")

    allowed = {"name", "status", "external_id", "config_json", "property_id"}
    for k, v in payload.items():
        if k in allowed:
            setattr(channel, k, v)

    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.user_id == current_user.id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    await db.delete(channel)
    await db.commit()


@router.get("/inbox-address")
async def inbox_address(current_user: User = Depends(get_current_user)):
    """Return the user's unique email ingestion address."""
    code = current_user.referral_code or str(current_user.id)
    return {
        "address": f"inbox+{code}@in.hostflow.io",
        "instructions": (
            "Encaminhe mensagens de hóspedes para este endereço. "
            "O HostFlow criará uma conversa automaticamente."
        ),
    }
