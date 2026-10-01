# Deployment on the KBC server

The runbook for the machine that runs Mshikaki. Keep it current; the next
developer should be able to deploy and recover using only this page.

## The server as it stands

| | |
|---|---|
| Host | `172.16.1.36`, SSH alias `local-36`, user `kbc` |
| Application directory | `/home/kbc/mshikaki` |
| Compose project | `mshikaki` |
| Containers | `mshikaki-app-1` (8090 to 8000), `mshikaki-db-1` (not published) |
| Volume | `mshikaki_pgdata` |
| Access from the LAN | http://172.16.1.36:8090 |
| Port choice | 8090, checked free before first deploy; the box already runs Coolify, radiologs, notification and edocs stacks, which must not be disturbed |

## Deploy a change

```bash
ssh local-36
cd /home/kbc/mshikaki
git pull
docker compose up -d --build      # entrypoint: wait for db -> migrate -> seed -> uvicorn
docker compose ps
curl -fsS http://localhost:8090/api/health/ready
```

Deploy in a quiet window, never during a session. A meeting in progress is the one
moment an upgrade must not happen.

## First-time setup on a fresh server

```bash
git clone <repo> /home/kbc/mshikaki && cd /home/kbc/mshikaki
cp .env.example .env
# set POSTGRES_PASSWORD, APP_SECRET_KEY, APP_PORT, ROOT_URL, ALLOWED_EMAIL_DOMAINS
docker compose up -d --build
```

`APP_ENV=production` makes the app refuse to start with default secrets, which is
deliberate.

## Everyday commands

| Task | Command |
|---|---|
| Status | `docker compose ps` |
| Logs | `docker compose logs -f app` |
| Migration state | `docker compose exec app alembic current` |
| Restart the app only | `docker compose restart app` |
| Stop everything | `docker compose down` (the volume survives) |
| Shell | `docker compose exec app bash` |
| Database shell | `docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'` |
| Send the digest by hand | `docker compose exec app python -m app.cli send-digest` |

## Backups and restore

```bash
cd /home/kbc/mshikaki
./scripts/backup.sh                       # backups/mshikaki-YYYY-MM-DD-HHMM.sql.gz, 14 day rotation
./scripts/restore.sh backups/<file>.sql.gz  # asks for confirmation, stops the app, restores, restarts
```

Recommended host cron:

```cron
0 21 * * * cd /home/kbc/mshikaki && ./scripts/backup.sh >> backups/backup.log 2>&1
```

Copy dumps off the machine as well. A backup on the same disk is not a backup.
Rehearse the restore into a scratch database at least once a quarter.

## Rollback

```bash
git checkout <previous-tag-or-commit>
docker compose up -d --build
```

For a bad migration, restore the pre-upgrade dump rather than running a downgrade
in a hurry. Downgrades exist where they are safe, and the dump is faster to trust.

## Health and failure handling

| Endpoint | Meaning |
|---|---|
| `/api/health` | the process is up; never touches the database |
| `/api/health/ready` | the process can serve traffic, which needs the database |

Every response carries `X-Request-Id`, and the same id appears in the log line and
in the body of a failure. Ask a user for that reference and search the logs:

```bash
docker compose logs app | grep <reference>
```

## Troubleshooting

| Symptom | First checks |
|---|---|
| Site does not load | `docker compose ps`; is 8090 open in the KBC firewall; does `curl localhost:8090` work on the server |
| `/api/health/ready` returns 503 | database container health, `DATABASE_URL` parts in `.env`, disk space |
| The app exits at start | missing environment variable (the logs name it); `APP_ENV=production` with default secrets |
| Login succeeds then fails immediately | `SESSION_COOKIE_SECURE` versus whether TLS terminates upstream; `ROOT_URL` |
| Copy button does nothing | the browser is on an insecure origin, so `navigator.clipboard` is absent; the summary falls back to a selectable box |
| A quiz is empty mid-meeting | the play was started without a content pack; start a new play and choose one |
| Disk filling | container log rotation, `backups/`, Postgres WAL in the volume |
| Slow pages | `docker compose logs app | grep slow`; then check the indexes in [database.md](database.md) |

## Reverse proxy and TLS

Mshikaki does not need a proxy. If KBC terminates TLS for internal services, point
it at the published port, forward the `Host` header, set `ROOT_URL` to the
external address and set `SESSION_COOKIE_SECURE=true`, then restart the app.
TLS also removes the clipboard limitation on http origins.
