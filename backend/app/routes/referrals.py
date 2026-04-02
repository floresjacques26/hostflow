from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services import referral_service

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/stats")
async def referral_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await referral_service.get_referral_stats(current_user, db)
