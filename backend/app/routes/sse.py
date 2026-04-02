"""
Server-Sent Events endpoint for real-time inbox updates.

EventSource doesn't support custom headers, so auth token is passed as a
query parameter and validated here using the same JWT logic as security.py.

Frontend connects to: GET /api/v1/inbox/events?token={jwt_token}
"""
import asyncio
import json
import logging
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.core.database import get_db
from app.core.config import settings
from app.services import sse_service

router = APIRouter(prefix="/inbox", tags=["sse"])
logger = logging.getLogger(__name__)

# SSE keepalive interval in seconds
_KEEPALIVE_SECONDS = 20


async def _user_from_token(token: str, db: AsyncSession):
    """Validate JWT from query param and return the User object."""
    from app.models.user import User

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise ValueError("no sub")
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


@router.get("/events")
async def inbox_events(
    token: str = Query(..., description="JWT token (EventSource cannot send headers)"),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE stream for real-time inbox events.

    Event types emitted:
      connected       — first event, confirms the stream is live
      thread_created  — data: {id, ...}
      thread_updated  — data: {id, status, draft_status, detected_context, updated_at}
      entry_added     — data: {thread_id, entry: {id, direction, body, sender_name, created_at}}
      draft_ready     — data: {thread_id, draft, detected_context}
    """
    user = await _user_from_token(token, db)
    user_id = user.id
    queue = sse_service.subscribe(user_id)

    async def generate():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    raw = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_SECONDS)
                    msg = json.loads(raw)
                    data_str = json.dumps(msg["data"], default=str)
                    yield f"event: {msg['type']}\ndata: {data_str}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            sse_service.unsubscribe(user_id, queue)
            logger.debug("SSE stream closed: user=%s", user_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
