-- Permisos PostgREST / Supabase roles (después de schema + seeds).
-- RLS sigue deshabilitado en schema.sql; service_role lee/escribe vía REST.

grant usage on schema public to anon, authenticated, service_role;

grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;
grant all on all routines in schema public to service_role;

grant select on all tables in schema public to anon, authenticated;
grant usage on all sequences in schema public to anon, authenticated;

alter default privileges in schema public
  grant all on tables to service_role;
alter default privileges in schema public
  grant select on tables to anon, authenticated;
alter default privileges in schema public
  grant all on sequences to service_role;
