-- Halketon — migration 002: WhatsApp confirmation gate (step 1 of 2)
-- Apply on databases that already ran schema.sql before the confirmation gate landed.
--
-- Step 1: enum value + staging column.
-- Step 2: run 003_confirmation_gate_indexes.sql in a **separate** SQL Editor session
--         (Postgres forbids using a new enum value in the same transaction that adds it).
--
-- Usage (Supabase SQL editor — run this file alone, then 003):
--   database/migrations/002_confirmation_gate.sql
--   database/migrations/003_confirmation_gate_indexes.sql
--
-- Or via psql (each file is its own transaction when run separately):
--   DATABASE_URL='postgresql://...' ./database/apply-migration.sh 002_confirmation_gate.sql
--   DATABASE_URL='postgresql://...' ./database/apply-migration.sh 003_confirmation_gate_indexes.sql

alter type task_draft_status add value if not exists 'awaiting_confirmation'
  after 'awaiting_project_choice';

alter table task_drafts add column if not exists resolved_task jsonb;
