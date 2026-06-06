-- Halketon — wipe all demo seed data (base + transactional)
-- Use before re-running seeds.sql from scratch (without reset.sql).
--
-- Usage:
--   psql $DATABASE_URL -f database/clear-all-seeds.sql
--   psql $DATABASE_URL -f database/seeds.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql
--
-- To refresh only tasks/projects while keeping orgs/users:
--   psql $DATABASE_URL -f database/clear-transactional.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql

begin;

-- Transactional (same order as clear-transactional.sql)
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

-- Base seed (seeds.sql)
delete from invitation_teams;
delete from invitation_categories;
delete from invitations;
delete from people_teams;
delete from people_categories;
delete from people;
delete from membership_teams;
delete from membership_categories;
delete from organization_memberships;
delete from teams;
delete from categories;
delete from organization_channels;
delete from organization_settings;
delete from users;
delete from organizations;

commit;
