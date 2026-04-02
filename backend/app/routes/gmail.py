"""
Gmail OAuth + management routes.

Flow:
  1. GET  /gmail/auth       → returns {auth_url}  (frontend redirects the browser)
  2. GET  /gmail/callback   → Google redirects here after consent; saves tokens; redirects to frontend
  3. GET  /gmail/status     → {connected, gmail_email, last_sync_at, sync_error, channel_id}
  4. POST /gmail/sync       → trigger manual sync
  5. DELETE /gmail/disconnect → revoke + delete credential + deactivate channel

State security:
  The OAuth `state` parameter is a short-lived JWT signed with settings.secret_key.
  This prevents CSRF without needing a server-side session store.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.channel import Channel
from app.models.gmail import GmailCredential
from app.models.user import User
from app.services.gmail_service import (
    GMAIL_SCOPES, encrypt_token, decrypt_token, _build_google_credentials,
)
from app.services import gmail_sync_service

router = APIRouter(prefix="/gmail", tags=["gmail"])
logger = logging.getLogger(__name__)


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.gmail_redirect_uri],
        }
    }


def _make_flow() -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.gmail_redirect_uri,
    )


def _make_state(user_id: int) -> str:
    """Sign a short-lived state token containing the user_id."""
    return jwt.encode(
        {
            "user_id": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def _verify_state(state: str) -> int:
    """Decode and validate the state JWT. Returns user_id."""
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
        return int(payload["user_id"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Estado OAuth inválido ou expirado") from exc


async def _get_or_update_credential(
    user_id: int, gmail_email: str, access_token: str, refresh_token: str,
    token_expiry: datetime | None, scopes: list[str], db: AsyncSession,
) -> GmailCredential:
    """Upsert a GmailCredential for the user."""
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == user_id)
    )
    cred = result.scalar_one_or_none()

    now = datetime.utcnow()
    encrypted_at = encrypt_token(access_token)
    encrypted_rt = encrypt_token(refresh_token)
    expiry_naive = token_expiry.replace(tzinfo=None) if token_expiry else None

    if cred is None:
        cred = GmailCredential(
            user_id=user_id,
            gmail_email=gmail_email,
            encrypted_access_token=encrypted_at,
            encrypted_refresh_token=encrypted_rt,
            token_expires_at=expiry_naive,
            scopes=" ".join(scopes),
            sync_enabled=True,
            sync_error=None,
            created_at=now,
            updated_at=now,
        )
        db.add(cred)
    else:
        cred.gmail_email = gmail_email
        cred.encrypted_access_token = encrypted_at
        if refresh_token:
            cred.encrypted_refresh_token = encrypted_rt
        cred.token_expires_at = expiry_naive
        cred.scopes = " ".join(scopes)
        cred.sync_enabled = True
        cred.sync_error = None
        cred.updated_at = now

    await db.flush()
    return cred


async def _ensure_gmail_channel(user_id: int, gmail_email: str, db: AsyncSession) -> Channel:
    """Find or create the user's Gmail channel."""
    result = await db.execute(
        select(Channel).where(
            Channel.user_id == user_id,
            Channel.type == "gmail",
        )
    )
    channel = result.scalar_one_or_none()
    if channel:
        channel.external_id = gmail_email
        channel.status = "active"
        channel.name = f"Gmail · {gmail_email}"
        return channel

    channel = Channel(
        user_id=user_id,
        type="gmail",
        name=f"Gmail · {gmail_email}",
        external_id=gmail_email,
        status="active",
    )
    db.add(channel)
    return channel


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/auth")
async def gmail_auth(
    current_user: User = Depends(get_current_user),
):
    """
    Step 1 of OAuth: return the Google authorization URL.
    The frontend should redirect the browser to this URL.
    """
    flow = _make_flow()
    state = _make_state(current_user.id)

    auth_url, _ = flow.authorization_url(
        state=state,
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # always show consent screen to guarantee refresh_token
    )
    return {"auth_url": auth_url}


@router.get("/callback")
async def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2 of OAuth: Google redirects here with an authorization code.
    Exchanges code for tokens, saves to DB, redirects to frontend.
    """
    if error:
        logger.warning("Gmail OAuth error: %s", error)
        return RedirectResponse(f"{settings.app_url}/integrations?gmail_error={error}")

    user_id = _verify_state(state)

    flow = _make_flow()
    flow.fetch_token(code=code)
    google_creds = flow.credentials

    if not google_creds.refresh_token:
        logger.error("Gmail callback: no refresh_token for user %s", user_id)
        return RedirectResponse(f"{settings.app_url}/integrations?gmail_error=no_refresh_token")

    # Fetch the Gmail account email via userinfo
    try:
        oauth2_service = build("oauth2", "v2", credentials=google_creds, cache_discovery=False)
        user_info = oauth2_service.userinfo().get().execute()
        gmail_email = user_info.get("email", "")
    except Exception as exc:
        logger.error("Failed to fetch Gmail userinfo: %s", exc)
        return RedirectResponse(f"{settings.app_url}/integrations?gmail_error=userinfo_failed")

    if not gmail_email:
        return RedirectResponse(f"{settings.app_url}/integrations?gmail_error=no_email")

    await _get_or_update_credential(
        user_id=user_id,
        gmail_email=gmail_email,
        access_token=google_creds.token,
        refresh_token=google_creds.refresh_token,
        token_expiry=google_creds.expiry,
        scopes=list(google_creds.scopes or GMAIL_SCOPES),
        db=db,
    )
    await _ensure_gmail_channel(user_id, gmail_email, db)
    await db.commit()

    logger.info("Gmail connected for user %s (%s)", user_id, gmail_email)

    # Kick off an initial sync (non-blocking — runs in background via event loop)
    import asyncio
    asyncio.create_task(gmail_sync_service.sync_user(user_id))

    return RedirectResponse(f"{settings.app_url}/integrations?gmail_connected=1")


@router.get("/status")
async def gmail_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current Gmail connection status for the authenticated user."""
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    cred = result.scalar_one_or_none()

    if cred is None:
        return {"connected": False}

    # Also get the channel
    ch_result = await db.execute(
        select(Channel).where(
            Channel.user_id == current_user.id,
            Channel.type == "gmail",
        )
    )
    channel = ch_result.scalar_one_or_none()

    return {
        "connected": True,
        "gmail_email": cred.gmail_email,
        "sync_enabled": cred.sync_enabled,
        "last_sync_at": cred.last_sync_at.isoformat() if cred.last_sync_at else None,
        "sync_error": cred.sync_error,
        "channel_id": channel.id if channel else None,
        "channel_status": channel.status if channel else None,
    }


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate Gmail sync for the authenticated user."""
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    cred = result.scalar_one_or_none()
    if cred is None:
        raise HTTPException(status_code=404, detail="Gmail não conectado")

    summary = await gmail_sync_service.sync_user(current_user.id)
    return {
        "ok": True,
        "threads_processed": summary["threads_processed"],
        "new_entries": summary["new_entries"],
        "errors": summary["errors"],
        "status": summary["status"],
    }


@router.delete("/disconnect", status_code=204)
async def gmail_disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect Gmail: revoke tokens with Google, delete credential row,
    and mark the Gmail channel as inactive.
    """
    result = await db.execute(
        select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    )
    cred = result.scalar_one_or_none()
    if cred is None:
        raise HTTPException(status_code=404, detail="Gmail não conectado")

    # Best-effort revoke with Google
    try:
        google_creds = _build_google_credentials(cred)
        import requests as http_requests
        http_requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": decrypt_token(cred.encrypted_refresh_token)},
            timeout=5,
        )
    except Exception as exc:
        logger.warning("Could not revoke Gmail token for user %s: %s", current_user.id, exc)

    # Deactivate the channel (keep threads — they remain historical)
    ch_result = await db.execute(
        select(Channel).where(
            Channel.user_id == current_user.id,
            Channel.type == "gmail",
        )
    )
    channel = ch_result.scalar_one_or_none()
    if channel:
        channel.status = "inactive"

    await db.delete(cred)
    await db.commit()
    logger.info("Gmail disconnected for user %s", current_user.id)
