-- Migration 009: inbox enhancements
-- guest_profiles, guest_profile_id on threads, pg_trgm for search

-- ── pg_trgm extension for fast ILIKE / fuzzy search ──────────────────────────

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── Trigram indexes on message_threads for search ─────────────────────────────

CREATE INDEX IF NOT EXISTS ix_message_threads_trgm_subject
    ON message_threads USING GIN (subject gin_trgm_ops)
    WHERE subject IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_message_threads_trgm_guest_name
    ON message_threads USING GIN (guest_name gin_trgm_ops)
    WHERE guest_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_message_threads_trgm_guest_contact
    ON message_threads USING GIN (guest_contact gin_trgm_ops)
    WHERE guest_contact IS NOT NULL;

-- ── Trigram index on message_entries body ─────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_message_entries_trgm_body
    ON message_entries USING GIN (body gin_trgm_ops);

-- ── Guest Profiles ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS guest_profiles (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name           VARCHAR(120),
    primary_email  VARCHAR(255),
    primary_phone  VARCHAR(30),
    notes          TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT now(),
    updated_at     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_guest_profiles_user_id       ON guest_profiles(user_id);
CREATE INDEX IF NOT EXISTS ix_guest_profiles_primary_email ON guest_profiles(primary_email) WHERE primary_email IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_guest_profiles_primary_phone ON guest_profiles(primary_phone) WHERE primary_phone IS NOT NULL;

-- Unique per user: one profile per email, one per phone
CREATE UNIQUE INDEX IF NOT EXISTS uq_guest_profile_email
    ON guest_profiles(user_id, primary_email) WHERE primary_email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_guest_profile_phone
    ON guest_profiles(user_id, primary_phone) WHERE primary_phone IS NOT NULL;

-- ── Link message_threads to guest_profiles ────────────────────────────────────

ALTER TABLE message_threads
    ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER REFERENCES guest_profiles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_message_threads_guest_profile_id
    ON message_threads(guest_profile_id) WHERE guest_profile_id IS NOT NULL;
