"""
Stripe webhook endpoint.
Must use raw body — do NOT use Pydantic parsing here.
"""
import stripe
import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.billing_service import sync_subscription, handle_subscription_deleted
from app.services import lifecycle_service
from app.services import referral_service
from sqlalchemy import select
from app.models.user import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

HANDLED_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
}


@router.post("/stripe", include_in_schema=False)
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook secret not configured — skipping signature check")
        try:
            event = stripe.Event.construct_from(
                stripe.util.convert_to_stripe_object(
                    stripe.util.json.loads(payload), None, None
                ),
                stripe.api_key,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    if event_type not in HANDLED_EVENTS:
        return {"received": True, "processed": False}

    logger.info("Processing Stripe event: %s", event_type)

    async with AsyncSessionLocal() as db:
        try:
            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                sub_id = session.get("subscription")
                if sub_id:
                    sub = stripe.Subscription.retrieve(sub_id)
                    await sync_subscription(sub, db)
                    # upgrade confirmation — fetch user after sync
                    user = await _user_for_subscription(sub, db)
                    if user:
                        await lifecycle_service.send_upgrade_confirmation(user, db)

            elif event_type == "customer.subscription.created":
                sub = event["data"]["object"]
                await sync_subscription(sub, db)
                # trial_started is triggered from /billing/start-trial (no-card flow)
                # For Stripe-created subscriptions with trial, send it here too
                if sub.get("status") == "trialing":
                    user = await _user_for_subscription(sub, db)
                    if user:
                        await lifecycle_service.send_trial_started(user, db)

            elif event_type == "customer.subscription.updated":
                sub = event["data"]["object"]
                previous = event["data"].get("previous_attributes", {})
                await sync_subscription(sub, db)

                # Detect trial → active transition (upgrade)
                prev_status = previous.get("status")
                new_status = sub.get("status")
                if prev_status == "trialing" and new_status == "active":
                    user = await _user_for_subscription(sub, db)
                    if user:
                        await lifecycle_service.send_upgrade_confirmation(user, db)
                        await referral_service.maybe_reward_referrer(user, db)

            elif event_type == "customer.subscription.deleted":
                sub = event["data"]["object"]
                user = await _user_for_subscription(sub, db)
                await handle_subscription_deleted(sub, db)
                if user:
                    await lifecycle_service.send_subscription_canceled(user, db)

            elif event_type == "invoice.paid":
                invoice = event["data"]["object"]
                sub_id = invoice.get("subscription")
                if sub_id:
                    sub = stripe.Subscription.retrieve(sub_id)
                    await sync_subscription(sub, db)

            elif event_type == "invoice.payment_failed":
                invoice = event["data"]["object"]
                sub_id = invoice.get("subscription")
                if sub_id:
                    sub = stripe.Subscription.retrieve(sub_id)
                    await sync_subscription(sub, db)
                    user = await _user_for_subscription(sub, db)
                    if user:
                        await lifecycle_service.send_payment_failed(user, db)

        except Exception as e:
            logger.exception("Error processing webhook event %s: %s", event_type, e)
            return {"received": True, "processed": False, "error": str(e)}

    return {"received": True, "processed": True}


async def _user_for_subscription(sub: stripe.Subscription, db) -> User | None:
    """Look up the User for a Stripe subscription object."""
    customer_id = sub["customer"] if isinstance(sub, dict) else sub.get("customer")
    if not customer_id:
        return None
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    return result.scalar_one_or_none()
