"""
Onboarding state machine.

Steps:
  0 → not started
  1 → created first property          (step 1 done)
  2 → generated first AI response     (step 2 done)
  3 → connected Gmail or WhatsApp     (step 3 done)
  4 → created first custom template   (step 4 done = completed)
"""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services import event_service

TOTAL_STEPS = 4

# Which step index each action completes
STEP_MAP = {
    "property":    1,
    "ai_response": 2,
    "integration": 3,
    "template":    4,
}


async def advance_onboarding(user: User, action: str, db: AsyncSession) -> bool:
    """
    Advance onboarding state when user completes an action.
    Returns True if this call just completed the onboarding.
    """
    step_value = STEP_MAP.get(action)
    if step_value is None or user.onboarding_completed:
        return False

    # Start onboarding on first action if not already started
    if user.onboarding_step == 0 and user.onboarding_started_at is None:
        user.onboarding_started_at = datetime.utcnow()
        await event_service.track(user, event_service.ONBOARDING_STARTED, db)

    # Only advance forward (never backwards)
    if step_value > user.onboarding_step:
        user.onboarding_step = step_value

    just_completed = user.onboarding_step >= TOTAL_STEPS and not user.onboarding_completed
    if just_completed:
        user.onboarding_completed = True
        user.onboarding_completed_at = datetime.utcnow()
        await event_service.track(user, event_service.ONBOARDING_COMPLETED, db)

    return just_completed


def is_user_activated(user: User) -> bool:
    """
    A user is 'activated' when they have:
    - created at least 1 property (step 1)
    - generated at least 1 AI response (step 2)
    Activation is the minimum viable 'aha moment'.
    """
    return user.onboarding_step >= 2


def get_onboarding_state(user: User) -> dict:
    steps = [
        {
            "key": "property",
            "step": 1,
            "title": "Cadastre seu primeiro imóvel",
            "description": "Configure check-in, check-out, preços e regras da casa.",
            "done": user.onboarding_step >= 1,
            "path": "/properties",
        },
        {
            "key": "ai_response",
            "step": 2,
            "title": "Gere sua primeira resposta com IA",
            "description": "Cole uma mensagem de hóspede e veja a IA responder.",
            "done": user.onboarding_step >= 2,
            "path": "/dashboard",
        },
        {
            "key": "integration",
            "step": 3,
            "title": "Conecte Gmail ou WhatsApp",
            "description": "Receba mensagens automaticamente no inbox centralizado.",
            "done": user.onboarding_step >= 3,
            "path": "/integrations",
        },
        {
            "key": "template",
            "step": 4,
            "title": "Crie seu primeiro template",
            "description": "Respostas prontas para as perguntas mais frequentes dos hóspedes.",
            "done": user.onboarding_step >= 4,
            "path": "/templates",
        },
    ]
    completed_count = sum(1 for s in steps if s["done"])
    return {
        "completed": user.onboarding_completed,
        "current_step": user.onboarding_step,
        "total_steps": TOTAL_STEPS,
        "completed_count": completed_count,
        "steps": steps,
    }
