"""Stripe billing operations."""
import stripe
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.plans import PLANS
from app.models.user import User

stripe.api_key = settings.stripe_secret_key
logger = logging.getLogger(__name__)

# Map Stripe price IDs → internal plan names
def _price_to_plan(price_id: str) -> str:
    mapping = {
        settings.stripe_price_pro_monthly: "pro",
        settings.stripe_price_business_monthly: "business",
    }
    return mapping.get(price_id, "free")


async def get_or_create_customer(user: User, db: AsyncSession) -> str:
    """Return existing Stripe customer ID or create a new one."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


async def create_checkout_session(
    user: User,
    price_id: str,
    success_url: str,
    cancel_url: str,
    db: AsyncSession,
) -> str:
    """Create a Stripe Checkout Session and return the URL."""
    customer_id = await get_or_create_customer(user, db)
    plan_name = _price_to_plan(price_id)
    trial_days = PLANS[plan_name].trial_days if plan_name in PLANS else 0

    params: dict = {
        "customer": customer_id,
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"user_id": str(user.id)},
    }
    # Only offer trial if user never had one (no prior subscription)
    if trial_days > 0 and not user.stripe_subscription_id:
        params["subscription_data"] = {"trial_period_days": trial_days}

    session = stripe.checkout.Session.create(**params)
    return session.url


async def create_portal_session(user: User, return_url: str, db: AsyncSession) -> str:
    """Create a Stripe Customer Portal session and return the URL."""
    customer_id = await get_or_create_customer(user, db)
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.utcfromtimestamp(ts)


async def sync_subscription(sub: stripe.Subscription, db: AsyncSession) -> None:
    """
    Sync a Stripe subscription object to our database.
    Called from webhook handlers and after checkout completion.
    """
    customer_id = sub["customer"]
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("sync_subscription: no user found for customer %s", customer_id)
        return

    price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
    plan_name = _price_to_plan(price_id) if price_id else "free"
    status = sub["status"]  # trialing | active | past_due | canceled | unpaid | incomplete

    user.stripe_subscription_id = sub["id"]
    user.stripe_price_id = price_id
    user.plan = plan_name if status in ("trialing", "active", "past_due") else "free"
    user.subscription_status = status
    user.current_period_end = _ts_to_dt(sub.get("current_period_end"))
    user.trial_ends_at = _ts_to_dt(sub.get("trial_end"))
    user.canceled_at = _ts_to_dt(sub.get("canceled_at"))

    await db.commit()
    logger.info("synced subscription %s → user %s, plan=%s, status=%s", sub["id"], user.id, plan_name, status)


async def handle_subscription_deleted(sub: stripe.Subscription, db: AsyncSession) -> None:
    customer_id = sub["customer"]
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.plan = "free"
    user.subscription_status = "canceled"
    user.stripe_subscription_id = None
    user.stripe_price_id = None
    user.current_period_end = _ts_to_dt(sub.get("current_period_end"))
    user.canceled_at = _ts_to_dt(sub.get("canceled_at")) or datetime.utcnow()
    await db.commit()
    logger.info("subscription deleted for user %s, reverted to free", user.id)
