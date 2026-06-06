-- Halketon — migration 002: WhatsApp confirmation gate
-- Apply on databases that already ran schema.sql before the confirmation gate landed.
--
-- Adds an 'awaiting_confirmation' draft state so a task is only written to `tasks`
-- after the sender replies "si". Previously "¿Confirmás?" was cosmetic: the task was
-- inserted immediately and the reply ("si") fell through to a fresh extraction.
--
-- Usage (Supabase SQL editor or psql):
--   database/migrations/002_confirmation_gate.sql
--
-- NOTE: Postgres forbids *using* a freshly-added enum value in the same transaction
-- that adds it. The index predicates below compare status::text against string
-- literals (never the enum literal), so this whole file runs safely as one script.
--
-- Rollback (dev only — cannot drop an enum value once present; leave it in place):
--   drop index if exists task_drafts_one_pending;
--   drop index if exists task_drafts_sender_pending_idx;
--   create unique index task_drafts_one_pending
--     on task_drafts (organization_id, sender_phone)
--     where status = 'awaiting_project_choice';
--   create index task_drafts_sender_pending_idx
--     on task_drafts (organization_id, sender_phone)
--     where status = 'awaiting_project_choice';
--   alter table task_drafts drop column if exists resolved_task;

-- 1. New conversation state.
alter type task_draft_status add value if not exists 'awaiting_confirmation'
  after 'awaiting_project_choice';

-- 2. Staging column for the resolved task row (inserted into `tasks` on "si").
alter table task_drafts add column if not exists resolved_task jsonb;

-- 3. Both pending states count as an open conversation: one per sender per org.
drop index if exists task_drafts_one_pending;
drop index if exists task_drafts_sender_pending_idx;

create index task_drafts_sender_pending_idx
  on task_drafts (organization_id, sender_phone)
  where status::text in ('awaiting_project_choice', 'awaiting_confirmation');

create unique index task_drafts_one_pending
  on task_drafts (organization_id, sender_phone)
  where status::text in ('awaiting_project_choice', 'awaiting_confirmation');
