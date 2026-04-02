"""
Server-Sent Events pub/sub service.

Architecture: in-memory asyncio.Queue per user session.
Supports multiple browser tabs (multiple queues per user).

Limitation: single-process only. For multi-process / multi-worker deployments,
replace with Redis pub/sub (use aioredis + PUBLISH/SUBSCRIBE on a channel
keyed by user_id, e.g. "inbox:events:{user_id}").
"""
import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# user_id → set of active queues (one per connected browser tab)
_queues: dict[int, set[asyncio.Queue]] = defaultdict(set)


def subscribe(user_id: int) -> asyncio.Queue:
    """Create and register a new queue for a user session."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _queues[user_id].add(q)
    logger.debug("SSE subscribe: user=%s active_sessions=%s", user_id, len(_queues[user_id]))
    return q


def unsubscribe(user_id: int, q: asyncio.Queue) -> None:
    """Remove a queue when the client disconnects."""
    _queues[user_id].discard(q)
    if not _queues[user_id]:
        del _queues[user_id]
    logger.debug("SSE unsubscribe: user=%s", user_id)


async def publish(user_id: int, event_type: str, data: Any) -> None:
    """
    Push an event to all active sessions for a user.
    Silently drops events if a queue is full (QueueFull) — non-blocking.
    Cleans up dead queues automatically.
    """
    payload = json.dumps({"type": event_type, "data": data})
    dead: set[asyncio.Queue] = set()

    for q in list(_queues.get(user_id, set())):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.add(q)
        except Exception as exc:
            logger.warning("SSE publish error: %s", exc)
            dead.add(q)

    for q in dead:
        _queues[user_id].discard(q)

    if dead:
        logger.debug("SSE: dropped %s dead queues for user=%s", len(dead), user_id)
