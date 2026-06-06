-- Halketon — base demo seed (orgs, users, teams, people — no tasks/projects)
-- Run after schema:
--   psql $DATABASE_URL -f database/schema.sql
--   psql $DATABASE_URL -f database/seeds.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql   ← tasks, fechas, meetings
--   psql $DATABASE_URL -f database/seeds-auth.sql            ← Supabase Auth (opcional)
--
-- Refrescar solo tareas/proyectos sin tocar usuarios:
--   ./database/refresh-demo-data.sh
--
-- Re-ejecutar seeds.sql sobre una DB ya poblada (duplicate key):
--   psql $DATABASE_URL -f database/clear-all-seeds.sql
--   psql $DATABASE_URL -f database/seeds.sql

-- ---------------------------------------------------------------------------
-- Organizations
-- ---------------------------------------------------------------------------

insert into organizations (id, name, slug, status) values
  ('11111111-1111-1111-1111-111111111111', 'Fundación Esperanza', 'fundacion-esperanza', 'active'),
  ('22222222-2222-2222-2222-222222222222', 'Red Comunitaria Norte', 'red-comunitaria-norte', 'active');

-- organization_settings rows are auto-created by trigger; customize one org:
update organization_settings
set features = features || '{"beneficiary_tracking": true}'::jsonb
where organization_id = '22222222-2222-2222-2222-222222222222';

-- ---------------------------------------------------------------------------
-- WhatsApp channels (one Twilio number per org)
-- ---------------------------------------------------------------------------

insert into organization_channels (id, organization_id, whatsapp_number, display_name) values
  ('c0111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'whatsapp:+14155238886', 'Fundación Esperanza'),
  ('c0222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'whatsapp:+14155238887', 'Red Comunitaria Norte');

-- ---------------------------------------------------------------------------
-- Teams & categories (Fundación Esperanza)
-- ---------------------------------------------------------------------------

insert into teams (id, organization_id, name, slug, description, color) values
  ('f1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'Coordinación', 'coordinacion', 'Equipo de coordinación general', '#2563eb'),
  ('f1111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'Territorio',     'territorio',     'Trabajo en territorio',          '#16a34a'),
  ('f1111111-1111-1111-1111-111111111113', '11111111-1111-1111-1111-111111111111', 'Voluntariado',   'voluntariado',   'Voluntarios y talleristas',      '#9333ea');

insert into categories (id, organization_id, name, slug, description, color) values
  ('e1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'Nutrición',       'nutricion',       'Programa de nutrición comunitaria', '#ea580c'),
  ('e1111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'Educación',       'educacion',       'Talleres y capacitaciones',         '#0891b2'),
  ('e1111111-1111-1111-1111-111111111113', '11111111-1111-1111-1111-111111111111', 'Administración',  'administracion',  'Informes, financiadores, gestión',  '#64748b');

-- Red Comunitaria Norte (single team + category for demo)
insert into teams (id, organization_id, name, slug) values
  ('f2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'Operaciones', 'operaciones');

insert into categories (id, organization_id, name, slug) values
  ('e2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'Impacto', 'impacto');

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------

insert into users (id, email, display_name, notification_email) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'directora@esperanza.org', 'Laura Méndez', 'directora@esperanza.org'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'coord@esperanza.org', 'Mateo Barbato', 'coord@esperanza.org'),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'voluntaria@esperanza.org', 'Ana Ruiz', 'voluntaria@esperanza.org'),
  ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'admin@rednorte.org', 'Carlos Vega', 'admin@rednorte.org');

-- ---------------------------------------------------------------------------
-- Memberships (role hierarchy)
-- ---------------------------------------------------------------------------

insert into organization_memberships (id, organization_id, user_id, role, status, joined_at, tasks_scope_override, primary_team_id, primary_category_id) values
  ('b0111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'owner',   'active', now() - interval '90 days', null, 'f1111111-1111-1111-1111-111111111111', null),
  ('b0111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'manager', 'active', now() - interval '60 days', 'team', 'f1111111-1111-1111-1111-111111111111', 'e1111111-1111-1111-1111-111111111113'),
  ('b0111111-1111-1111-1111-111111111113', '11111111-1111-1111-1111-111111111111', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'member',  'active', now() - interval '30 days', null, 'f1111111-1111-1111-1111-111111111113', 'e1111111-1111-1111-1111-111111111111'),
  ('b0222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'owner',   'active', now() - interval '45 days', null, 'f2222222-2222-2222-2222-222222222222', 'e2222222-2222-2222-2222-222222222222');

-- Membership ↔ teams / categories
insert into membership_teams (membership_id, team_id) values
  ('b0111111-1111-1111-1111-111111111111', 'f1111111-1111-1111-1111-111111111111'),
  ('b0111111-1111-1111-1111-111111111112', 'f1111111-1111-1111-1111-111111111111'),
  ('b0111111-1111-1111-1111-111111111113', 'f1111111-1111-1111-1111-111111111113');

insert into membership_categories (membership_id, category_id) values
  ('b0111111-1111-1111-1111-111111111112', 'e1111111-1111-1111-1111-111111111113'),
  ('b0111111-1111-1111-1111-111111111113', 'e1111111-1111-1111-1111-111111111111');

-- ---------------------------------------------------------------------------
-- Pending invitation (shareable link demo)
-- Token is fixed for reproducible demos: /invite/demo-invite-token-esperanza
-- ---------------------------------------------------------------------------

insert into invitations (id, organization_id, email, role, token, invited_by, status, expires_at) values
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
    '11111111-1111-1111-1111-111111111111',
    'nuevo@esperanza.org',
    'member',
    'demo-invite-token-esperanza',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'pending',
    now() + interval '7 days'
  );

insert into invitation_teams (invitation_id, team_id) values
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'f1111111-1111-1111-1111-111111111113');

insert into invitation_categories (invitation_id, category_id) values
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'e1111111-1111-1111-1111-111111111111');

-- ---------------------------------------------------------------------------
-- People (WhatsApp-linked, linked to dashboard users where applicable)
-- ---------------------------------------------------------------------------

insert into people (id, organization_id, display_name, whatsapp_number, role_label, user_id) values
  ('a1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'Mateo',  '+5491112345678', 'Coordinador', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
  ('a1111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'Ana',    '+5491187654321', 'Voluntaria',  'cccccccc-cccc-cccc-cccc-cccccccccccc'),
  ('a1111111-1111-1111-1111-111111111113', '11111111-1111-1111-1111-111111111111', 'Laura',  '+5491155555555', 'Directora',   'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
  ('a2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'Carlos', '+5491144444444', 'Admin',       'dddddddd-dddd-dddd-dddd-dddddddddddd'),
  -- Same phone in two orgs (edge case): must use the correct Twilio number per org
  ('a3333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 'Mateo',  '+5491112345678', 'Consultor externo', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');

insert into people_teams (people_id, team_id) values
  ('a1111111-1111-1111-1111-111111111111', 'f1111111-1111-1111-1111-111111111111'),
  ('a1111111-1111-1111-1111-111111111112', 'f1111111-1111-1111-1111-111111111113'),
  ('a1111111-1111-1111-1111-111111111113', 'f1111111-1111-1111-1111-111111111111'),
  ('a2222222-2222-2222-2222-222222222222', 'f2222222-2222-2222-2222-222222222222');

insert into people_categories (people_id, category_id) values
  ('a1111111-1111-1111-1111-111111111111', 'e1111111-1111-1111-1111-111111111113'),
  ('a1111111-1111-1111-1111-111111111112', 'e1111111-1111-1111-1111-111111111111'),
  ('a2222222-2222-2222-2222-222222222222', 'e2222222-2222-2222-2222-222222222222');

-- Proyectos, tareas, meetings, mensajes → database/seeds-transactional.sql
