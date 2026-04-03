from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, TokenOut, UserOut
from app.services import event_service
from app.services import lifecycle_service
from app.services import referral_service
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegisterExtended(UserRegister):
    ref: Optional[str] = None
    partner_code: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


async def _bg_welcome(user_id: int) -> None:
    """Open a fresh DB session for the welcome email (runs after request completes)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            await lifecycle_service.send_welcome(user, db)


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(
    payload: UserRegisterExtended,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        partner_code=payload.partner_code,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
    )
    db.add(user)
    await db.flush()  # get user.id

    # Generate unique referral code for every new user
    import random, string as _string
    for _ in range(10):
        candidate = "".join(random.choices(_string.ascii_uppercase + _string.digits, k=7))
        existing = await db.execute(select(User).where(User.referral_code == candidate))
        if existing.scalar_one_or_none() is None:
            user.referral_code = candidate
            break

    # Apply incoming referral attribution
    if payload.ref:
        await referral_service.apply_referral(user, payload.ref, db)

    await event_service.track(user, event_service.SIGNUP, db, metadata={
        "source": payload.utm_source or ("referral" if payload.ref else "web"),
        "ref": payload.ref,
        "partner": payload.partner_code,
    })
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(_bg_welcome, user.id)

    token = create_access_token({"sub": str(user.id)})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    user.last_login_at = datetime.utcnow()
    await event_service.track(user, event_service.LOGIN, db)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
