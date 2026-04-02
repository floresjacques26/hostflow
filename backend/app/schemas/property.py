from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
from decimal import Decimal
import re

PROPERTY_TYPES = ["guest_house", "quarto_privativo", "apartamento", "casa", "studio", "kitnet"]
TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class PropertyCreate(BaseModel):
    name: str
    type: str = "apartamento"
    address_label: Optional[str] = None
    check_in_time: str = "14:00"
    check_out_time: str = "11:00"
    daily_rate: Optional[Decimal] = None
    half_day_rate: Optional[Decimal] = None
    early_checkin_policy: Optional[str] = None
    late_checkout_policy: Optional[str] = None
    accepts_pets: bool = False
    has_parking: bool = False
    parking_policy: Optional[str] = None
    house_rules: Optional[str] = None

    @field_validator("check_in_time", "check_out_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not TIME_RE.match(v):
            raise ValueError("Formato de hora inválido. Use HH:MM (ex: 14:00)")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in PROPERTY_TYPES:
            raise ValueError(f"Tipo inválido. Opções: {', '.join(PROPERTY_TYPES)}")
        return v


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    address_label: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    daily_rate: Optional[Decimal] = None
    half_day_rate: Optional[Decimal] = None
    early_checkin_policy: Optional[str] = None
    late_checkout_policy: Optional[str] = None
    accepts_pets: Optional[bool] = None
    has_parking: Optional[bool] = None
    parking_policy: Optional[str] = None
    house_rules: Optional[str] = None

    @field_validator("check_in_time", "check_out_time", mode="before")
    @classmethod
    def validate_time(cls, v):
        if v is not None and not TIME_RE.match(str(v)):
            raise ValueError("Formato de hora inválido. Use HH:MM (ex: 14:00)")
        return v


class PropertyOut(BaseModel):
    id: int
    name: str
    type: str
    address_label: Optional[str]
    check_in_time: str
    check_out_time: str
    daily_rate: Optional[Decimal]
    half_day_rate: Optional[Decimal]
    early_checkin_policy: Optional[str]
    late_checkout_policy: Optional[str]
    accepts_pets: bool
    has_parking: bool
    parking_policy: Optional[str]
    house_rules: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertySummary(BaseModel):
    """Lightweight version for dropdowns."""
    id: int
    name: str
    type: str
    check_in_time: str
    check_out_time: str
    daily_rate: Optional[Decimal]

    model_config = {"from_attributes": True}
