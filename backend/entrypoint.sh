#!/usr/bin/env sh
# Container entrypoint.
#
# Wait for the database, bring the schema up to date, then start the server.
# Doing migrations here makes deployment a single command:
#   git pull && docker compose up -d --build
#
# Safe while there is exactly one app container. If that ever stops being true,
# move `alembic upgrade head` into a separate one-shot service that runs before
# the app containers start (see docs/deployment.md).

set -e

echo "Waiting for the database..."
python -m app.cli wait-for-db --timeout "${DB_WAIT_TIMEOUT:-60}"

echo "Applying migrations..."
alembic upgrade head

echo "Starting uvicorn on :8000"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-2}" \
    --proxy-headers \
    --forwarded-allow-ips '*'
