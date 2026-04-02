-- ============================================================
-- Migration 011: Context-aware template system
-- ============================================================

-- Add smart-match fields to templates
ALTER TABLE templates
    ADD COLUMN IF NOT EXISTS context_key   VARCHAR(40),         -- early_checkin, late_checkout, etc.
    ADD COLUMN IF NOT EXISTS channel_type  VARCHAR(30),         -- gmail, email_forward, manual, whatsapp
    ADD COLUMN IF NOT EXISTS language      VARCHAR(10),         -- pt, en, es
    ADD COLUMN IF NOT EXISTS tone          VARCHAR(30),         -- friendly, formal, brief
    ADD COLUMN IF NOT EXISTS priority      INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS auto_apply    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS active        BOOLEAN NOT NULL DEFAULT TRUE;

-- Index for fast context lookups during matching
CREATE INDEX IF NOT EXISTS idx_templates_context_key
    ON templates (context_key)
    WHERE context_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_templates_auto_apply
    ON templates (auto_apply, active)
    WHERE auto_apply = TRUE AND active = TRUE;

-- Track which template was used to generate the current draft on a thread
ALTER TABLE message_threads
    ADD COLUMN IF NOT EXISTS applied_template_id INTEGER REFERENCES templates(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS template_auto_applied BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_message_threads_applied_template
    ON message_threads (applied_template_id)
    WHERE applied_template_id IS NOT NULL;
