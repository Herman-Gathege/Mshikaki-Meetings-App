#!/usr/bin/env bash
# Restore a dump into the running database.
#
#   ./scripts/restore.sh backups/mshikaki-2026-10-01-2100.sql.gz
#
# This overwrites the current database, so it asks before doing anything.
# Rehearse this before you need it: an untested backup is not a backup.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Usage: $0 backups/mshikaki-YYYY-MM-DD-HHMM.sql.gz" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a && source .env && set +a

echo "This will REPLACE the contents of database '${POSTGRES_DB}' with ${DUMP}."
read -r -p "Type 'restore' to continue: " CONFIRM
[[ "$CONFIRM" == "restore" ]] || { echo "Cancelled."; exit 1; }

echo "Stopping the app so nothing writes during the restore..."
docker compose stop app

echo "Restoring..."
gunzip -c "$DUMP" | docker compose exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "Starting the app again..."
docker compose start app
sleep 10

echo "Health check:"
curl -fsS "http://localhost:${APP_PORT:-8080}/api/health/ready" && echo
echo "Restore finished. Confirm the meeting you expected is present before moving on."
