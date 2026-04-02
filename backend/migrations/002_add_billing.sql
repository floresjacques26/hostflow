-- Migration 002: Add billing & usage tracking
-- Safe to run multiple times (idempotent DO blocks)

-- 1. Add billing columns to users table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='subscription_status') THEN
        ALTER TABLE users ADD COLUMN subscription_status VARCHAR(30) NOT NULL DEFAULT 'free';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='stripe_customer_id') THEN
        ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(100) UNIQUE;
        CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users(stripe_customer_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='stripe_subscription_id') THEN
        ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(100) UNIQUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='stripe_price_id') THEN
        ALTER TABLE users ADD COLUMN stripe_price_id VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='trial_ends_at') THEN
        ALTER TABLE users ADD COLUMN trial_ends_at TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='current_period_end') THEN
        ALTER TABLE users ADD COLUMN current_period_end TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='canceled_at') THEN
        ALTER TABLE users ADD COLUMN canceled_at TIMESTAMP;
    END IF;
END $$;

-- 2. Create usage_counters table
CREATE TABLE IF NOT EXISTS usage_counters (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month       VARCHAR(7) NOT NULL,            -- 'YYYY-MM'
    ai_responses INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_usage_user_month UNIQUE (user_id, month)
);

CREATE INDEX IF NOT EXISTS ix_usage_counters_user_id ON usage_counters(user_id);
