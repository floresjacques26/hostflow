from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.onboarding import OnboardingState, SkipOnboardingRequest
from app.services.onboarding_service import get_onboarding_state
from app.services import event_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/", response_model=OnboardingState)
async def get_state(current_user: User = Depends(get_current_user)):
    return get_onboarding_state(current_user)


@router.post("/skip", response_model=OnboardingState)
async def skip_onboarding(
    payload: SkipOnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.onboarding_completed:
        current_user.onboarding_completed = True
        await event_service.track(
            current_user,
            event_service.ONBOARDING_SKIPPED,
            db,
            metadata={"reason": payload.reason, "step_reached": current_user.onboarding_step},
        )
        await db.commit()

    return get_onboarding_state(current_user)
