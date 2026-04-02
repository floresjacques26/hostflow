"""
Guest profile matching and management.

Normalizes contact info (email/phone) and upserts GuestProfile records.
Called on thread creation to auto-link threads to guest profiles.
"""
import re
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.guest import GuestProfile

logger = logging.getLogger(__name__)


def _looks_like_email(contact: str) -> bool:
    return "@" in contact


def _normalize_email(raw: str) -> str:
    return raw.strip().lower()


def _normalize_phone(raw: str) -> str:
    """Strip everything except digits; include leading + for international."""
    digits = re.sub(r"[^\d]", "", raw.strip())
    return digits if len(digits) >= 7 else ""


async def find_or_create_profile(
    user_id: int,
    guest_contact: str | None,
    guest_name: str | None,
    db: AsyncSession,
) -> GuestProfile | None:
    """
    Given a raw guest_contact string (email or phone), find or create a GuestProfile.
    Returns the profile or None if contact is empty/unparseable.
    Never raises.
    """
    if not guest_contact or not guest_contact.strip():
        return None

    try:
        contact = guest_contact.strip()

        if _looks_like_email(contact):
            norm = _normalize_email(contact)
            result = await db.execute(
                select(GuestProfile).where(
                    GuestProfile.user_id == user_id,
                    GuestProfile.primary_email == norm,
                )
            )
        else:
            norm = _normalize_phone(contact)
            if not norm:
                return None
            result = await db.execute(
                select(GuestProfile).where(
                    GuestProfile.user_id == user_id,
                    GuestProfile.primary_phone == norm,
                )
            )

        profile = result.scalar_one_or_none()

        if profile:
            # Enrich existing profile with name if we now have it
            if guest_name and not profile.name:
                profile.name = guest_name
                profile.updated_at = datetime.now(timezone.utc)
            return profile

        # Create new profile
        profile = GuestProfile(
            user_id=user_id,
            name=guest_name,
            primary_email=_normalize_email(contact) if _looks_like_email(contact) else None,
            primary_phone=_normalize_phone(contact) if not _looks_like_email(contact) else None,
        )
        db.add(profile)
        await db.flush()
        logger.info("GuestProfile created: user=%s contact=%s", user_id, norm)
        return profile

    except Exception as exc:
        logger.warning("guest_service.find_or_create_profile failed: %s", exc)
        return None


async def get_profile_stats(profile_id: int, db: AsyncSession) -> dict:
    """
    Compute stats for a guest profile:
    - thread_count
    - common_contexts (top 3)
    - properties involved
    - last_contact_at
    """
    from sqlalchemy import func
    from app.models.thread import MessageThread

    result = await db.execute(
        select(
            func.count().label("total"),
            func.max(MessageThread.last_message_at).label("last_contact"),
        ).where(MessageThread.guest_profile_id == profile_id)
    )
    row = result.one()

    # Most common contexts
    ctx_result = await db.execute(
        select(
            MessageThread.detected_context,
            func.count().label("cnt"),
        )
        .where(
            MessageThread.guest_profile_id == profile_id,
            MessageThread.detected_context.isnot(None),
        )
        .group_by(MessageThread.detected_context)
        .order_by(func.count().desc())
        .limit(3)
    )
    common_contexts = [r.detected_context for r in ctx_result.all()]

    # Properties involved
    from app.models.property import Property
    from sqlalchemy.orm import selectinload
    prop_result = await db.execute(
        select(Property.id, Property.name)
        .join(MessageThread, MessageThread.property_id == Property.id)
        .where(MessageThread.guest_profile_id == profile_id)
        .distinct()
        .limit(5)
    )
    properties = [{"id": r.id, "name": r.name} for r in prop_result.all()]

    return {
        "thread_count": row.total or 0,
        "common_contexts": common_contexts,
        "properties": properties,
        "last_contact_at": row.last_contact,
    }
