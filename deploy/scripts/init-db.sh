#!/bin/sh
set -eu

echo "Waiting for Postgres..."
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; do
  sleep 1
done

echo "Waiting for GoTrue auth schema..."
for _ in $(seq 1 60); do
  if psql -tAc "SELECT EXISTS (SELECT FROM information_schema.schemata WHERE schema_name = 'auth')" | grep -q t; then
    break
  fi
  sleep 2
done

if psql -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organizations')" | grep -q t; then
  echo "Schema already applied — skipping init."
  exit 0
fi

echo "Applying database/schema.sql..."
psql -v ON_ERROR_STOP=1 -f /schema/schema.sql

echo "Applying database/seeds.sql..."
psql -v ON_ERROR_STOP=1 -f /schema/seeds.sql

echo "Applying deploy/postgres/grants.sql..."
psql -v ON_ERROR_STOP=1 -f /grants/grants.sql

echo "Applying database/seeds-auth.sql..."
psql -v ON_ERROR_STOP=1 -f /schema/seeds-auth.sql

echo "Database init complete."
