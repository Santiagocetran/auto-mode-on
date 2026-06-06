-- Halketon — transactional demo data (tasks, projects, meetings, messages)
-- Requires base seeds.sql (orgs, users, teams, people).
-- Dates are relative to current_date so calendar/stats always look alive.
--
-- Fresh install:
--   psql $DATABASE_URL -f database/schema.sql
--   psql $DATABASE_URL -f database/seeds.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql
--
-- Refresh without touching orgs/users:
--   psql $DATABASE_URL -f database/clear-transactional.sql
--   psql $DATABASE_URL -f database/seeds-transactional.sql
--   # or: ./database/refresh-demo-data.sh

-- ---------------------------------------------------------------------------
-- Projects
-- ---------------------------------------------------------------------------

insert into projects (
  id, organization_id, team_id, name, slug, description, status,
  start_date, end_date, created_by_user_id, created_by_people_id, created_via
) values
  (
    '70111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111111',
    'Informe financiador Q2',
    'informe-financiador-q2',
    'Entrega de informe trimestral al financiador principal',
    'active',
    current_date - interval '14 days',
    current_date + interval '30 days',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    null,
    'dashboard'
  ),
  (
    '70111111-1111-1111-1111-111111111112',
    '11111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111113',
    'Taller nutrición comunitaria',
    'taller-nutricion-comunitaria',
    'Ciclo de talleres en barrios del sur — cruza nutrición y educación',
    'active',
    current_date - interval '7 days',
    current_date + interval '60 days',
    null,
    'a1111111-1111-1111-1111-111111111111',
    'whatsapp'
  ),
  (
    '70111111-1111-1111-1111-111111111113',
    '11111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111112',
    'Campaña verano territorio',
    'campana-verano-territorio',
    'Actividades de campo en verano — equipo territorio',
    'active',
    current_date - interval '3 days',
    current_date + interval '45 days',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    null,
    'dashboard'
  ),
  (
    '70111111-1111-1111-1111-111111111114',
    '11111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111111',
    'Auditoría interna 2025',
    'auditoria-interna-2025',
    'Cierre de auditoría — proyecto completado',
    'completed',
    current_date - interval '90 days',
    current_date - interval '10 days',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    null,
    'dashboard'
  ),
  (
    '70222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222',
    'f2222222-2222-2222-2222-222222222222',
    'Registro de impacto 2026',
    'registro-impacto-2026',
    null,
    'planning',
    null,
    null,
    'dddddddd-dddd-dddd-dddd-dddddddddddd',
    null,
    'dashboard'
  );

insert into project_categories (project_id, category_id, is_primary) values
  ('70111111-1111-1111-1111-111111111111', 'e1111111-1111-1111-1111-111111111113', true),
  ('70111111-1111-1111-1111-111111111112', 'e1111111-1111-1111-1111-111111111111', true),
  ('70111111-1111-1111-1111-111111111112', 'e1111111-1111-1111-1111-111111111112', false),
  ('70111111-1111-1111-1111-111111111113', 'e1111111-1111-1111-1111-111111111112', true),
  ('70111111-1111-1111-1111-111111111114', 'e1111111-1111-1111-1111-111111111113', true),
  ('70222222-2222-2222-2222-222222222222', 'e2222222-2222-2222-2222-222222222222', true);

-- ---------------------------------------------------------------------------
-- Inbound messages (WhatsApp capture demos)
-- ---------------------------------------------------------------------------

insert into inbound_messages (id, organization_id, provider, provider_message_id, sender_phone, sender_name, body, received_at) values
  (
    'b1111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    'twilio', 'SM001', '+5491112345678', 'Mateo',
    'Yo me encargo del informe para el viernes',
    now() - interval '2 days'
  ),
  (
    'b1111111-1111-1111-1111-111111111112',
    '11111111-1111-1111-1111-111111111111',
    'twilio', 'SM002', '+5491187654321', 'Ana',
    'Me encargo de coordinar el taller de nutrición para el jueves.',
    now() - interval '5 days'
  ),
  (
    'b1111111-1111-1111-1111-111111111113',
    '11111111-1111-1111-1111-111111111111',
    'twilio', 'SM003', '+5491155555555', 'Laura',
    'Necesitamos cerrar la auditoría antes del fin de mes',
    now() - interval '20 days'
  );

-- ---------------------------------------------------------------------------
-- Tasks — Fundación Esperanza
-- Spread across overdue / last week / this week / next week / month / future
-- ---------------------------------------------------------------------------

insert into tasks (
  id, organization_id, project_id, team_id, category_id, owner_id, owner_name,
  task_title, description, due_date, status, priority, source_message_id, source_type,
  source_text, confidence, created_at, updated_at
) values
  -- Overdue
  (
    'c1111111-1111-1111-1111-111111111112',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111112',
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111111',
    'a1111111-1111-1111-1111-111111111112', 'Ana',
    'Coordinar taller de nutrición',
    'Confirmar espacio y lista de asistentes',
    current_date - interval '1 day',
    'in_progress', 'normal',
    'b1111111-1111-1111-1111-111111111112', 'whatsapp',
    'Me encargo de coordinar el taller de nutrición para el jueves.',
    0.91,
    now() - interval '5 days', now() - interval '1 day'
  ),
  (
    'c1111111-1111-1111-1111-111111111116',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111113',
    'f1111111-1111-1111-1111-111111111112',
    'e1111111-1111-1111-1111-111111111112',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Relevamiento barrio sur',
    'Visita casa por casa — bloqueado por lluvia',
    current_date - interval '3 days',
    'blocked', 'high',
    null, 'manual', null, null,
    now() - interval '10 days', now() - interval '2 days'
  ),
  (
    'c1111111-1111-1111-1111-111111111117',
    '11111111-1111-1111-1111-111111111111',
    null,
    'f1111111-1111-1111-1111-111111111111',
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111113', 'Laura',
    'Firmar acta de directorio',
    null,
    current_date - interval '5 days',
    'pending', 'urgent',
    null, 'manual', null, null,
    now() - interval '14 days', now() - interval '4 days'
  ),
  -- This week
  (
    'c1111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111111',
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Preparar informe',
    'Informe mensual para financiador',
    current_date + interval '3 days',
    'pending', 'high',
    'b1111111-1111-1111-1111-111111111111', 'whatsapp',
    'Yo me encargo del informe para el viernes',
    0.94,
    now() - interval '2 days', now() - interval '2 days'
  ),
  (
    'c1111111-1111-1111-1111-111111111118',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111112',
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111112',
    'a1111111-1111-1111-1111-111111111112', 'Ana',
    'Diseñar material educativo del taller',
    'Folletos y presentación para familias',
    current_date + interval '1 day',
    'pending', 'normal',
    null, 'manual', null, null,
    now() - interval '7 days', now() - interval '3 days'
  ),
  (
    'c1111111-1111-1111-1111-111111111119',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111113',
    'f1111111-1111-1111-1111-111111111112',
    'e1111111-1111-1111-1111-111111111112',
    'a1111111-1111-1111-1111-111111111112', 'Ana',
    'Organizar logística campaña verano',
    'Transporte y refrigerios para salidas',
    current_date + interval '4 days',
    'in_progress', 'normal',
    null, 'manual', null, null,
    now() - interval '3 days', now() - interval '1 day'
  ),
  (
    'c1111111-1111-1111-1111-11111111111a',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111111',
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111113', 'Laura',
    'Revisar borrador informe financiador',
    null,
    current_date,
    'pending', 'high',
    null, 'manual', null, null,
    now() - interval '1 day', now()
  ),
  -- Next week
  (
    'c1111111-1111-1111-1111-111111111113',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111112',
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111112',
    'a1111111-1111-1111-1111-111111111112', 'Ana',
    'Imprimir material del taller',
    null,
    current_date + interval '8 days',
    'pending', 'low',
    null, 'manual', null, null,
    now() - interval '4 days', now() - interval '4 days'
  ),
  (
    'c1111111-1111-1111-1111-11111111111b',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111113',
    'f1111111-1111-1111-1111-111111111112',
    'e1111111-1111-1111-1111-111111111112',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Capacitación voluntarios campaña',
    null,
    current_date + interval '10 days',
    'pending', 'normal',
    null, 'manual', null, null,
    now() - interval '2 days', now() - interval '2 days'
  ),
  (
    'c1111111-1111-1111-1111-11111111111c',
    '11111111-1111-1111-1111-111111111111',
    null,
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111111',
    'a1111111-1111-1111-1111-111111111112', 'Ana',
    'Comprar insumos nutrición',
    'Ad-hoc — fuera de proyecto formal',
    current_date + interval '12 days',
    'pending', 'normal',
    null, 'manual', null, null,
    now() - interval '1 day', now()
  ),
  -- Later this month / next months
  (
    'c1111111-1111-1111-1111-111111111114',
    '11111111-1111-1111-1111-111111111111',
    null,
    'f1111111-1111-1111-1111-111111111111',
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111113', 'Laura',
    'Renovar certificado SSL del sitio web',
    'Vencimiento estatutario — standalone',
    current_date + interval '20 days',
    'pending', 'urgent',
    null, 'manual', null, null,
    now() - interval '6 days', now() - interval '6 days'
  ),
  (
    'c1111111-1111-1111-1111-11111111111d',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111112',
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111111',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Evaluación impacto talleres Q1',
    null,
    current_date + interval '35 days',
    'pending', 'normal',
    null, 'manual', null, null,
    now() - interval '30 days', now() - interval '30 days'
  ),
  -- Completed / cancelled (history for stats & timeline)
  (
    'c1111111-1111-1111-1111-11111111111e',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111114',
    'f1111111-1111-1111-1111-111111111111',
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111113', 'Laura',
    'Entregar documentación auditoría',
    null,
    current_date - interval '12 days',
    'done', 'high',
    'b1111111-1111-1111-1111-111111111113', 'whatsapp',
    'Necesitamos cerrar la auditoría antes del fin de mes',
    0.88,
    now() - interval '25 days', now() - interval '11 days'
  ),
  (
    'c1111111-1111-1111-1111-11111111111f',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111111',
    'f1111111-1111-1111-1111-111111111111',
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Recopilar datos Q1 financiador',
    null,
    current_date - interval '8 days',
    'done', 'normal',
    null, 'manual', null, null,
    now() - interval '20 days', now() - interval '7 days'
  ),
  (
    'c1111111-1111-1111-1111-111111111120',
    '11111111-1111-1111-1111-111111111111',
    null,
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111111',
    'a1111111-1111-1111-1111-111111111112', 'Ana',
    'Reservar salón municipal (cancelado)',
    'Evento suspendido por el municipio',
    current_date + interval '15 days',
    'cancelled', 'low',
    null, 'manual', null, null,
    now() - interval '15 days', now() - interval '9 days'
  ),
  -- No due date
  (
    'c1111111-1111-1111-1111-111111111121',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111113',
    'f1111111-1111-1111-1111-111111111112',
    'e1111111-1111-1111-1111-111111111112',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Actualizar mapa de referentes barriales',
    'Sin fecha — backlog territorio',
    null,
    'pending', 'low',
    null, 'manual', null, null,
    now() - interval '45 days', now() - interval '45 days'
  );

-- Global tasks (org-wide)
insert into tasks (
  id, organization_id, project_id, is_global, team_id, category_id, owner_id, owner_name,
  task_title, description, due_date, status, priority, source_type, created_at
) values
  (
    'c1111111-1111-1111-1111-111111111115',
    '11111111-1111-1111-1111-111111111111',
    null, true, null,
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111113', 'Laura',
    'Renovar personería jurídica de la fundación',
    'Trámite institucional — toda la organización',
    current_date + interval '45 days',
    'pending', 'high', 'manual',
    now() - interval '60 days'
  ),
  (
    'c1111111-1111-1111-1111-111111111122',
    '11111111-1111-1111-1111-111111111111',
    null, true, null,
    'e1111111-1111-1111-1111-111111111113',
    'a1111111-1111-1111-1111-111111111111', 'Mateo',
    'Actualizar política de protección de datos',
    'Revisión anual obligatoria',
    current_date + interval '14 days',
    'in_progress', 'high', 'manual',
    now() - interval '10 days'
  );

-- ---------------------------------------------------------------------------
-- Tasks — Red Comunitaria Norte
-- ---------------------------------------------------------------------------

insert into tasks (
  id, organization_id, project_id, team_id, category_id, owner_id, owner_name,
  task_title, due_date, status, priority, source_type, created_at
) values
  (
    'c2222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222',
    '70222222-2222-2222-2222-222222222222',
    'f2222222-2222-2222-2222-222222222222',
    'e2222222-2222-2222-2222-222222222222',
    'a2222222-2222-2222-2222-222222222222', 'Carlos',
    'Cargar actividades del mes',
    current_date + interval '5 days',
    'pending', 'normal', 'manual',
    now() - interval '3 days'
  ),
  (
    'c2222222-2222-2222-2222-222222222223',
    '22222222-2222-2222-2222-222222222222',
    '70222222-2222-2222-2222-222222222222',
    'f2222222-2222-2222-2222-222222222222',
    'e2222222-2222-2222-2222-222222222222',
    'a3333333-3333-3333-3333-333333333333', 'Mateo',
    'Revisar indicadores de impacto',
    current_date - interval '2 days',
    'in_progress', 'high', 'manual',
    now() - interval '8 days'
  ),
  (
    'c2222222-2222-2222-2222-222222222224',
    '22222222-2222-2222-2222-222222222222',
    null,
    'f2222222-2222-2222-2222-222222222222',
    'e2222222-2222-2222-2222-222222222222',
    'a2222222-2222-2222-2222-222222222222', 'Carlos',
    'Coordinar reunión con aliados',
    current_date + interval '9 days',
    'pending', 'normal', 'manual',
    now() - interval '1 day'
  );

-- ---------------------------------------------------------------------------
-- Meetings
-- ---------------------------------------------------------------------------

insert into meetings (id, organization_id, project_id, team_id, category_id, title, transcript, summary, created_at) values
  (
    'd1111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111112',
    'f1111111-1111-1111-1111-111111111113',
    'e1111111-1111-1111-1111-111111111111',
    'Reunión semanal equipo',
    'Laura: Ana, ¿podés confirmar el espacio para el taller? Ana: Sí, lo hago mañana.',
    'Se acordó confirmar el espacio del taller de nutrición.',
    now() - interval '5 days'
  ),
  (
    'd1111111-1111-1111-1111-111111111112',
    '11111111-1111-1111-1111-111111111111',
    '70111111-1111-1111-1111-111111111113',
    'f1111111-1111-1111-1111-111111111112',
    'e1111111-1111-1111-1111-111111111112',
    'Planificación campaña verano',
    'Mateo: Necesitamos dos salidas por semana. Ana: Organizo logística.',
    'Definir calendario de salidas y responsables.',
    now() - interval '3 days'
  );

insert into meeting_tasks (meeting_id, task_id) values
  ('d1111111-1111-1111-1111-111111111111', 'c1111111-1111-1111-1111-111111111112'),
  ('d1111111-1111-1111-1111-111111111112', 'c1111111-1111-1111-1111-111111111119');

-- ---------------------------------------------------------------------------
-- Reminders (due, not yet sent)
-- ---------------------------------------------------------------------------

insert into reminders (task_id, scheduled_at, idempotency_key) values
  ('c1111111-1111-1111-1111-111111111112', now() + interval '1 hour', 'reminder:send:c1111111-1111-1111-1111-111111111112:initial'),
  ('c1111111-1111-1111-1111-111111111117', now() + interval '30 minutes', 'reminder:send:c1111111-1111-1111-1111-111111111117:initial');

-- ---------------------------------------------------------------------------
-- Task recurrence (suggested template from completed task pattern)
-- ---------------------------------------------------------------------------

insert into task_recurrences (
  id, organization_id, title_template, project_id, team_id, category_id,
  owner_id, interval_unit, interval_count, status, next_occurrence_on,
  suggested_from_task_id, created_by_user_id
) values (
  '80111111-1111-1111-1111-111111111111',
  '11111111-1111-1111-1111-111111111111',
  'Informe mensual financiador',
  '70111111-1111-1111-1111-111111111111',
  'f1111111-1111-1111-1111-111111111111',
  'e1111111-1111-1111-1111-111111111113',
  'a1111111-1111-1111-1111-111111111111',
  'monthly', 1, 'suggested',
  current_date + interval '30 days',
  'c1111111-1111-1111-1111-11111111111f',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
);
