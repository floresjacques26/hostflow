"""
Email provider abstraction.

Swappable architecture: set RESEND_API_KEY in .env to activate real sending.
Without it, emails are logged to stdout (dev/test mode — zero side effects).

To swap to Postmark or SendGrid, implement a new class matching the same
async `send()` signature and update `get_provider()`.
"""
import asyncio
import logging
from typing import Protocol, runtime_checkable
from app.core.config import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class EmailProvider(Protocol):
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> bool:
        """Send an email. Returns True on success, False on failure."""
        ...


class ResendProvider:
    """
    Sends email via Resend (https://resend.com).
    Requires: pip install resend
    Env var: RESEND_API_KEY
    """

    def __init__(self, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from = from_address

    async def send(self, to: str, subject: str, html: str, text: str | None = None) -> bool:
        try:
            import resend  # lazy import — only required when actually used

            resend.api_key = self._api_key
            params: dict = {
                "from": self._from,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            if text:
                params["text"] = text

            await asyncio.to_thread(resend.Emails.send, params)
            logger.info("email sent via Resend to=%s subject=%r", to, subject)
            return True
        except Exception as exc:
            logger.error("ResendProvider.send failed to=%s: %s", to, exc)
            return False


class LoggingProvider:
    """
    Dev/test fallback — prints email contents to the log instead of sending.
    No external dependencies. Zero side effects.
    """

    async def send(self, to: str, subject: str, html: str, text: str | None = None) -> bool:
        logger.info(
            "[EMAIL-DEV] to=%s | subject=%r | len(html)=%d",
            to,
            subject,
            len(html),
        )
        if text:
            logger.debug("[EMAIL-DEV] plain-text preview:\n%s", text[:400])
        return True


# ── Singleton provider (resolved once at import time) ────────────────────────

_provider: EmailProvider | None = None


def get_provider() -> EmailProvider:
    """
    Returns the configured provider singleton.
    Resolution order:
      1. RESEND_API_KEY set → ResendProvider
      2. fallback           → LoggingProvider (dev)
    """
    global _provider
    if _provider is None:
        if settings.resend_api_key:
            _provider = ResendProvider(settings.resend_api_key, settings.email_from)
            logger.info("email_service: using ResendProvider (from=%s)", settings.email_from)
        else:
            _provider = LoggingProvider()
            logger.info("email_service: RESEND_API_KEY not set — using LoggingProvider (dev mode)")
    return _provider


def reset_provider() -> None:
    """Force re-resolution of the provider. Useful in tests."""
    global _provider
    _provider = None
