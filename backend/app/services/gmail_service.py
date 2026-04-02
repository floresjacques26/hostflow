"""
Gmail API service layer.

Responsibilities:
  - Fernet-based token encryption / decryption
  - Build an authenticated Google API service object (auto-refreshes token)
  - Parse Gmail messages into a clean dataclass
  - Send replies, preserving Gmail thread continuity
  - Persist updated token state back to the DB after refresh

Dependencies (add to requirements.txt / pyproject.toml):
    google-auth>=2.29.0
    google-auth-oauthlib>=1.2.0
    google-api-python-client>=2.127.0
    cryptography>=42.0.0
"""
import base64
import email.utils
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional

from cryptography.fernet import Fernet
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.gmail import GmailCredential

logger = logging.getLogger(__name__)

# Scopes: modify covers read + labels + send (no delete)
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


# ── Token encryption ──────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    return Fernet(settings.gmail_encryption_key.encode())


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode()).decode()


# ── Credentials + API client ──────────────────────────────────────────────────

def _build_google_credentials(cred: GmailCredential) -> Credentials:
    """Reconstruct Google credentials from the stored (encrypted) token data."""
    expires_at = None
    if cred.token_expires_at:
        expires_at = cred.token_expires_at.replace(tzinfo=timezone.utc)

    return Credentials(
        token=decrypt_token(cred.encrypted_access_token),
        refresh_token=decrypt_token(cred.encrypted_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=cred.scopes.split() if cred.scopes else GMAIL_SCOPES,
        expiry=expires_at,
    )


async def get_gmail_service(cred: GmailCredential, db: AsyncSession):
    """
    Return an authenticated Gmail API Resource.
    If the access token is expired, refreshes it and persists the new token to DB.
    Raises RuntimeError if credentials are invalid / unrefreshable.
    """
    google_creds = _build_google_credentials(cred)

    if google_creds.expired and google_creds.refresh_token:
        try:
            google_creds.refresh(GoogleAuthRequest())
            # Persist updated token
            cred.encrypted_access_token = encrypt_token(google_creds.token)
            if google_creds.expiry:
                cred.token_expires_at = google_creds.expiry.replace(tzinfo=None)  # store naive UTC
            cred.sync_error = None
            cred.updated_at = datetime.utcnow()
            await db.commit()
            logger.info("Gmail token refreshed for user_id=%s", cred.user_id)
        except RefreshError as exc:
            cred.sync_error = f"Token refresh failed: {exc}"
            cred.updated_at = datetime.utcnow()
            await db.commit()
            raise RuntimeError(f"Gmail token refresh failed for user {cred.user_id}: {exc}") from exc

    return build("gmail", "v1", credentials=google_creds, cache_discovery=False)


# ── Message parsing ───────────────────────────────────────────────────────────

@dataclass
class ParsedGmailMessage:
    gmail_message_id: str
    gmail_thread_id: str
    subject: str
    sender_name: Optional[str]
    sender_email: Optional[str]
    to_email: Optional[str]
    message_id_header: Optional[str]   # RFC 2822 Message-ID (for In-Reply-To)
    references_header: Optional[str]   # RFC 2822 References chain
    body: str
    snippet: str
    sent_at: Optional[datetime]
    internalDate: Optional[int] = None  # ms since epoch (fallback)


def _decode_base64(data: str) -> str:
    """Decode URL-safe base64 Gmail body data."""
    if not data:
        return ""
    # Pad to multiple of 4
    padded = data + "=" * (4 - len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_body(payload: dict, prefer: str = "text/plain") -> str:
    """
    Recursively extract the body text from a Gmail message payload.
    Prefers plain text; falls back to HTML (tags stripped), then snippet.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == prefer and body_data:
        return _decode_base64(body_data)

    # Multipart: recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        result = _extract_body(part, prefer)
        if result.strip():
            return result

    # Fallback: any text/* part
    if mime_type.startswith("text/") and body_data:
        text = _decode_base64(body_data)
        if mime_type == "text/html":
            # Very basic HTML tag stripping
            import re
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\s+", " ", text).strip()
        return text

    return ""


def parse_gmail_message(msg: dict) -> ParsedGmailMessage:
    """Convert a raw Gmail API message dict into a ParsedGmailMessage."""
    headers_list = msg.get("payload", {}).get("headers", [])
    headers = {h["name"].lower(): h["value"] for h in headers_list}

    subject = headers.get("subject", "(sem assunto)")
    from_raw = headers.get("from", "")
    to_raw = headers.get("to", "")
    message_id_hdr = headers.get("message-id")
    references_hdr = headers.get("references")
    date_str = headers.get("date", "")

    sender_name, sender_email = email.utils.parseaddr(from_raw)
    if not sender_email:
        sender_email = None
    if not sender_name:
        sender_name = sender_email

    sent_at: Optional[datetime] = None
    if date_str:
        try:
            dt = email.utils.parsedate_to_datetime(date_str)
            sent_at = dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            pass

    if not sent_at and msg.get("internalDate"):
        sent_at = datetime.utcfromtimestamp(int(msg["internalDate"]) / 1000)

    body = _extract_body(msg.get("payload", {}))
    if not body.strip():
        body = msg.get("snippet", "")

    return ParsedGmailMessage(
        gmail_message_id=msg["id"],
        gmail_thread_id=msg["threadId"],
        subject=subject,
        sender_name=sender_name,
        sender_email=sender_email,
        to_email=to_raw or None,
        message_id_header=message_id_hdr,
        references_header=references_hdr,
        body=body.strip(),
        snippet=msg.get("snippet", ""),
        sent_at=sent_at,
        internalDate=int(msg.get("internalDate", 0)),
    )


# ── Fetch helpers ─────────────────────────────────────────────────────────────

def list_thread_ids(service, after_date: Optional[datetime] = None, max_results: int = 50) -> list[str]:
    """Return Gmail thread IDs modified after after_date (or last 7 days)."""
    from datetime import timedelta
    if after_date is None:
        after_date = datetime.utcnow() - timedelta(days=7)

    # Gmail search query: after:<epoch_seconds>
    epoch = int(after_date.replace(tzinfo=timezone.utc).timestamp())
    query = f"after:{epoch}"

    thread_ids = []
    page_token = None
    while True:
        kwargs = {
            "userId": "me",
            "q": query,
            "maxResults": min(max_results, 100),
        }
        if page_token:
            kwargs["pageToken"] = page_token

        try:
            resp = service.users().threads().list(**kwargs).execute()
        except HttpError as exc:
            logger.error("Gmail threads.list error: %s", exc)
            break

        for t in resp.get("threads", []):
            thread_ids.append(t["id"])
            if len(thread_ids) >= max_results:
                break

        page_token = resp.get("nextPageToken")
        if not page_token or len(thread_ids) >= max_results:
            break

    return thread_ids


def get_thread_messages(service, gmail_thread_id: str) -> list[ParsedGmailMessage]:
    """Fetch all messages in a Gmail thread, parsed."""
    try:
        resp = service.users().threads().get(
            userId="me",
            id=gmail_thread_id,
            format="full",
        ).execute()
    except HttpError as exc:
        logger.error("Gmail threads.get(%s) error: %s", gmail_thread_id, exc)
        return []

    return [parse_gmail_message(m) for m in resp.get("messages", [])]


# ── Send reply ────────────────────────────────────────────────────────────────

def build_reply_raw(
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: Optional[str],
    references: Optional[str],
    from_email: Optional[str] = None,
) -> dict:
    """
    Build a base64url-encoded RFC 2822 reply message.
    Returns the dict to pass to service.users().messages().send(body=...).
    """
    subject_clean = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject_clean

    if from_email:
        msg["From"] = from_email

    if reply_to_message_id:
        msg["In-Reply-To"] = reply_to_message_id
        # References = previous references + current message-id
        refs = f"{references} {reply_to_message_id}".strip() if references else reply_to_message_id
        msg["References"] = refs

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


async def send_reply(
    service,
    to: str,
    subject: str,
    body: str,
    gmail_thread_id: str,
    reply_to_message_id: Optional[str] = None,
    references: Optional[str] = None,
) -> dict:
    """
    Send a reply via Gmail API.
    Returns the sent message dict (with 'id' and 'threadId').
    Raises HttpError on failure.
    """
    payload = build_reply_raw(to, subject, body, reply_to_message_id, references)
    payload["threadId"] = gmail_thread_id

    sent = service.users().messages().send(userId="me", body=payload).execute()
    logger.info(
        "Gmail reply sent: thread=%s message=%s",
        sent.get("threadId"), sent.get("id"),
    )
    return sent
