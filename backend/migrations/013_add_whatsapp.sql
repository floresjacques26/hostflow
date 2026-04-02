-- Migration 013: WhatsApp Business integration
-- Run after 012_add_auto_send.sql

CREATE TABLE IF NOT EXISTS whatsapp_credentials (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id              INTEGER REFERENCES channels(id) ON DELETE SET NULL,

    -- Provider: meta | 360dialog (extensible)
    provider                VARCHAR(30) NOT NULL DEFAULT 'meta',

    -- Phone number in E.164 format, e.g. +5511999990000
    phone_number            VARCHAR(30) NOT NULL,

    -- Meta-specific IDs
    phone_number_id         VARCHAR(60) NOT NULL,
    business_account_id     VARCHAR(60),

    -- Encrypted access token (Fernet, same key as Gmail)
    encrypted_access_token  TEXT NOT NULL,

    -- Unique token expected in webhook GET verification (per-user random string)
    webhook_verify_token    VARCHAR(100) NOT NULL,

    -- connected | disconnected | error | pending_verification
    status                  VARCHAR(30) NOT NULL DEFAULT 'pending_verification',

    last_sync_at            TIMESTAMPTZ,
    last_error              TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One credential per user (single WhatsApp account per HostFlow account in v1)
CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_user ON whatsapp_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_channel ON whatsapp_credentials(channel_id);

-- Index to look up by phone_number_id (used in webhook routing)
CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_phone_number_id ON whatsapp_credentials(phone_number_id);
