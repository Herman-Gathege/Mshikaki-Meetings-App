# Architecture

Enough to understand the repository in ten minutes.

## Running shape

Two containers on the KBC server, defined in `docker-compose.yml`:

```text
KBC server (internal IP)

docker compose project: mshikaki
|
|-- app   image built from Dockerfile        published on APP_PORT (8090)
|         uvicorn -> FastAPI                 serves /api/*
|         static files                       serves the built React SPA
|
`-- db    postgres:16-alpine                 not published to the host
          volume mshikaki_pgdata             reachable only on the compose network
```

The SPA and the API are the same origin, so there is no CORS in production and
one port to open. A reverse proxy is not needed; if KBC has one, point it at the
published port and read [deployment.md](deployment.md).

## Container start-up

`backend/entrypoint.sh` runs, in order:

1. `python -m app.cli wait-for-db` - waits for Postgres, up to 60 seconds.
2. `alembic upgrade head` - applies migrations.
3. `python -m app.cli seed` - loads game definitions, content packs, XP rules and
   achievements. Idempotent, and it updates content in place so a deploy cannot
   break a game that is running.
4. `uvicorn app.main:app` - two workers with proxy headers enabled.

## Request path

```text
browser
  |
  v
request logging middleware      assigns a request id, logs one line per request
  |
  v
CSRF middleware                 every write needs the X-Mshikaki-Request header
  |
  v
router (app/api/)               validates shape, resolves the target, checks a capability
  |
  v
service (app/services/)         loads entities, applies domain rules, persists, records activity
  |
  v
domain (app/domain/)            pure rules: state machines, permissions, XP, summary
  |
  v
models (app/db/models/)         SQLAlchemy -> PostgreSQL
```

The domain layer imports no framework and no database, and
`tests/unit/test_domain_purity.py` fails the build if that changes. Everything
that makes the product trustworthy lives there and is tested in milliseconds.

## Where things live

| Looking for | Go to |
|---|---|
| Statuses, roles, capabilities | `backend/app/domain/enums.py`, `permissions.py` |
| The audit trail vocabulary | `backend/app/domain/activity.py` |
| Session, task, idea rules | `backend/app/domain/sessions.py`, `tasks.py`, `ideas.py` |
| XP, achievements, the summary | `backend/app/domain/xp.py`, `achievements.py`, `summary.py` |
| Meeting minutes template | `backend/app/domain/minutes.py` |
| The one activity write path | `backend/app/services/activity.py` |
| Who may do what, at request time | `backend/app/deps.py` |
| Endpoints | `backend/app/api/` |
| Game content | `content/packs/*.json` |
| Screens and components | `frontend/src/pages/`, `components/`, `layouts/` |
| Audit scripts | `scripts/` |

## The two ideas worth knowing

**One write path for the record.** Every mutating service calls
`record_activity` in the same transaction as the change it describes, so the work
and the record can never disagree. See [audit-trail.md](audit-trail.md).

**Origin links are permanent.** A task keeps the session, idea and decision it
came from, which is what makes "why does this exist?" answerable months later.
