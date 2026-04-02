"""Tracks and queries monthly AI response usage per user."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.usage import UsageCounter


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def get_monthly_usage(user_id: int, db: AsyncSession) -> int:
    month = _current_month()
    result = await db.execute(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.month == month,
        )
    )
    counter = result.scalar_one_or_none()
    return counter.ai_responses if counter else 0


async def increment_ai_response(user_id: int, db: AsyncSession) -> int:
    """
    Atomically increments the AI response counter for the current month.
    Uses PostgreSQL upsert to avoid race conditions.
    Returns the new count.
    """
    month = _current_month()
    stmt = (
        pg_insert(UsageCounter)
        .values(user_id=user_id, month=month, ai_responses=1)
        .on_conflict_do_update(
            constraint="uq_usage_user_month",
            set_={"ai_responses": UsageCounter.ai_responses + 1, "updated_at": datetime.now(timezone.utc)},
        )
        .returning(UsageCounter.ai_responses)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def get_usage_summary(user_id: int, db: AsyncSession) -> dict:
    month = _current_month()
    result = await db.execute(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.month == month,
        )
    )
    counter = result.scalar_one_or_none()
    return {
        "month": month,
        "ai_responses": counter.ai_responses if counter else 0,
    }
