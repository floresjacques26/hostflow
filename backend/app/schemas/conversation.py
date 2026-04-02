from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.property import PropertySummary


class MessageRequest(BaseModel):
    guest_message: str
    property_id: Optional[int] = None   # preferred over daily_rate when set
    daily_rate: Optional[float] = None  # fallback when no property selected


class MessageResponse(BaseModel):
    ai_response: str
    context: Optional[str] = None
    conversation_id: int


class ConversationOut(BaseModel):
    id: int
    guest_message: str
    ai_response: str
    context: Optional[str]
    property_id: Optional[int]
    property: Optional[PropertySummary]
    created_at: datetime

    model_config = {"from_attributes": True}
