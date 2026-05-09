-- SmartSleep Database Migration
-- Run this in Supabase SQL Editor before deploying the updated backend.

-- 1. Add new computed columns to derived_sleep_data
ALTER TABLE derived_sleep_data
    ADD COLUMN IF NOT EXISTS tib        FLOAT,
    ADD COLUMN IF NOT EXISTS tst        FLOAT,
    ADD COLUMN IF NOT EXISTS bio_ready  FLOAT,
    ADD COLUMN IF NOT EXISTS psych_load FLOAT,
    ADD COLUMN IF NOT EXISTS env_score  FLOAT;

-- 2. training_data table — stores per-user labeled samples for online learning
CREATE TABLE IF NOT EXISTS training_data (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    derived_id  UUID NOT NULL,
    date        DATE NOT NULL,
    features    JSONB NOT NULL,
    user_score  FLOAT,
    user_class  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_training_data_user_id ON training_data(user_id);

-- 3. model_artifact table (create if not already present)
CREATE TABLE IF NOT EXISTS model_artifact (
    model_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    training_samples       INT DEFAULT 0,
    last_trained           TIMESTAMPTZ,
    regression_model_path  TEXT,
    classifier_model_path  TEXT,
    current_learning_factor FLOAT DEFAULT 0.0,
    created_at             TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Ensure user_stat has hrv and body_temp stat columns
ALTER TABLE user_stat
    ADD COLUMN IF NOT EXISTS mean_hrv       FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS std_hrv        FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS mean_body_temp FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS std_body_temp  FLOAT DEFAULT 0.0;
