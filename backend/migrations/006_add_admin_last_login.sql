-- Migration 006: Admin flag + last login tracking
-- Idempotent — safe to run multiple times

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'is_admin'
    ) THEN
        ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'last_login_at'
    ) THEN
        ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
    END IF;
END $$;

-- Index for admin lookups
CREATE INDEX IF NOT EXISTS ix_users_is_admin ON users(is_admin) WHERE is_admin = TRUE;

-- Promote the first user to admin (safe for initial setup — adjust email if needed)
-- Uncomment and edit to bootstrap your admin account:
-- UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';
