from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CheckoutRequest(BaseModel):
    price_id: str       # Stripe price ID


class PortalRequest(BaseModel):
    return_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionOut(BaseModel):
    plan: str
    effective_plan: str
    subscription_status: str
    is_trial_active: bool
    trial_ends_at: Optional[datetime]
    current_period_end: Optional[datetime]
    canceled_at: Optional[datetime]
    stripe_subscription_id: Optional[str]

    model_config = {"from_attributes": True}


class UsageSummaryOut(BaseModel):
    month: str
    ai_responses: int
    ai_responses_limit: Optional[int]   # None = unlimited
    properties_count: int
    properties_limit: Optional[int]
    custom_templates_count: int
    custom_templates_limit: Optional[int]
    plan: str
    effective_plan: str


class PlanOut(BaseModel):
    name: str
    display_name: str
    max_properties: Optional[int]
    max_ai_responses_per_month: Optional[int]
    max_custom_templates: Optional[int]
    has_full_history: bool
    has_advanced_analytics: bool
    trial_days: int
    price_id: Optional[str]             # Stripe price ID (None when not configured)
    price_brl: Optional[int]            # Display price in BRL cents (None = free)
