-- Adds parse-stage tracking columns to corporate_actions.
--
-- Run with:  psql "$SUPABASE_DB_URL" -f 001_parse_stage_columns.sql
-- or via the Supabase SQL editor. Idempotent; safe to re-run.

ALTER TABLE corporate_actions
  ADD COLUMN IF NOT EXISTS parsed_at        TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS chunk_count      INTEGER NULL,
  ADD COLUMN IF NOT EXISTS parse_error      TEXT NULL,
  ADD COLUMN IF NOT EXISTS parse_attempts   INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS corporate_actions_parsed_pending_idx
  ON corporate_actions (id)
  WHERE local_pdf_path IS NOT NULL AND parsed_at IS NULL;

CREATE INDEX IF NOT EXISTS corporate_actions_ingest_pending_idx
  ON corporate_actions (id)
  WHERE parsed_at IS NOT NULL AND ingested_at IS NULL;
