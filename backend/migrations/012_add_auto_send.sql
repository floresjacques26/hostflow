-- Migration 012: Auto-send rules + decision audit log
-- Run after 011_add_template_context.sql

-- ── Auto-send rules ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auto_send_rules (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Scope filters (NULL = match all)
    property_id     INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    channel_type    VARCHAR(30),           -- gmail | manual | whatsapp | NULL
    context_key     VARCHAR(40),           -- checkin | checkout | pets | … | NULL

    -- Optional: require a specific template to be matched before auto-send
    template_id     INTEGER REFERENCES templates(id) ON DELETE SET NULL,

    -- Confidence threshold (0.0–1.0); message confidence must be ≥ this value
    min_confidence  NUMERIC(4,3) NOT NULL DEFAULT 0.85,

    -- If True, auto-send is blocked when no template matched
    require_template_match BOOLEAN NOT NULL DEFAULT TRUE,

    -- Time window: only auto-send between these hours (UTC, 0–23; NULL = any hour)
    allowed_start_hour  SMALLINT,
    allowed_end_hour    SMALLINT,

    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auto_send_rules_user ON auto_send_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_auto_send_rules_user_active ON auto_send_rules(user_id, active);

-- ── Auto-send decision log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auto_send_decision_logs (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id       INTEGER NOT NULL REFERENCES message_threads(id) ON DELETE CASCADE,
    template_id     INTEGER REFERENCES templates(id) ON DELETE SET NULL,
    matched_rule_id INTEGER REFERENCES auto_send_rules(id) ON DELETE SET NULL,

    -- decision: sent | blocked | manual_review
    decision        VARCHAR(20) NOT NULL,
    -- reason codes: no_rule | low_confidence | no_template | risky_keyword |
    --               blocked_category | message_too_long | complaint_sentiment |
    --               outside_time_window | ok
    reason_code     VARCHAR(40) NOT NULL,
    reason_message  TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auto_send_log_user ON auto_send_decision_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_auto_send_log_thread ON auto_send_decision_logs(thread_id);
CREATE INDEX IF NOT EXISTS idx_auto_send_log_created ON auto_send_decision_logs(created_at DESC);

-- ── Extend message_threads ────────────────────────────────────────────────────
ALTER TABLE message_threads
    ADD COLUMN IF NOT EXISTS auto_send_decision   VARCHAR(20),  -- sent | blocked | manual_review | NULL
    ADD COLUMN IF NOT EXISTS auto_send_rule_id    INTEGER REFERENCES auto_send_rules(id) ON DELETE SET NULL;
