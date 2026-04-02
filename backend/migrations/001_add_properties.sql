-- Migration 001: Add multi-property support
-- Safe to run multiple times (uses IF NOT EXISTS / DO blocks)

-- 1. Create properties table
CREATE TABLE IF NOT EXISTS properties (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(120) NOT NULL,
    type            VARCHAR(40) NOT NULL DEFAULT 'apartamento',
    address_label   VARCHAR(200),
    check_in_time   VARCHAR(5) NOT NULL DEFAULT '14:00',
    check_out_time  VARCHAR(5) NOT NULL DEFAULT '11:00',
    daily_rate      NUMERIC(10,2),
    half_day_rate   NUMERIC(10,2),
    early_checkin_policy  TEXT,
    late_checkout_policy  TEXT,
    accepts_pets    BOOLEAN NOT NULL DEFAULT FALSE,
    has_parking     BOOLEAN NOT NULL DEFAULT FALSE,
    parking_policy  TEXT,
    house_rules     TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_properties_user_id ON properties(user_id);

-- 2. Add property_id to conversations (nullable — backward compatible)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='conversations' AND column_name='property_id'
    ) THEN
        ALTER TABLE conversations
            ADD COLUMN property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL;
        CREATE INDEX ix_conversations_property_id ON conversations(property_id);
    END IF;
END $$;

-- 3. Add property_id to templates (nullable — backward compatible)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='templates' AND column_name='property_id'
    ) THEN
        ALTER TABLE templates
            ADD COLUMN property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL;
        CREATE INDEX ix_templates_property_id ON templates(property_id);
    END IF;
END $$;
