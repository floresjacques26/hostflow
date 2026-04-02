from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.property import Property
from app.schemas.template import CalculatorRequest, CalculatorResponse
from app.services.onboarding_service import advance_onboarding
from app.services import event_service

router = APIRouter(prefix="/calculator", tags=["calculator"])


def _compute(
    daily_rate: float,
    half_day_rate: float,
    check_in: str,
    check_out: str,
    property_name: str | None,
    early_policy: str | None,
    late_policy: str | None,
) -> CalculatorResponse:
    hourly = daily_rate / 12

    early_msg = (
        early_policy
        or (
            f"Olá! Verificamos a disponibilidade para early check-in.\n"
            f"Conseguimos liberar o imóvel antes das {check_in} mediante pagamento de "
            f"meia diária (R$ {half_day_rate:.2f}) se disponível, ou da diária anterior completa "
            f"(R$ {daily_rate:.2f}). Como prefere prosseguir?"
        )
    )

    late_msg = (
        late_policy
        or (
            f"Olá! Sobre o late check-out:\n"
            f"• Até 15h: meia diária (R$ {half_day_rate:.2f})\n"
            f"• Até 18h: diária completa (R$ {daily_rate:.2f})\n"
            f"Sujeito à disponibilidade. Confirma o interesse?"
        )
    )

    return CalculatorResponse(
        property_name=property_name,
        daily_rate=daily_rate,
        half_day_rate=half_day_rate,
        early_checkin_half=half_day_rate,
        early_checkin_full=daily_rate,
        late_checkout_half=half_day_rate,
        late_checkout_full=daily_rate,
        hourly_rate=round(hourly, 2),
        check_in_time=check_in,
        check_out_time=check_out,
        early_checkin_message=early_msg,
        late_checkout_message=late_msg,
    )


@router.post("/", response_model=CalculatorResponse)
async def calculate(
    payload: CalculatorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.property_id:
        result = await db.execute(
            select(Property).where(
                Property.id == payload.property_id,
                Property.user_id == current_user.id,
            )
        )
        prop = result.scalar_one_or_none()
        if not prop:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado")

        daily_rate = float(prop.daily_rate or 0)
        if daily_rate == 0:
            if not payload.daily_rate:
                raise HTTPException(
                    status_code=400,
                    detail="Este imóvel não tem valor de diária cadastrado. Informe o valor manualmente.",
                )
            daily_rate = payload.daily_rate

        half_day = float(prop.half_day_rate) if prop.half_day_rate else daily_rate / 2

        result_data = _compute(
            daily_rate=daily_rate,
            half_day_rate=half_day,
            check_in=prop.check_in_time,
            check_out=prop.check_out_time,
            property_name=prop.name,
            early_policy=prop.early_checkin_policy,
            late_policy=prop.late_checkout_policy,
        )
        await event_service.track(current_user, event_service.USED_CALCULATOR, db, metadata={"property_id": prop.id})
        await advance_onboarding(current_user, "calculator", db)
        await db.commit()
        return result_data

    # Manual mode — no property selected
    if not payload.daily_rate:
        raise HTTPException(
            status_code=400,
            detail="Informe o valor da diária ou selecione um imóvel.",
        )

    r = payload.daily_rate
    result_data = _compute(
        daily_rate=r,
        half_day_rate=r / 2,
        check_in="14:00",
        check_out="11:00",
        property_name=None,
        early_policy=None,
        late_policy=None,
    )
    await event_service.track(current_user, event_service.USED_CALCULATOR, db, metadata={"manual_rate": r})
    await advance_onboarding(current_user, "calculator", db)
    await db.commit()
    return result_data
