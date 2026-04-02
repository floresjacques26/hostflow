"""
Reusable plan-limit guards.
Raise HTTP 402 with a structured payload when a limit is exceeded.
The frontend interprets 402 to show upgrade CTAs.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.plans import get_plan, is_within_property_limit, is_within_response_limit, is_within_template_limit
from app.models.user import User
from app.models.property import Property
from app.models.template import Template
from app.services.usage_service import get_monthly_usage


def _upgrade_error(code: str, message: str, upgrade_to: str = "pro") -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "code": code,
            "message": message,
            "upgrade_to": upgrade_to,
        },
    )


async def guard_property_limit(user: User, db: AsyncSession) -> None:
    """Raise 402 if user is at their property limit."""
    plan_name = user.effective_plan
    plan = get_plan(plan_name)
    if plan.max_properties is None:
        return

    result = await db.execute(
        select(func.count()).where(Property.user_id == user.id)
    )
    count = result.scalar_one()

    if not is_within_property_limit(plan_name, count):
        upgrade_to = "pro" if plan_name == "free" else "business"
        raise _upgrade_error(
            code="PROPERTY_LIMIT_REACHED",
            message=(
                f"Você atingiu o limite de {plan.max_properties} imóve{'l' if plan.max_properties == 1 else 'is'} "
                f"do plano {plan.display_name}. "
                f"Faça upgrade para cadastrar mais imóveis."
            ),
            upgrade_to=upgrade_to,
        )


async def guard_ai_response_limit(user: User, db: AsyncSession) -> None:
    """Raise 402 if user is at their monthly AI response limit."""
    plan_name = user.effective_plan
    plan = get_plan(plan_name)
    if plan.max_ai_responses_per_month is None:
        return

    count = await get_monthly_usage(user.id, db)
    if not is_within_response_limit(plan_name, count):
        upgrade_to = "pro" if plan_name == "free" else "business"
        raise _upgrade_error(
            code="AI_RESPONSE_LIMIT_REACHED",
            message=(
                f"Você atingiu o limite de {plan.max_ai_responses_per_month} respostas por mês "
                f"do plano {plan.display_name}. "
                f"Faça upgrade para continuar usando a IA sem interrupções."
            ),
            upgrade_to=upgrade_to,
        )


async def guard_template_limit(user: User, db: AsyncSession) -> None:
    """Raise 402 if user is at their custom template limit."""
    plan_name = user.effective_plan
    plan = get_plan(plan_name)
    if plan.max_custom_templates is None:
        return

    result = await db.execute(
        select(func.count()).where(
            Template.user_id == user.id,
            Template.is_default == False,
        )
    )
    count = result.scalar_one()

    if not is_within_template_limit(plan_name, count):
        upgrade_to = "pro" if plan_name == "free" else "business"
        raise _upgrade_error(
            code="TEMPLATE_LIMIT_REACHED",
            message=(
                f"Você atingiu o limite de {plan.max_custom_templates} templates personalizados "
                f"do plano {plan.display_name}. Faça upgrade para criar templates ilimitados."
            ),
            upgrade_to=upgrade_to,
        )
