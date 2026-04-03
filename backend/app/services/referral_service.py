"""
Referral service: code generation, attribution, and reward logic.
"""
import random
import string
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.referral import Referral

logger = logging.getLogger(__name__)

_CHARS = string.ascii_uppercase + string.digits
_CODE_LEN = 7
REWARD_TRIAL_DAYS = 7   # extra trial days granted to referrer on conversion


# ── Code generation ──────────────────────────────────────────────────────────

def _gen_code() -> str:
    return "".join(random.choices(_CHARS, k=_CODE_LEN))


async def ensure_referral_code(user: User, db: AsyncSession) -> str:
    """Assign a unique referral code if the user doesn't have one yet."""
    if user.referral_code:
        return user.referral_code

    for _ in range(10):
        candidate = _gen_code()
        existing = await db.execute(select(User).where(User.referral_code == candidate))
        if existing.scalar_one_or_none() is None:
            user.referral_code = candidate
            await db.commit()
            return candidate

    raise RuntimeError("Failed to generate unique referral code after 10 attempts")


# ── Attribution ───────────────────────────────────────────────────────────────

async def apply_referral(new_user: User, ref_code: str, db: AsyncSession) -> None:
    """
    Called during registration when `ref` query param is present.
    Looks up the referrer, links the new user, and creates a pending Referral record.
    """
    if not ref_code:
        return
    try:
        result = await db.execute(
            select(User).where(User.referral_code == ref_code.upper())
        )
        referrer = result.scalar_one_or_none()
        if referrer is None or referrer.id == new_user.id:
            return

        new_user.referred_by_user_id = referrer.id
        referral = Referral(
            referrer_user_id=referrer.id,
            referred_user_id=new_user.id,
            referral_code=ref_code.upper(),
            status="pending",
        )
        db.add(referral)
        logger.info("Referral created: referrer=%s → referred=%s", referrer.id, new_user.id)
    except Exception as exc:
        logger.warning("apply_referral failed for code=%s: %s", ref_code, exc)


# ── Reward ────────────────────────────────────────────────────────────────────

async def maybe_reward_referrer(referred_user: User, db: AsyncSession) -> None:
    """
    Called when a referred user activates (starts trial or upgrades to paid).
    Grants the referrer REWARD_TRIAL_DAYS extra trial days and marks the referral rewarded.
    Safe to call multiple times — idempotent via status check.
    """
    if referred_user.referred_by_user_id is None:
        return
    try:
        result = await db.execute(
            select(Referral).where(
                Referral.referred_user_id == referred_user.id,
                Referral.status != "rewarded",
            )
        )
        referral = result.scalar_one_or_none()
        if referral is None:
            return

        referrer_result = await db.execute(
            select(User).where(User.id == referral.referrer_user_id)
        )
        referrer = referrer_result.scalar_one_or_none()
        if referrer is None:
            return

        # Extend trial for referrer
        now = datetime.utcnow()
        base = (
            referrer.trial_ends_at
            if referrer.trial_ends_at and referrer.trial_ends_at > now
            else now
        )
        referrer.trial_ends_at = base + timedelta(days=REWARD_TRIAL_DAYS)

        # If referrer was on free plan, bump them to trial status
        if referrer.subscription_status == "free":
            referrer.subscription_status = "trialing"
            referrer.plan = "pro"

        referral.status = "rewarded"
        referral.reward_type = "trial_days"
        referral.reward_value = REWARD_TRIAL_DAYS
        referral.rewarded_at = now

        logger.info(
            "Referral reward: referrer=%s +%d trial days (referral_id=%s)",
            referrer.id, REWARD_TRIAL_DAYS, referral.id,
        )
    except Exception as exc:
        logger.warning("maybe_reward_referrer failed for user=%s: %s", referred_user.id, exc)


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_referral_stats(user: User, db: AsyncSession) -> dict:
    """Return stats for the user's referral dashboard card."""
    total_result = await db.execute(
        select(func.count()).where(Referral.referrer_user_id == user.id)
    )
    total = total_result.scalar() or 0

    rewarded_result = await db.execute(
        select(func.count()).where(
            Referral.referrer_user_id == user.id,
            Referral.status == "rewarded",
        )
    )
    rewarded = rewarded_result.scalar() or 0

    code = await ensure_referral_code(user, db)

    return {
        "referral_code": code,
        "total_referrals": total,
        "rewarded_referrals": rewarded,
        "reward_description": f"+{REWARD_TRIAL_DAYS} dias de trial por indicação convertida",
    }
