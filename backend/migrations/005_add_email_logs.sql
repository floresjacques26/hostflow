-- Migration 005: Email log for lifecycle / retention emails
-- Idempotent — safe to run multiple times

CREATE TABLE IF NOT EXISTS email_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_type  VARCHAR(80)  NOT NULL,
    subject     VARCHAR(255) NOT NULL,
    provider    VARCHAR(40)  NOT NULL DEFAULT 'logging',
    status      VARCHAR(20)  NOT NULL DEFAULT 'sent',  -- sent | failed | skipped
    sent_at     TIMESTAMP,
    metadata    JSONB,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_email_logs_user_id    ON email_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_email_logs_email_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS ix_email_logs_created_at ON email_logs(created_at);

-- Composite index for dedup queries (user_id + email_type + created_at)
CREATE INDEX IF NOT EXISTS ix_email_logs_dedup
    ON email_logs(user_id, email_type, created_at)
    WHERE status = 'sent';
