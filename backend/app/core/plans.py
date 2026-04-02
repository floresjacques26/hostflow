"""
Central plan configuration.
All limits and features live here — never hardcoded elsewhere.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PlanConfig:
    name: str
    display_name: str
    max_properties: Optional[int]       # None = unlimited
    max_ai_responses_per_month: Optional[int]  # None = unlimited
    max_custom_templates: Optional[int]  # None = unlimited
    has_full_history: bool
    has_advanced_analytics: bool
    trial_days: int = 0


PLANS: dict[str, PlanConfig] = {
    "free": PlanConfig(
        name="free",
        display_name="Free",
        max_properties=1,
        max_ai_responses_per_month=20,
        max_custom_templates=3,
        has_full_history=False,
        has_advanced_analytics=False,
    ),
    "pro": PlanConfig(
        name="pro",
        display_name="Pro",
        max_properties=5,
        max_ai_responses_per_month=500,
        max_custom_templates=None,
        has_full_history=True,
        has_advanced_analytics=False,
        trial_days=14,
    ),
    "business": PlanConfig(
        name="business",
        display_name="Business",
        max_properties=None,
        max_ai_responses_per_month=None,
        max_custom_templates=None,
        has_full_history=True,
        has_advanced_analytics=True,
    ),
}


def get_plan(plan_name: str) -> PlanConfig:
    return PLANS.get(plan_name, PLANS["free"])


def is_within_property_limit(plan_name: str, current_count: int) -> bool:
    plan = get_plan(plan_name)
    if plan.max_properties is None:
        return True
    return current_count < plan.max_properties


def is_within_response_limit(plan_name: str, monthly_count: int) -> bool:
    plan = get_plan(plan_name)
    if plan.max_ai_responses_per_month is None:
        return True
    return monthly_count < plan.max_ai_responses_per_month


def is_within_template_limit(plan_name: str, current_count: int) -> bool:
    plan = get_plan(plan_name)
    if plan.max_custom_templates is None:
        return True
    return current_count < plan.max_custom_templates
