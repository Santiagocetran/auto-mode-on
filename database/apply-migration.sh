#!/usr/bin/env bash
# Apply a SQL migration file to Postgres (Supabase remote or local).
#
# Usage:
#   DATABASE_URL='postgresql://postgres.[ref]:[password]@...' ./database/apply-migration.sh 002_confirmation_gate.sql
#
# Get DATABASE_URL from Supabase → Project Settings → Database → Connection string (URI).

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: set DATABASE_URL to your Postgres connection string." >&2
  exit 1
fi

migration_file="${1:-002_confirmation_gate.sql}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sql_path="${script_dir}/migrations/${migration_file}"

if [[ ! -f "$sql_path" ]]; then
  echo "ERROR: migration not found: $sql_path" >&2
  exit 1
fi

echo "Applying ${sql_path} ..."
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$sql_path"
echo "Done."
