-- Halketon — migration 003: WhatsApp confirmation gate indexes (step 2 of 2)
--
-- Run **after** 002_confirmation_gate.sql has committed successfully.
-- Uses enum literals in index predicates (not status::text — that cast is not IMMUTABLE
-- and Supabase rejects it with ERROR 42P17).
--
-- Usage:
--   database/migrations/003_confirmation_gate_indexes.sql
--
-- Rollback (dev only):
--   drop index if exists task_drafts_one_pending;
--   drop index if exists task_drafts_sender_pending_idx;
--   create unique index task_drafts_one_pending
--     on task_drafts (organization_id, sender_phone)
--     where status = 'awaiting_project_choice';
--   create index task_drafts_sender_pending_idx
--     on task_drafts (organization_id, sender_phone)
--     where status = 'awaiting_project_choice';

drop index if exists task_drafts_one_pending;
drop index if exists task_drafts_sender_pending_idx;

create index task_drafts_sender_pending_idx
  on task_drafts (organization_id, sender_phone)
  where status in ('awaiting_project_choice', 'awaiting_confirmation');

create unique index task_drafts_one_pending
  on task_drafts (organization_id, sender_phone)
  where status in ('awaiting_project_choice', 'awaiting_confirmation');
