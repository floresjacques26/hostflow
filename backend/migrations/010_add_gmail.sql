-- ============================================================
-- Migration 010: Gmail OAuth + sync fields
-- ============================================================

-- Gmail OAuth credentials (one per user)
CREATE TABLE IF NOT EXISTS gmail_credentials (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gmail_email             VARCHAR(255) NOT NULL,
    encrypted_access_token  TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_expires_at        TIMESTAMP,
    scopes                  TEXT,
    sync_enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at            TIMESTAMP,
    sync_error              TEXT,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_gmail_credentials_user_id
    ON gmail_credentials (user_id);

-- External linkage fields on message_threads
ALTER TABLE message_threads
    ADD COLUMN IF NOT EXISTS external_thread_id  VARCHAR(200),
    ADD COLUMN IF NOT EXISTS external_source_id  VARCHAR(200),
    ADD COLUMN IF NOT EXISTS sync_status         VARCHAR(20) DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS last_synced_at      TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS idx_message_threads_external_thread_id
    ON message_threads (user_id, external_thread_id)
    WHERE external_thread_id IS NOT NULL;

-- External linkage + delivery fields on message_entries
ALTER TABLE message_entries
    ADD COLUMN IF NOT EXISTS external_message_id VARCHAR(200),
    ADD COLUMN IF NOT EXISTS sent_via_provider   BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS delivery_status     VARCHAR(20);

CREATE UNIQUE INDEX IF NOT EXISTS idx_message_entries_external_message_id
    ON message_entries (external_message_id)
    WHERE external_message_id IS NOT NULL;
