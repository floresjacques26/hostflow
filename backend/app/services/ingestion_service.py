"""
Email ingestion service.
Parses inbound email payloads from email forwarding providers.

Designed to support:
  - Postmark Inbound Parse (primary)
  - Mailgun Inbound Routes (secondary)
  - Raw fallback (any dict with at least a 'body' or 'text' key)

The ingestion email address format is: inbox+{referral_code}@hostflow.io
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns to strip quoted reply content from forwarded emails
_QUOTE_PATTERNS = [
    re.compile(r"On .+? wrote:", re.DOTALL),
    re.compile(r"Em .+? escreveu:", re.DOTALL),
    re.compile(r"-{3,}.*?Original Message.*?-{3,}", re.DOTALL | re.IGNORECASE),
    re.compile(r">{1,}.*$", re.MULTILINE),
]


def _strip_quoted(text: str) -> str:
    """Remove quoted/forwarded content from email bodies."""
    for pat in _QUOTE_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


def _extract_inbox_token(to_address: str) -> Optional[str]:
    """
    Extract inbox token from To address.
    Expects formats like:
      inbox+ABC1234@hostflow.io
      <inbox+ABC1234@hostflow.io>
    """
    match = re.search(r"inbox\+([A-Z0-9]{4,20})@", to_address, re.IGNORECASE)
    return match.group(1).upper() if match else None


class ParsedEmail:
    __slots__ = ("inbox_token", "sender_email", "sender_name", "subject", "body", "raw")

    def __init__(
        self,
        inbox_token: Optional[str],
        sender_email: str,
        sender_name: str,
        subject: str,
        body: str,
        raw: dict,
    ):
        self.inbox_token = inbox_token
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.subject = subject
        self.body = body
        self.raw = raw


def parse_postmark(payload: dict) -> ParsedEmail:
    """Parse Postmark InboundMessage format."""
    to_address = payload.get("To") or payload.get("ToFull", [{}])[0].get("Email", "")
    inbox_token = _extract_inbox_token(to_address)

    sender_email = payload.get("From", "")
    sender_name = payload.get("FromName", "") or sender_email

    subject = payload.get("Subject", "Sem assunto")

    # Prefer StrippedTextReply (most clean), fall back to TextBody, then HtmlBody (stripped)
    body = (
        payload.get("StrippedTextReply")
        or payload.get("TextBody")
        or re.sub(r"<[^>]+>", " ", payload.get("HtmlBody", ""))
    )
    body = _strip_quoted(body or "").strip()

    return ParsedEmail(
        inbox_token=inbox_token,
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        body=body or "(Corpo da mensagem vazio)",
        raw=payload,
    )


def parse_mailgun(payload: dict) -> ParsedEmail:
    """Parse Mailgun inbound route format."""
    to_address = payload.get("recipient", "")
    inbox_token = _extract_inbox_token(to_address)

    sender_email = payload.get("sender", "")
    sender_name = payload.get("from", sender_email)

    subject = payload.get("subject", "Sem assunto")
    body = (
        payload.get("stripped-text")
        or payload.get("body-plain")
        or ""
    )
    body = _strip_quoted(body).strip()

    return ParsedEmail(
        inbox_token=inbox_token,
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        body=body or "(Corpo da mensagem vazio)",
        raw=payload,
    )


def parse_raw(payload: dict) -> ParsedEmail:
    """Fallback parser — looks for common field names."""
    to_address = (
        payload.get("to") or payload.get("To") or
        payload.get("recipient") or payload.get("Recipient") or ""
    )
    inbox_token = _extract_inbox_token(to_address)

    sender_email = (
        payload.get("from") or payload.get("From") or
        payload.get("sender") or ""
    )
    sender_name = sender_email

    subject = (
        payload.get("subject") or payload.get("Subject") or "Sem assunto"
    )
    body = (
        payload.get("body") or payload.get("text") or
        payload.get("body-plain") or payload.get("TextBody") or ""
    )
    body = _strip_quoted(str(body)).strip()

    return ParsedEmail(
        inbox_token=inbox_token,
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        body=body or "(Corpo da mensagem vazio)",
        raw=payload,
    )


def parse_inbound_email(payload: dict) -> ParsedEmail:
    """
    Auto-detect provider and parse.
    Falls back to raw parser if provider is unknown.
    """
    # Postmark: has 'MessageID' or 'MailboxHash'
    if "MessageID" in payload or "MailboxHash" in payload:
        return parse_postmark(payload)
    # Mailgun: has 'message-headers' or 'body-plain'
    if "body-plain" in payload or "message-headers" in payload:
        return parse_mailgun(payload)
    return parse_raw(payload)
