from openai import AsyncOpenAI
from app.core.config import settings
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.property import Property

client = AsyncOpenAI(api_key=settings.openai_api_key)

_BASE_DIRECTIVES = """
Diretrizes de comunicação:
- Tom: educado, firme, direto e profissional
- Responda SEMPRE em português brasileiro
- Seja simpático mas claro quanto às regras
- Não prometa flexibilidade que não existe
- Se o hóspede pedir algo fora das regras, recuse com educação e ofereça alternativas
- Mensagens devem ser concisas (máximo 150 palavras)
- Use "Olá!" como abertura quando apropriado

Contextos comuns:
- Pedido de early check-in: explique a política e o custo
- Pedido de late check-out: explique a política e o custo
- Problema com equipamento (descarga, cozinha, etc): seja empático, peça foto/vídeo e acione manutenção
- Dúvidas sobre regras da casa: seja claro e objetivo
- Reclamações: ouça com empatia, ofereça solução prática

Identifique o contexto da mensagem e responda de forma adequada."""


def _build_system_prompt(property: Optional["Property"] = None, daily_rate: Optional[float] = None) -> str:
    if property is not None:
        # Build rich context from the actual property
        check_in = property.check_in_time
        check_out = property.check_out_time
        rate = float(property.daily_rate) if property.daily_rate else daily_rate
        half_rate = float(property.half_day_rate) if property.half_day_rate else (rate / 2 if rate else None)

        early_policy = property.early_checkin_policy or (
            f"Disponível mediante pagamento de meia diária (R$ {half_rate:.2f}) ou da diária anterior completa (R$ {rate:.2f})"
            if rate and half_rate else "Disponível mediante pagamento de meia diária ou da diária anterior completa"
        )
        late_policy = property.late_checkout_policy or (
            f"Até 15h: meia diária (R$ {half_rate:.2f}). Até 18h: diária completa (R$ {rate:.2f})"
            if rate and half_rate else "Até 15h: meia diária. Até 18h: diária completa"
        )

        rules_section = f"\nRegras gerais da casa:\n{property.house_rules}" if property.house_rules else ""
        pet_section = f"\nPolítica pet: {'Aceita animais de estimação.' if property.accepts_pets else 'Não aceita animais de estimação.'}"
        parking_section = (
            f"\nEstacionamento: {property.parking_policy}"
            if property.has_parking and property.parking_policy
            else ("\nEstacionamento disponível." if property.has_parking else "")
        )
        rate_section = (
            f"\n- Valor da diária: R$ {rate:.2f}"
            f"\n- Meia diária: R$ {half_rate:.2f}"
        ) if rate and half_rate else ""

        property_block = f"""Você é um assistente especializado em atendimento para anfitriões do Airbnb e guest houses no Brasil.

Dados do imóvel: {property.name} ({property.type})
Regras da propriedade:
- Check-in: {check_in}
- Check-out: {check_out}
- Early check-in (antes das {check_in}): {early_policy}
- Late check-out (após {check_out}): {late_policy}{rate_section}{pet_section}{parking_section}{rules_section}
- Pagamentos extras combinados diretamente com o anfitrião"""

        return property_block + _BASE_DIRECTIVES

    # Fallback: generic default rules
    rate_section = ""
    if daily_rate:
        half = daily_rate / 2
        rate_section = f"\n- Valor da diária: R$ {daily_rate:.2f}\n- Meia diária: R$ {half:.2f}"

    return f"""Você é um assistente especializado em atendimento para anfitriões do Airbnb e guest houses no Brasil.

Regras da propriedade (padrão):
- Check-in: 14:00
- Check-out: 11:00
- Early check-in: necessário reservar a diária anterior OU pagar meia diária se disponível
- Late check-out: meia diária (até 15h) ou diária completa (após 15h){rate_section}
- Pagamentos extras combinados diretamente com o anfitrião""" + _BASE_DIRECTIVES


async def generate_response(
    guest_message: str,
    property: Optional["Property"] = None,
    daily_rate: Optional[float] = None,
    template_hint: Optional[str] = None,
) -> tuple[str, str]:
    """
    Returns (ai_response, detected_context).
    context: checkin | checkout | complaint | question | charge | other

    template_hint: optional template content to use as structured grounding.
    When provided, the AI adapts the template to the specific guest message
    rather than generating a response from scratch.
    """
    system_prompt = _build_system_prompt(property=property, daily_rate=daily_rate)

    if template_hint:
        user_content = (
            f"Mensagem do hóspede:\n{guest_message}\n\n"
            f"Use o template abaixo como base para sua resposta. "
            f"Adapte-o naturalmente à mensagem do hóspede, personalizando o tom e os detalhes conforme necessário. "
            f"Não copie o template literalmente — use-o como guia estrutural.\n\n"
            f"Template de referência:\n---\n{template_hint}\n---\n\n"
            "Na última linha escreva APENAS o contexto detectado "
            "em formato: CONTEXTO: [checkin|checkout|complaint|question|charge|other]"
        )
    else:
        user_content = (
            f"Mensagem do hóspede:\n{guest_message}\n\n"
            "Responda à mensagem acima e na última linha escreva APENAS o contexto detectado "
            "em formato: CONTEXTO: [checkin|checkout|complaint|question|charge|other]"
        )

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=400,
    )

    full_text = response.choices[0].message.content.strip()

    context = "other"
    lines = full_text.splitlines()
    if lines and lines[-1].startswith("CONTEXTO:"):
        context_raw = lines[-1].replace("CONTEXTO:", "").strip().lower()
        valid = {"checkin", "checkout", "complaint", "question", "charge", "other"}
        context = context_raw if context_raw in valid else "other"
        ai_response = "\n".join(lines[:-1]).strip()
    else:
        ai_response = full_text

    return ai_response, context
