-- Migration 014: Media attachments + WhatsApp message templates
-- Run after 013_add_whatsapp.sql

-- ── Media attachments ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS media_attachments (
    id                  SERIAL PRIMARY KEY,
    entry_id            INTEGER NOT NULL REFERENCES message_entries(id) ON DELETE CASCADE,

    -- channel/integration that produced this attachment
    provider            VARCHAR(30) NOT NULL DEFAULT 'whatsapp',  -- whatsapp | gmail | upload

    -- image | audio | document | video | sticker | unknown
    media_type          VARCHAR(20) NOT NULL DEFAULT 'unknown',

    -- MIME type, e.g. image/jpeg, audio/ogg; codecs=opus, application/pdf
    mime_type           VARCHAR(100),

    -- Original filename from provider (may be null for images/audio)
    file_name           VARCHAR(255),

    -- Provider-specific media ID (Meta wamid for media, Gmail attachment ID, etc.)
    external_media_id   VARCHAR(200),

    -- File size in bytes (set after download)
    file_size           BIGINT,

    -- Storage object key (e.g. media/2024/01/uuid.jpg) — null until uploaded to storage
    storage_key         VARCHAR(500),

    -- Pre-computed public URL or flag to use signed URL flow
    -- Null = generate signed URL on demand; non-null = permanent CDN URL
    public_url          TEXT,

    -- Future: audio transcript (Whisper), OCR text (Tesseract/Vision)
    transcript_text     TEXT,
    extracted_text      TEXT,

    -- download_pending | downloaded | upload_failed | ready | error
    status              VARCHAR(20) NOT NULL DEFAULT 'download_pending',

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_entry ON media_attachments(entry_id);
CREATE INDEX IF NOT EXISTS idx_media_ext ON media_attachments(external_media_id);

-- ── WhatsApp message templates ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS wa_message_templates (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Template name as registered in Meta Business Manager
    provider_template_name  VARCHAR(200) NOT NULL,

    -- BCP 47 language code, e.g. pt_BR, en_US
    language_code           VARCHAR(10) NOT NULL DEFAULT 'pt_BR',

    -- AUTHENTICATION | MARKETING | UTILITY
    category                VARCHAR(30) NOT NULL DEFAULT 'UTILITY',

    -- Full components JSON as returned by Meta API (or manually authored)
    -- Structure: [{type: HEADER|BODY|FOOTER|BUTTONS, ...}]
    components_json         JSONB,

    active                  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wa_tpl_user ON wa_message_templates(user_id);

-- ── Extend message_threads ────────────────────────────────────────────────────
-- Track when the last inbound (customer) message arrived for 24h window calculation
ALTER TABLE message_threads
    ADD COLUMN IF NOT EXISTS last_inbound_at TIMESTAMPTZ;

-- ── Extend message_entries ────────────────────────────────────────────────────
-- Track whether this entry is a WA template send (vs free-form text)
ALTER TABLE message_entries
    ADD COLUMN IF NOT EXISTS is_template_message BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS template_name VARCHAR(200);
