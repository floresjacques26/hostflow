from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    plan: str
    effective_plan: str
    subscription_status: str
    is_trial_active: bool
    trial_days_remaining: int
    trial_ends_at: Optional[datetime]
    current_period_end: Optional[datetime]
    onboarding_completed: bool
    onboarding_step: int
    is_admin: bool
    referral_code: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
