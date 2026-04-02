-- Migration 007: acquisition engine
-- referral_code + attribution fields on users, referrals, partners, testimonials tables

-- ── Users: acquisition fields ────────────────────────────────────────────────

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20),
  ADD COLUMN IF NOT EXISTS referred_by_user_id INTEGER REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS partner_code VARCHAR(50),
  ADD COLUMN IF NOT EXISTS utm_source VARCHAR(100),
  ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(100),
  ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(100);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_referral_code ON users(referral_code) WHERE referral_code IS NOT NULL;

-- ── Referrals ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS referrals (
    id                 SERIAL PRIMARY KEY,
    referrer_user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_user_id   INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    referral_code      VARCHAR(20) NOT NULL,
    status             VARCHAR(20) NOT NULL DEFAULT 'pending',
    reward_type        VARCHAR(30),
    reward_value       INTEGER,
    rewarded_at        TIMESTAMP,
    created_at         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_referrals_referrer ON referrals(referrer_user_id);
CREATE INDEX IF NOT EXISTS ix_referrals_status    ON referrals(status);

-- ── Partners ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS partners (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    code             VARCHAR(50)  NOT NULL UNIQUE,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    commission_type  VARCHAR(20),
    commission_value INTEGER,
    contact_email    VARCHAR(255),
    notes            VARCHAR(500),
    created_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_partners_code ON partners(code);

-- ── Testimonials ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS testimonials (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating                INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    quote                 VARCHAR(500) NOT NULL,
    trigger_event         VARCHAR(50),
    status                VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_for_public_use BOOLEAN NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_testimonials_user_id ON testimonials(user_id);
CREATE INDEX IF NOT EXISTS ix_testimonials_status  ON testimonials(status);
