-- ============================================================
-- Ken Research — WhatsApp Campaign Automation
-- Paste this entire file into Supabase → SQL Editor → Run
-- ============================================================

-- Campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    messages        JSONB NOT NULL DEFAULT '{"step_1":"","step_2":"","step_3":""}',
    delay_days      INTEGER NOT NULL DEFAULT 1,
    delay_hours     INTEGER NOT NULL DEFAULT 0,
    delay_minutes   INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft | active | paused | completed
    created_by      TEXT DEFAULT 'team',
    stats           JSONB NOT NULL DEFAULT '{"total":0,"sent":0,"replied":0,"completed":0}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    phone_number    TEXT NOT NULL,
    first_name      TEXT DEFAULT 'there',
    company         TEXT DEFAULT '',
    current_step    INTEGER NOT NULL DEFAULT 1,     -- 1, 2, or 3
    status          TEXT NOT NULL DEFAULT 'active', -- active | replied | completed | stopped
    next_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    messages_sent   JSONB NOT NULL DEFAULT '[]',    -- [{step, sent_at, unique_id}]
    replied_at      TIMESTAMPTZ,
    reply_body      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_contacts_campaign_id ON contacts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_contacts_status      ON contacts(status);
CREATE INDEX IF NOT EXISTS idx_contacts_next_msg    ON contacts(next_message_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_status     ON campaigns(status);

-- Prevent duplicate phone numbers within the same campaign
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_unique_phone
    ON contacts(campaign_id, phone_number);
