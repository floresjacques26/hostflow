"""
WhatsApp template message (HSM) sending service.

Meta requires pre-approved templates for:
  - Proactive outbound messages (no prior conversation)
  - Re-engaging contacts after the 24-hour customer service window

API reference:
  POST /{version}/{phone_number_id}/messages
  {
    "messaging_product": "whatsapp",
    "to": "<phone>",
    "type": "template",
    "template": {
      "name": "<template_name>",
      "language": {"code": "<language_code>"},
      "components": [
        {"type": "body", "parameters": [{"type": "text", "text": "value1"}, ...]}
      ]
    }
  }

Variable substitution:
  The caller provides a flat list of string values.
  They are injected as body parameters in order ({{1}}, {{2}}, …).
  Header/button parameters can be added in a future version.
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com"


async def send_template_message(
    phone_number_id: str,
    access_token: str,
    to_phone: str,
    template_name: str,
    language_code: str,
    variables: list[str] | None = None,
    api_version: str | None = None,
) -> dict:
    """
    Send an approved WhatsApp template message.

    Parameters
    ----------
    phone_number_id
        Meta phone_number_id for the sending account.
    access_token
        Decrypted permanent access token.
    to_phone
        Recipient's E.164 phone number.
    template_name
        Exact name as registered in Meta Business Manager.
    language_code
        BCP 47, e.g. 'pt_BR', 'en_US'.
    variables
        Ordered list of text values for body parameters ({{1}}, {{2}}, …).
    api_version
        Overrides settings.whatsapp_api_version.

    Returns
    -------
    dict
        Raw Meta API response.

    Raises
    ------
    RuntimeError
        On non-2xx response from Meta.
    """
    version = api_version or settings.whatsapp_api_version
    url = f"{META_API_BASE}/{version}/{phone_number_id}/messages"
    normalized = to_phone.lstrip("+")

    # Build body parameters from variables list
    body_parameters = [
        {"type": "text", "text": str(v)}
        for v in (variables or [])
    ]

    template_payload: dict = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if body_parameters:
        template_payload["components"] = [
            {"type": "body", "parameters": body_parameters}
        ]

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalized,
        "type": "template",
        "template": template_payload,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if resp.status_code not in (200, 201):
        logger.error(
            "WA template send failed: status=%d body=%s",
            resp.status_code, resp.text[:500],
        )
        raise RuntimeError(
            f"WhatsApp template API error {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    wamid = data.get("messages", [{}])[0].get("id", "?")
    logger.info(
        "WA template sent: name=%s to=%s wamid=%s",
        template_name, normalized, wamid,
    )
    return data
