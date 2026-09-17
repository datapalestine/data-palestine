-- Idempotent migration for existing (hand-drifted) databases, e.g. production.
-- A fresh DB built from packages/db/schema.sql already has these columns.
-- Alembic is currently a stub (apps/api/alembic/ has no versions/env.py) --
-- until a real migration mechanism is wired into the deploy pipeline, run
-- this by hand against a target database:
--   psql "$DATABASE_URL_SYNC" -f packages/db/migrations/002_add_curation_soft_delete.sql

ALTER TABLE datasets ADD COLUMN IF NOT EXISTS quality_status VARCHAR(20) DEFAULT 'needs_review';
ALTER TABLE indicators ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
