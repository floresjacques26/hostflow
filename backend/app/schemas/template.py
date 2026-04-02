from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal


class TemplateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    category: str
    content: str = Field(..., min_length=1, max_length=5000)
    property_id: Optional[int] = None
    # Smart-match fields
    context_key: Optional[str] = None
    channel_type: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    priority: int = 0
    auto_apply: bool = False
    active: bool = True


class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    property_id: Optional[int] = None
    context_key: Optional[str] = None
    channel_type: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    priority: Optional[int] = None
    auto_apply: Optional[bool] = None
    active: Optional[bool] = None


class TemplateOut(BaseModel):
    id: int
    title: str
    category: str
    content: str
    is_default: bool
    property_id: Optional[int]
    context_key: Optional[str] = None
    channel_type: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    priority: int = 0
    auto_apply: bool = False
    active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateSuggestion(BaseModel):
    """A matched template with its score and reason, for the UI suggestion panel."""
    template: TemplateOut
    score: int
    match_label: str
    is_context_specific: bool
    auto_applied: bool = False


class ThreadTemplateSuggestions(BaseModel):
    """Response from GET /templates/suggest."""
    thread_id: int
    detected_context: Optional[str]
    best_match: Optional[TemplateSuggestion]
    suggestions: list[TemplateSuggestion]


# ── Calculator schemas ─────────────────────────────────────────────────────────

class CalculatorRequest(BaseModel):
    daily_rate: Optional[float] = None
    property_id: Optional[int] = None


class CalculatorResponse(BaseModel):
    property_name: Optional[str]
    daily_rate: float
    half_day_rate: float
    early_checkin_half: float
    early_checkin_full: float
    late_checkout_half: float
    late_checkout_full: float
    hourly_rate: float
    check_in_time: str
    check_out_time: str
    early_checkin_message: str
    late_checkout_message: str
