from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Channel schemas ──────────────────────────────────────────────────────────

class ChannelCreate(BaseModel):
    type: str = "manual"
    name: str
    property_id: Optional[int] = None
    external_id: Optional[str] = None
    config_json: Optional[dict] = None


class ChannelOut(BaseModel):
    id: int
    type: str
    name: str
    property_id: Optional[int]
    external_id: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Entry schemas ─────────────────────────────────────────────────────────────

class MediaAttachmentOut(BaseModel):
    id: int
    media_type: str
    mime_type: Optional[str]
    file_name: Optional[str]
    external_media_id: Optional[str]
    file_size: Optional[int]
    storage_key: Optional[str]
    public_url: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EntryOut(BaseModel):
    id: int
    direction: str   # inbound | outbound | ai_draft | note
    body: str
    sender_name: Optional[str]
    external_message_id: Optional[str] = None
    sent_via_provider: bool = False
    delivery_status: Optional[str] = None
    is_template_message: bool = False
    template_name: Optional[str] = None
    created_at: datetime
    attachments: List["MediaAttachmentOut"] = []

    model_config = {"from_attributes": True}


class EntryCreate(BaseModel):
    direction: str = Field(..., pattern="^(outbound|note)$")
    body: str = Field(..., min_length=1, max_length=5000)
    sender_name: Optional[str] = None


# ── Thread schemas ────────────────────────────────────────────────────────────

class ThreadCreate(BaseModel):
    guest_message: str = Field(..., min_length=1, max_length=5000)
    guest_name: Optional[str] = None
    guest_contact: Optional[str] = None
    subject: Optional[str] = None
    property_id: Optional[int] = None
    channel_id: Optional[int] = None
    source_type: str = "manual"
    tags: Optional[str] = None


class ThreadUpdate(BaseModel):
    status: Optional[str] = None
    property_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_contact: Optional[str] = None
    subject: Optional[str] = None
    detected_context: Optional[str] = None
    tags: Optional[str] = None
    draft_status: Optional[str] = None


class PropertyBrief(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class ChannelBrief(BaseModel):
    id: int
    type: str
    name: str
    model_config = {"from_attributes": True}


class ThreadOut(BaseModel):
    id: int
    subject: Optional[str]
    guest_name: Optional[str]
    guest_contact: Optional[str]
    source_type: str
    status: str
    detected_context: Optional[str]
    draft_status: str
    tags: Optional[str]
    guest_profile_id: Optional[int] = None
    property: Optional[PropertyBrief]
    channel: Optional[ChannelBrief]
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # SLA computed fields — derived from model @property
    is_overdue: bool = False
    is_stale: bool = False
    # External provider sync fields
    external_thread_id: Optional[str] = None
    sync_status: str = "none"
    last_synced_at: Optional[datetime] = None
    # Template matching fields
    applied_template_id: Optional[int] = None
    template_auto_applied: bool = False
    # Auto-send decision: sent | blocked | manual_review | None
    auto_send_decision: Optional[str] = None
    # WhatsApp 24-hour service window (computed @property on model)
    wa_window_open: bool = True
    last_inbound_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ThreadDetailOut(ThreadOut):
    entries: List[EntryOut] = []


# ── Bulk action ───────────────────────────────────────────────────────────────

class BulkActionRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1, max_length=200)
    action: str = Field(..., pattern="^(resolve|archive|pending|open)$")
