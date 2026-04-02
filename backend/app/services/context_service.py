"""
Fast context classification for inbound guest messages.
Uses a dedicated, cheap OpenAI call with zero temperature.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

CONTEXT_TYPES = {
    "early_checkin", "late_checkout", "address", "parking", "pets",
    "house_rules", "pricing", "availability", "cancellation", "amenities",
    "complaint", "checkin", "checkout", "question", "charge", "general",
}

CONTEXT_LABELS = {
    "early_checkin":  "Check-in antecipado",
    "late_checkout":  "Check-out tardio",
    "address":        "Endereço",
    "parking":        "Estacionamento",
    "pets":           "Animais",
    "house_rules":    "Regras da casa",
    "pricing":        "Preços",
    "availability":   "Disponibilidade",
    "cancellation":   "Cancelamento",
    "amenities":      "Comodidades",
    "complaint":      "Reclamação",
    "checkin":        "Check-in",
    "checkout":       "Check-out",
    "question":       "Dúvida",
    "charge":         "Cobrança",
    "general":        "Geral",
}

_CLASSIFIER_SYSTEM = (
    "You classify guest messages for short-term rental properties. "
    "Return ONLY one word from this list — nothing else:\n"
    "early_checkin, late_checkout, address, parking, pets, house_rules, "
    "pricing, availability, cancellation, amenities, complaint, checkin, "
    "checkout, question, charge, general"
)


async def detect_context(message: str) -> str:
    """
    Classify a guest message into one of the known context types.
    Returns 'general' if classification fails or OpenAI is not configured.
    Never raises.
    """
    if not settings.openai_api_key or not message.strip():
        return "general"
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": message[:600]},
            ],
            max_tokens=10,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip().lower().replace(" ", "_").replace("-", "_")
        return raw if raw in CONTEXT_TYPES else "general"
    except Exception as exc:
        logger.warning("context_service.detect_context failed: %s", exc)
        return "general"
