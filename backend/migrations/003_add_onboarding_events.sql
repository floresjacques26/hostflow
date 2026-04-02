-- Migration 003: Onboarding fields + event tracking
-- Idempotent — safe to run multiple times

-- 1. Add onboarding fields to users
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='onboarding_completed') THEN
        ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='onboarding_step') THEN
        ALTER TABLE users ADD COLUMN onboarding_step INTEGER NOT NULL DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='onboarding_started_at') THEN
        ALTER TABLE users ADD COLUMN onboarding_started_at TIMESTAMP;
    END IF;
END $$;

-- 2. Create user_events table
CREATE TABLE IF NOT EXISTS user_events (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_name  VARCHAR(80) NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_events_user_id    ON user_events(user_id);
CREATE INDEX IF NOT EXISTS ix_user_events_event_name ON user_events(event_name);
CREATE INDEX IF NOT EXISTS ix_user_events_created_at ON user_events(created_at);
