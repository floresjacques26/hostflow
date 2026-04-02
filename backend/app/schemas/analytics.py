from pydantic import BaseModel
from typing import List


class FunnelMetrics(BaseModel):
    total_users: int
    activated_users: int                # onboarding_step >= 2
    trial_users: int
    paying_users: int                   # subscription_status = active
    activation_rate_pct: float          # activated / total * 100
    trial_conversion_rate_pct: float    # paying / trial * 100


class DashboardStats(BaseModel):
    """Per-user value stats shown in the Dashboard."""
    ai_responses_month: int
    ai_responses_total: int
    minutes_saved_month: int            # responses * 2
    minutes_saved_total: int
    properties_count: int
    is_activated: bool
    trial_days_remaining: int


class EventFrequency(BaseModel):
    """Count of a single event type across all users."""
    event_name: str
    count: int


class DailyCount(BaseModel):
    """Count of an event or action on a given date (YYYY-MM-DD)."""
    date: str
    count: int


class EventStatsOut(BaseModel):
    """Admin-only: top events + daily signup/activation series."""
    top_events: List[EventFrequency]
    daily_signups: List[DailyCount]     # last 30 days
    daily_activations: List[DailyCount] # last 30 days (first generated_response per user)


class EmailStatEntry(BaseModel):
    email_type: str
    sent: int
    failed: int


class EmailStatsOut(BaseModel):
    """Admin-only: outbound lifecycle email performance."""
    by_type: List[EmailStatEntry]
    total_sent: int
    total_failed: int
