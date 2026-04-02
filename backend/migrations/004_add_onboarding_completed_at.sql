-- Migration 004: Add onboarding_completed_at to users
-- Idempotent — safe to run multiple times

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'onboarding_completed_at'
    ) THEN
        ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP;
    END IF;
END $$;
