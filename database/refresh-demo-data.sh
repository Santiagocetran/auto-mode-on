#!/usr/bin/env bash
# Wipe tasks, projects, messages, etc. and reload rich demo data.
# Does NOT touch orgs, users, teams, people, or auth.
#
# Usage:
#   DATABASE_URL='postgresql://...' ./database/refresh-demo-data.sh

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: set DATABASE_URL to your Postgres connection string." >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Clearing transactional data..."
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "${script_dir}/clear-transactional.sql"

echo "Loading demo tasks, projects, meetings..."
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "${script_dir}/seeds-transactional.sql"

echo "Done. Demo data refreshed."
