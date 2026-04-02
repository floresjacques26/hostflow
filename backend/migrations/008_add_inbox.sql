-- Migration 008: integrations / inbox layer
-- channels, message_threads, message_entries tables

-- ── Channels ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS channels (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id  INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    type         VARCHAR(30) NOT NULL DEFAULT 'manual',
    name         VARCHAR(120) NOT NULL,
    external_id  VARCHAR(200),
    status       VARCHAR(20) NOT NULL DEFAULT 'active',
    config_json  JSONB,
    created_at   TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_channels_user_id ON channels(user_id);

-- ── Message Threads ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS message_threads (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id       INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    channel_id        INTEGER REFERENCES channels(id) ON DELETE SET NULL,
    subject           VARCHAR(255),
    guest_name        VARCHAR(120),
    guest_contact     VARCHAR(200),
    source_type       VARCHAR(30) NOT NULL DEFAULT 'manual',
    status            VARCHAR(20) NOT NULL DEFAULT 'open',
    detected_context  VARCHAR(40),
    draft_status      VARCHAR(30) NOT NULL DEFAULT 'none',
    tags              VARCHAR(300),
    last_message_at   TIMESTAMP,
    created_at        TIMESTAMP NOT NULL DEFAULT now(),
    updated_at        TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_message_threads_user_id          ON message_threads(user_id);
CREATE INDEX IF NOT EXISTS ix_message_threads_status           ON message_threads(status);
CREATE INDEX IF NOT EXISTS ix_message_threads_detected_context ON message_threads(detected_context);
CREATE INDEX IF NOT EXISTS ix_message_threads_last_message_at  ON message_threads(last_message_at DESC);

-- ── Message Entries ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS message_entries (
    id           SERIAL PRIMARY KEY,
    thread_id    INTEGER NOT NULL REFERENCES message_threads(id) ON DELETE CASCADE,
    direction    VARCHAR(20) NOT NULL,
    body         TEXT NOT NULL,
    raw_payload  JSONB,
    sender_name  VARCHAR(120),
    created_at   TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_message_entries_thread_id   ON message_entries(thread_id);
CREATE INDEX IF NOT EXISTS ix_message_entries_created_at  ON message_entries(created_at);
CREATE INDEX IF NOT EXISTS ix_message_entries_direction   ON message_entries(direction);
