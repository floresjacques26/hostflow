from pydantic import BaseModel
from typing import List


class OnboardingStep(BaseModel):
    key: str
    step: int
    title: str
    description: str
    done: bool
    path: str


class OnboardingState(BaseModel):
    completed: bool
    current_step: int
    total_steps: int
    completed_count: int
    steps: List[OnboardingStep]


class SkipOnboardingRequest(BaseModel):
    reason: str = "user_skipped"
