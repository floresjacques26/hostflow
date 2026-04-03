from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.core.config import settings
from app.core.plans import PLANS, get_plan
from app.models.user import User
from app.models.property import Property
from app.models.template import Template
from app.schemas.billing import (
    CheckoutRequest, CheckoutResponse,
    PortalRequest, PortalResponse,
    SubscriptionOut, UsageSummaryOut, PlanOut,
)
from app.services.billing_service import create_checkout_session, create_portal_session
from app.services.usage_service import get_usage_summary
from app.services import lifecycle_service
from app.services import referral_service
from typing import List
import stripe

router = APIRouter(prefix="/billing", tags=["billing"])


async def _bg_trial_started(user_id: int) -> None:
    """Send trial_started email with its own DB session."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            await lifecycle_service.send_trial_started(user, db)


@router.get("/plans", response_model=List[PlanOut])
async def list_plans():
    """Public endpoint — no auth required."""
    price_map = {
        "pro": settings.stripe_price_pro_monthly or None,
        "business": settings.stripe_price_business_monthly or None,
    }
    # BRL prices in cents, sourced from config (same values shown on pricing page)
    price_brl_map = {
        "free": None,
        "pro": settings.plan_price_pro_brl,
        "business": settings.plan_price_business_brl,
    }
    return [
        PlanOut(
            **{k: v for k, v in vars(plan).items()},
            price_id=price_map.get(plan.name),
            price_brl=price_brl_map.get(plan.name),
        )
        for plan in PLANS.values()
    ]


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(current_user: User = Depends(get_current_user)):
    return SubscriptionOut(
        plan=current_user.plan,
        effective_plan=current_user.effective_plan,
        subscription_status=current_user.subscription_status,
        is_trial_active=current_user.is_trial_active,
        trial_ends_at=current_user.trial_ends_at,
        current_period_end=current_user.current_period_end,
        canceled_at=current_user.canceled_at,
        stripe_subscription_id=current_user.stripe_subscription_id,
    )


@router.get("/usage", response_model=UsageSummaryOut)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    usage = await get_usage_summary(current_user.id, db)
    plan = get_plan(current_user.effective_plan)

    prop_count_result = await db.execute(
        select(func.count()).where(Property.user_id == current_user.id)
    )
    tmpl_count_result = await db.execute(
        select(func.count()).where(
            Template.user_id == current_user.id,
            Template.is_default == False,
        )
    )

    return UsageSummaryOut(
        month=usage["month"],
        ai_responses=usage["ai_responses"],
        ai_responses_limit=plan.max_ai_responses_per_month,
        properties_count=prop_count_result.scalar_one(),
        properties_limit=plan.max_properties,
        custom_templates_count=tmpl_count_result.scalar_one(),
        custom_templates_limit=plan.max_custom_templates,
        plan=current_user.plan,
        effective_plan=current_user.effective_plan,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _sk = settings.stripe_secret_key
    if not _sk or not _sk.startswith(("sk_test_", "sk_live_")) or len(_sk) < 30:
        raise HTTPException(status_code=503, detail="Stripe não configurado — adicione STRIPE_SECRET_KEY válida no .env")

    price_to_plan = {
        settings.stripe_price_pro_monthly: "pro",
        settings.stripe_price_business_monthly: "business",
    }
    if payload.price_id not in price_to_plan:
        raise HTTPException(status_code=400, detail="Plano inválido")

    plan_name = price_to_plan[payload.price_id]

    try:
        url = await create_checkout_session(
            user=current_user,
            price_id=payload.price_id,
            # Redirect to the dedicated success page with the plan name so the
            # frontend can show the right congratulatory message.
            success_url=f"{settings.frontend_url}/checkout/success?plan={plan_name}",
            cancel_url=f"{settings.frontend_url}/billing?canceled=1",
            db=db,
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Erro Stripe: {e.user_message}")

    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def open_portal(
    payload: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Sem assinatura ativa para gerenciar")

    try:
        url = await create_portal_session(
            user=current_user,
            return_url=payload.return_url,
            db=db,
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Erro Stripe: {e.user_message}")

    return PortalResponse(portal_url=url)


@router.post("/start-trial", response_model=SubscriptionOut)
async def start_trial(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Starts a free trial without requiring a credit card.
    Only allowed if user never had a subscription before.
    """
    if current_user.stripe_subscription_id or current_user.subscription_status != "free":
        raise HTTPException(status_code=400, detail="Você já utilizou ou tem uma assinatura ativa")

    trial_days = PLANS["pro"].trial_days
    trial_end = datetime.utcnow() + timedelta(days=trial_days)

    current_user.plan = "pro"
    current_user.subscription_status = "trialing"
    current_user.trial_ends_at = trial_end

    # Reward the referrer if this user was referred
    await referral_service.maybe_reward_referrer(current_user, db)

    await db.commit()

    background_tasks.add_task(_bg_trial_started, current_user.id)

    return SubscriptionOut(
        plan=current_user.plan,
        effective_plan=current_user.effective_plan,
        subscription_status=current_user.subscription_status,
        is_trial_active=current_user.is_trial_active,
        trial_ends_at=current_user.trial_ends_at,
        current_period_end=current_user.current_period_end,
        canceled_at=current_user.canceled_at,
        stripe_subscription_id=current_user.stripe_subscription_id,
    )
