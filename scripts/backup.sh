#!/usr/bin/env bash
# Dump the Mshikaki database to backups/, keeping 14 days.
#
#   ./scripts/backup.sh
#   # host cron, 21:00 daily
#   0 21 * * * cd /opt/mshikaki && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# A backup on the same disk as the database is not a backup: copy the directory
# somewhere else as part of your routine.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
set -a && source .env && set +a

STAMP="$(date +%F-%H%M)"
TARGET="backups/mshikaki-${STAMP}.sql.gz"
mkdir -p backups

echo "Dumping database to ${TARGET}"
docker compose exec -T db pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "$TARGET"

SIZE="$(du -h "$TARGET" | cut -f1)"
echo "Wrote ${TARGET} (${SIZE})"

find backups -name 'mshikaki-*.sql.gz' -mtime +14 -print -delete
echo "Kept the last 14 days of dumps."
