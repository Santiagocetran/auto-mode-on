-- Halketon — clear volatile demo / runtime data
-- Keeps orgs, users, teams, categories, people, memberships, invitations, channels.
-- Safe to re-run before seeds-transactional.sql (NOT seeds.sql — orgs still exist).
--
-- Usage (Supabase SQL editor or psql):
--   psql $DATABASE_URL -f database/clear-transactional.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql
--
-- Or: ./database/refresh-demo-data.sh
--
-- Full re-seed from scratch (includes orgs/users):
--   psql $DATABASE_URL -f database/clear-all-seeds.sql
--   psql $DATABASE_URL -f database/seeds.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql

begin;

delete from proactive_outreach;
delete from recurrence_occurrences;
delete from reminders;
delete from meeting_tasks;
delete from task_drafts;
delete from task_recurrences;
delete from tasks;
delete from meetings;
delete from inbound_messages;
delete from whatsapp_sessions;
delete from project_categories;
delete from projects;

commit;
