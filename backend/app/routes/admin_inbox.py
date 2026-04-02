from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, text
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_admin_user
from app.core.config import settings
from app.models.thread import MessageThread, MessageEntry
from app.models.gmail import GmailCredential
from app.models.template import Template
from app.models.auto_send import AutoSendDecisionLog, AutoSendRule
from app.models.whatsapp import WhatsAppCredential

router = APIRouter(prefix="/admin/inbox", tags=["admin-inbox"])


@router.get("/stats")
async def inbox_stats(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Overall counts
    totals = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((MessageThread.status == "open", 1), else_=0)).label("open"),
            func.sum(case((MessageThread.status == "pending", 1), else_=0)).label("pending"),
            func.sum(case((MessageThread.status == "resolved", 1), else_=0)).label("resolved"),
            func.sum(case((MessageThread.status == "archived", 1), else_=0)).label("archived"),
            func.sum(case((MessageThread.draft_status == "draft_generated", 1), else_=0)).label("drafts_pending"),
            func.sum(case((MessageThread.draft_status == "replied", 1), else_=0)).label("replied"),
        )
    )
    t = totals.one()

    # Total AI drafts generated
    draft_count = await db.execute(
        select(func.count()).where(MessageEntry.direction == "ai_draft")
    )

    # By channel source_type
    by_source = await db.execute(
        select(
            MessageThread.source_type,
            func.count().label("count"),
        )
        .group_by(MessageThread.source_type)
        .order_by(func.count().desc())
    )

    # By context
    by_context = await db.execute(
        select(
            func.coalesce(MessageThread.detected_context, "unclassified").label("context"),
            func.count().label("count"),
        )
        .group_by(text("1"))
        .order_by(func.count().desc())
        .limit(15)
    )

    # Average time to first AI draft (hours)
    # = avg(first ai_draft entry.created_at - thread.created_at) WHERE draft exists
    avg_ttd = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    func.min(MessageEntry.created_at) - MessageThread.created_at
                ) / 3600
            ).label("avg_hours")
        )
        .join(MessageThread, MessageThread.id == MessageEntry.thread_id)
        .where(MessageEntry.direction == "ai_draft")
        .group_by(MessageThread.id)
    )
    avg_rows = avg_ttd.scalars().all()
    avg_draft_hours = (
        round(sum(avg_rows) / len(avg_rows), 2) if avg_rows else 0.0
    )

    resolved_rate = round(t.resolved / t.total * 100, 1) if t.total else 0.0

    # SLA thresholds
    overdue_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.sla_open_overdue_hours)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.sla_pending_stale_hours)

    # Overdue: open threads created more than sla_open_overdue_hours ago
    overdue_result = await db.execute(
        select(func.count()).where(
            MessageThread.status == "open",
            MessageThread.created_at < overdue_cutoff,
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Stale: pending threads with last_message_at (or updated_at) older than sla_pending_stale_hours
    stale_result = await db.execute(
        select(func.count()).where(
            MessageThread.status == "pending",
            func.coalesce(MessageThread.last_message_at, MessageThread.updated_at) < stale_cutoff,
        )
    )
    stale_count = stale_result.scalar() or 0

    # Average time to resolve (hours): resolved threads only
    avg_resolve = await db.execute(
        select(
            func.avg(
                func.extract("epoch", MessageThread.updated_at - MessageThread.created_at) / 3600
            ).label("avg_hours")
        ).where(MessageThread.status == "resolved")
    )
    avg_resolve_hours = round(avg_resolve.scalar() or 0.0, 2)

    # Average time open (hours): currently open threads, measured from created_at to now
    avg_open = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    func.now() - MessageThread.created_at
                ) / 3600
            ).label("avg_hours")
        ).where(MessageThread.status == "open")
    )
    avg_open_hours = round(avg_open.scalar() or 0.0, 2)

    # Average time pending (hours): pending threads, from last_message_at (or created_at) to now
    avg_pending = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    func.now() - func.coalesce(MessageThread.last_message_at, MessageThread.created_at)
                ) / 3600
            ).label("avg_hours")
        ).where(MessageThread.status == "pending")
    )
    avg_pending_hours = round(avg_pending.scalar() or 0.0, 2)

    # Repeat-guest rate: threads from guests with > 1 thread
    repeat_guest = await db.execute(
        select(func.count()).where(
            MessageThread.guest_profile_id.in_(
                select(MessageThread.guest_profile_id)
                .where(MessageThread.guest_profile_id.is_not(None))
                .group_by(MessageThread.guest_profile_id)
                .having(func.count() > 1)
                .scalar_subquery()
            )
        )
    )
    repeat_guest_threads = repeat_guest.scalar() or 0
    repeat_guest_rate = round(repeat_guest_threads / t.total * 100, 1) if t.total else 0.0

    return {
        "total_threads": t.total or 0,
        "open": t.open or 0,
        "pending": t.pending or 0,
        "resolved": t.resolved or 0,
        "archived": t.archived or 0,
        "resolved_rate_pct": resolved_rate,
        "drafts_pending_review": t.drafts_pending or 0,
        "replied": t.replied or 0,
        "total_ai_drafts_generated": draft_count.scalar() or 0,
        "avg_time_to_draft_hours": avg_draft_hours,
        # SLA metrics
        "sla_overdue_open_count": overdue_count,
        "sla_stale_pending_count": stale_count,
        "avg_time_to_resolve_hours": avg_resolve_hours,
        "avg_time_open_hours": avg_open_hours,
        "avg_time_pending_hours": avg_pending_hours,
        "repeat_guest_thread_rate_pct": repeat_guest_rate,
        "by_source": [
            {"source": r.source_type, "count": r.count}
            for r in by_source.all()
        ],
        "by_context": [
            {"context": r.context, "count": r.count}
            for r in by_context.all()
        ],
        # Gmail-specific analytics (appended below)
    }

    # ── Gmail analytics ──────────────────────────────────────────────────────

    # Connected Gmail accounts
    gmail_accounts = await db.execute(select(func.count()).select_from(GmailCredential))
    data["gmail_connected_accounts"] = gmail_accounts.scalar() or 0

    # Accounts with a recent sync error
    gmail_errors = await db.execute(
        select(func.count()).where(GmailCredential.sync_error.is_not(None))
    )
    data["gmail_sync_error_accounts"] = gmail_errors.scalar() or 0

    # Total Gmail-sourced threads
    gmail_threads = await db.execute(
        select(func.count()).where(MessageThread.source_type == "gmail")
    )
    data["gmail_synced_threads"] = gmail_threads.scalar() or 0

    # Replies sent via Gmail API
    gmail_sent = await db.execute(
        select(func.count()).where(
            MessageEntry.sent_via_provider == True,  # noqa: E712
            MessageEntry.delivery_status == "sent",
        )
    )
    data["gmail_sent_replies"] = gmail_sent.scalar() or 0

    # Failed sends
    gmail_failed = await db.execute(
        select(func.count()).where(
            MessageEntry.sent_via_provider == True,  # noqa: E712
            MessageEntry.delivery_status == "failed",
        )
    )
    data["gmail_failed_sends"] = gmail_failed.scalar() or 0

    # Average time since last sync (hours) — for connected accounts
    avg_since_sync = await db.execute(
        select(
            func.avg(
                func.extract("epoch", func.now() - GmailCredential.last_sync_at) / 3600
            )
        ).where(GmailCredential.last_sync_at.is_not(None))
    )
    data["gmail_avg_hours_since_sync"] = round(avg_since_sync.scalar() or 0.0, 2)

    return data


@router.get("/auto-send-analytics")
async def auto_send_analytics(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-send system analytics across all users."""

    # Global totals
    totals = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((AutoSendDecisionLog.decision == "sent", 1), else_=0)).label("sent"),
            func.sum(case((AutoSendDecisionLog.decision == "blocked", 1), else_=0)).label("blocked"),
            func.sum(case((AutoSendDecisionLog.decision == "manual_review", 1), else_=0)).label("manual_review"),
        )
    )
    t = totals.one()
    total = t.total or 0
    sent = t.sent or 0

    # Top block reasons
    block_reasons = await db.execute(
        select(
            AutoSendDecisionLog.reason_code,
            func.count().label("count"),
        )
        .where(AutoSendDecisionLog.decision == "blocked")
        .group_by(AutoSendDecisionLog.reason_code)
        .order_by(func.count().desc())
    )

    # Decision breakdown by context
    by_context = await db.execute(
        select(
            func.coalesce(MessageThread.detected_context, "unclassified").label("context"),
            func.sum(case((AutoSendDecisionLog.decision == "sent", 1), else_=0)).label("sent"),
            func.sum(case((AutoSendDecisionLog.decision == "blocked", 1), else_=0)).label("blocked"),
            func.count().label("total"),
        )
        .join(MessageThread, MessageThread.id == AutoSendDecisionLog.thread_id)
        .group_by(text("1"))
        .order_by(func.count().desc())
        .limit(15)
    )

    # Active rules count per user (top 10 users)
    rules_per_user = await db.execute(
        select(
            AutoSendRule.user_id,
            func.count().label("rules"),
        )
        .where(AutoSendRule.active == True)  # noqa: E712
        .group_by(AutoSendRule.user_id)
        .order_by(func.count().desc())
        .limit(10)
    )

    return {
        "total_evaluations": total,
        "auto_sent": sent,
        "blocked": t.blocked or 0,
        "manual_review": t.manual_review or 0,
        "auto_send_rate_pct": round(sent / total * 100, 1) if total else 0.0,
        "top_block_reasons": [
            {"reason_code": r.reason_code, "count": r.count}
            for r in block_reasons.all()
        ],
        "by_context": [
            {"context": r.context, "sent": r.sent, "blocked": r.blocked, "total": r.total}
            for r in by_context.all()
        ],
        "rules_per_user_top10": [
            {"user_id": r.user_id, "rules": r.rules}
            for r in rules_per_user.all()
        ],
    }


@router.get("/template-analytics")
async def template_analytics(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Template usage analytics across all users."""

    # Top templates by number of threads they were applied to
    top_templates_result = await db.execute(
        select(
            MessageThread.applied_template_id,
            func.count().label("threads_count"),
            func.sum(
                case((MessageThread.template_auto_applied == True, 1), else_=0)  # noqa: E712
            ).label("auto_applied_count"),
        )
        .where(MessageThread.applied_template_id.is_not(None))
        .group_by(MessageThread.applied_template_id)
        .order_by(func.count().desc())
        .limit(20)
    )
    top_rows = top_templates_result.all()

    # Fetch template titles in one query
    if top_rows:
        template_ids = [r.applied_template_id for r in top_rows]
        t_result = await db.execute(
            select(Template.id, Template.title, Template.context_key).where(
                Template.id.in_(template_ids)
            )
        )
        t_map = {row.id: row for row in t_result.all()}
    else:
        t_map = {}

    top_templates = []
    for row in top_rows:
        t_info = t_map.get(row.applied_template_id)
        top_templates.append({
            "template_id": row.applied_template_id,
            "title": t_info.title if t_info else "Desconhecido",
            "context_key": t_info.context_key if t_info else None,
            "threads_count": row.threads_count,
            "auto_applied_count": row.auto_applied_count,
            "manual_selected_count": row.threads_count - row.auto_applied_count,
            "auto_apply_rate_pct": round(row.auto_applied_count / row.threads_count * 100, 1),
        })

    # Total threads with a template applied
    with_template = await db.execute(
        select(func.count()).where(MessageThread.applied_template_id.is_not(None))
    )
    without_template = await db.execute(
        select(func.count()).where(MessageThread.applied_template_id.is_(None))
    )
    total_with = with_template.scalar() or 0
    total_without = without_template.scalar() or 0
    total = total_with + total_without
    coverage_pct = round(total_with / total * 100, 1) if total else 0.0

    # Auto-apply rate overall
    auto_applied_total = await db.execute(
        select(func.count()).where(
            MessageThread.applied_template_id.is_not(None),
            MessageThread.template_auto_applied == True,  # noqa: E712
        )
    )
    auto_rate = round((auto_applied_total.scalar() or 0) / total_with * 100, 1) if total_with else 0.0

    # Contexts without any template coverage (active templates)
    active_ctx_result = await db.execute(
        select(Template.context_key).where(
            Template.active == True,  # noqa: E712
            Template.context_key.is_not(None),
        ).distinct()
    )
    covered_contexts = {r[0] for r in active_ctx_result.all() if r[0]}

    all_thread_contexts_result = await db.execute(
        select(MessageThread.detected_context, func.count().label("count"))
        .where(MessageThread.detected_context.is_not(None))
        .group_by(MessageThread.detected_context)
        .order_by(func.count().desc())
    )
    uncovered_contexts = [
        {"context": r.detected_context, "thread_count": r.count}
        for r in all_thread_contexts_result.all()
        if r.detected_context not in covered_contexts
    ]

    return {
        "template_coverage_pct": coverage_pct,
        "threads_with_template": total_with,
        "threads_without_template": total_without,
        "auto_apply_rate_pct": auto_rate,
        "top_templates": top_templates,
        "uncovered_contexts": uncovered_contexts,
    }


@router.get("/whatsapp-analytics")
async def whatsapp_analytics(
    _admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """WhatsApp integration analytics across all users."""

    # Connected accounts
    wa_accounts = await db.execute(select(func.count()).select_from(WhatsAppCredential))
    wa_connected = await db.execute(
        select(func.count()).where(WhatsAppCredential.status == "connected")
    )
    wa_errors = await db.execute(
        select(func.count()).where(WhatsAppCredential.status == "error")
    )

    # Total WhatsApp threads
    wa_threads = await db.execute(
        select(func.count()).where(MessageThread.source_type == "whatsapp")
    )

    # Inbound messages from WhatsApp
    wa_inbound = await db.execute(
        select(func.count())
        .join(MessageThread, MessageThread.id == MessageEntry.thread_id)
        .where(
            MessageThread.source_type == "whatsapp",
            MessageEntry.direction == "inbound",
        )
    )

    # Sent replies via provider
    wa_sent = await db.execute(
        select(func.count())
        .join(MessageThread, MessageThread.id == MessageEntry.thread_id)
        .where(
            MessageThread.source_type == "whatsapp",
            MessageEntry.sent_via_provider == True,  # noqa: E712
            MessageEntry.delivery_status == "sent",
        )
    )

    # Failed sends
    wa_failed = await db.execute(
        select(func.count())
        .join(MessageThread, MessageThread.id == MessageEntry.thread_id)
        .where(
            MessageThread.source_type == "whatsapp",
            MessageEntry.sent_via_provider == True,  # noqa: E712
            MessageEntry.delivery_status == "failed",
        )
    )

    # Delivered (status webhook updated)
    wa_delivered = await db.execute(
        select(func.count())
        .join(MessageThread, MessageThread.id == MessageEntry.thread_id)
        .where(
            MessageThread.source_type == "whatsapp",
            MessageEntry.delivery_status == "delivered",
        )
    )

    # Read
    wa_read = await db.execute(
        select(func.count())
        .join(MessageThread, MessageThread.id == MessageEntry.thread_id)
        .where(
            MessageThread.source_type == "whatsapp",
            MessageEntry.delivery_status == "read",
        )
    )

    # Top contexts from WhatsApp threads
    wa_contexts = await db.execute(
        select(
            func.coalesce(MessageThread.detected_context, "unclassified").label("context"),
            func.count().label("count"),
        )
        .where(MessageThread.source_type == "whatsapp")
        .group_by(text("1"))
        .order_by(func.count().desc())
        .limit(10)
    )

    # Channel mix: WhatsApp vs Gmail vs manual vs other
    channel_mix = await db.execute(
        select(
            MessageThread.source_type,
            func.count().label("count"),
        )
        .group_by(MessageThread.source_type)
        .order_by(func.count().desc())
    )

    return {
        "wa_total_accounts": wa_accounts.scalar() or 0,
        "wa_connected_accounts": wa_connected.scalar() or 0,
        "wa_error_accounts": wa_errors.scalar() or 0,
        "wa_threads": wa_threads.scalar() or 0,
        "wa_inbound_messages": wa_inbound.scalar() or 0,
        "wa_sent_replies": wa_sent.scalar() or 0,
        "wa_failed_sends": wa_failed.scalar() or 0,
        "wa_delivered": wa_delivered.scalar() or 0,
        "wa_read": wa_read.scalar() or 0,
        "wa_top_contexts": [
            {"context": r.context, "count": r.count}
            for r in wa_contexts.all()
        ],
        "channel_mix": [
            {"source": r.source_type, "count": r.count}
            for r in channel_mix.all()
        ],
    }
