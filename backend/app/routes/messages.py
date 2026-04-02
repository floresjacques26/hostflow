from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.guards import guard_ai_response_limit
from app.models.user import User
from app.models.conversation import Conversation
from app.models.property import Property
from app.schemas.conversation import MessageRequest, MessageResponse, ConversationOut
from app.services.ai_service import generate_response
from app.services.usage_service import increment_ai_response
from app.services.onboarding_service import advance_onboarding
from app.services import event_service
from typing import List

router = APIRouter(prefix="/messages", tags=["messages"])


async def _resolve_property(
    property_id: int | None, user_id: int, db: AsyncSession
) -> Property | None:
    if property_id is None:
        return None
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.user_id == user_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return prop


@router.post("/generate", response_model=MessageResponse)
async def generate(
    payload: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.guest_message.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode estar vazia")

    try:
        await guard_ai_response_limit(current_user, db)
    except HTTPException as guard_exc:
        if guard_exc.status_code == 402:
            await event_service.track(current_user, event_service.HIT_USAGE_LIMIT, db,
                                      metadata={"plan": current_user.effective_plan})
            await db.commit()
        raise

    prop = await _resolve_property(payload.property_id, current_user.id, db)

    try:
        ai_response, context = await generate_response(
            guest_message=payload.guest_message,
            property=prop,
            daily_rate=payload.daily_rate,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar IA: {str(e)}")

    conversation = Conversation(
        user_id=current_user.id,
        property_id=prop.id if prop else None,
        guest_message=payload.guest_message,
        ai_response=ai_response,
        context=context,
    )
    db.add(conversation)

    await event_service.track(
        current_user, event_service.GENERATED_RESPONSE, db,
        metadata={"context": context, "property_id": prop.id if prop else None},
    )
    await advance_onboarding(current_user, "ai_response", db)

    await db.commit()
    await db.refresh(conversation)
    await increment_ai_response(current_user.id, db)

    return MessageResponse(
        ai_response=ai_response,
        context=context,
        conversation_id=conversation.id,
    )


@router.get("/history", response_model=List[ConversationOut])
async def history(
    limit: int = 20,
    offset: int = 0,
    property_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Conversation)
        .options(selectinload(Conversation.property))
        .where(Conversation.user_id == current_user.id)
    )
    if property_id is not None:
        query = query.where(Conversation.property_id == property_id)

    query = query.order_by(desc(Conversation.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    await db.delete(conv)
    await db.commit()
