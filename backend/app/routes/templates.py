from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.guards import guard_template_limit
from app.models.user import User
from app.models.property import Property
from app.models.template import Template
from app.models.thread import MessageThread
from app.schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateOut,
    TemplateSuggestion, ThreadTemplateSuggestions,
)
from app.services import template_match_service
from app.services.onboarding_service import advance_onboarding

router = APIRouter(prefix="/templates", tags=["templates"])

VALID_CONTEXT_KEYS = {
    "early_checkin", "late_checkout", "address", "parking", "pets",
    "house_rules", "pricing", "availability", "cancellation", "amenities",
    "complaint", "checkin", "checkout", "question", "charge", "general",
}
VALID_CHANNEL_TYPES = {"manual", "email_forward", "gmail", "whatsapp", "webhook"}
VALID_TONES = {"friendly", "formal", "brief"}
VALID_LANGUAGES = {"pt", "en", "es"}


async def _assert_property_owned(
    property_id: int | None, user_id: int, db: AsyncSession
) -> None:
    if property_id is None:
        return
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")


def _validate_smart_fields(payload: TemplateCreate | TemplateUpdate) -> None:
    if payload.context_key and payload.context_key not in VALID_CONTEXT_KEYS:
        raise HTTPException(status_code=400, detail=f"context_key inválido. Use: {', '.join(sorted(VALID_CONTEXT_KEYS))}")
    if payload.channel_type and payload.channel_type not in VALID_CHANNEL_TYPES:
        raise HTTPException(status_code=400, detail=f"channel_type inválido. Use: {', '.join(VALID_CHANNEL_TYPES)}")
    if payload.tone and payload.tone not in VALID_TONES:
        raise HTTPException(status_code=400, detail=f"tone inválido. Use: {', '.join(VALID_TONES)}")
    if payload.language and payload.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"language inválido. Use: {', '.join(VALID_LANGUAGES)}")


@router.get("/", response_model=List[TemplateOut])
async def list_templates(
    property_id: Optional[int] = None,
    context_key: Optional[str] = None,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns system defaults + user's global templates + property-specific templates.
    Optionally filter by property_id, context_key, or active status.
    """
    conditions = [Template.is_default == True]  # noqa: E712
    conditions.append(
        and_(Template.user_id == current_user.id, Template.property_id == None)  # noqa: E711
    )
    if property_id is not None:
        conditions.append(
            and_(Template.user_id == current_user.id, Template.property_id == property_id)
        )

    query = select(Template).where(or_(*conditions))
    if active_only:
        query = query.where(Template.active == True)  # noqa: E712
    if context_key:
        query = query.where(Template.context_key == context_key)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=TemplateOut, status_code=201)
async def create_template(
    payload: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await guard_template_limit(current_user, db)
    await _assert_property_owned(payload.property_id, current_user.id, db)
    _validate_smart_fields(payload)

    # Check if this is the user's first custom (non-default) template
    count_result = await db.execute(
        select(func.count()).where(
            Template.user_id == current_user.id,
            Template.is_default == False,  # noqa: E712
        )
    )
    is_first_template = count_result.scalar() == 0

    template = Template(**payload.model_dump(), user_id=current_user.id)
    db.add(template)

    if is_first_template:
        await advance_onboarding(current_user, "template", db)

    await db.commit()
    await db.refresh(template)
    return template


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    payload: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.user_id == current_user.id,
            Template.is_default == False,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    if payload.property_id is not None:
        await _assert_property_owned(payload.property_id, current_user.id, db)
    _validate_smart_fields(payload)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.user_id == current_user.id,
            Template.is_default == False,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado ou protegido")

    await db.delete(template)
    await db.commit()


@router.get("/suggest", response_model=ThreadTemplateSuggestions)
async def suggest_templates(
    thread_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return ranked template suggestions for a specific inbox thread.
    Used by the draft panel to show which templates match the conversation.
    """
    result = await db.execute(
        select(MessageThread)
        .options(selectinload(MessageThread.entries))
        .where(MessageThread.id == thread_id, MessageThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    matches = await template_match_service.get_suggestions(thread, current_user.id, db, limit=6)

    # Find the auto-apply candidate
    auto_match = next(
        (m for m in matches if m.template.auto_apply and m.is_context_specific),
        None,
    )

    def to_suggestion(m: template_match_service.TemplateMatch, is_auto: bool = False) -> TemplateSuggestion:
        return TemplateSuggestion(
            template=TemplateOut.model_validate(m.template),
            score=m.score,
            match_label=m.match_label,
            is_context_specific=m.is_context_specific,
            auto_applied=is_auto,
        )

    best = to_suggestion(matches[0], auto_match is not None and matches[0].template.id == auto_match.template.id) if matches else None

    return ThreadTemplateSuggestions(
        thread_id=thread_id,
        detected_context=thread.detected_context,
        best_match=best,
        suggestions=[to_suggestion(m) for m in matches],
    )
