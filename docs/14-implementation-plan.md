# 14 - Mshikaki MVP 1 Implementation Plan

Input: [13-plan-brief.md](13-plan-brief.md), with the stack overridden to
React + TypeScript + Vite + shadcn/ui + Tailwind on the front, FastAPI + Pydantic +
SQLAlchemy + Alembic on the back, PostgreSQL underneath, Docker Compose on KBC
servers.

This document is the plan. It is written to be executed ticket by ticket. Product
decisions from the brief are treated as approved and are not re-litigated here.

**Ticket sizes:** S = under half a day, M = about a day, L = 2-3 days, XL = split
it. Anything marked XL in this plan has already been split.

---

## 1. Architecture decision

### Why this stack fits this project

**FastAPI + Pydantic + SQLAlchemy + Alembic + Postgres** is a conventional Python
stack with almost no framework magic. Pydantic validates at the boundary and
publishes an OpenAPI schema for free, which is simultaneously the API docs for the
next developer and the source for the frontend's types. SQLAlchemy in its 2.0 typed
style keeps database behaviour explicit and readable, and Alembic gives ordinary,
reviewable migrations. Python also matches the team's existing internal tooling
experience, which lowers the bus factor.

**React + TypeScript + Vite + Tailwind + shadcn/ui** is the least surprising
frontend for someone joining later. shadcn/ui is not a component library dependency
to fight; it is source code copied into the repo that you own and can edit, which is
exactly right for a product that needs a playful-but-professional visual language
rather than an ERP theme.

**Two languages, and the honest cost.** React plus FastAPI means two runtimes and
two type systems, so API shapes can drift. Mitigation, and it matters: generate the
TypeScript types from the backend's OpenAPI schema with a script
(`openapi-typescript`), and fail `make check` if the generated file is stale. The
shape of the API then has exactly one source of truth. That is the only
cross-language machinery this project needs.

**Vite as a single-page app, and why that is acceptable here.** SSR would give a
better first paint on a slow public network. Mshikaki runs on KBC's internal network
against an IP:PORT, so network latency is a LAN problem, not an internet one. The
real constraint is low-end Android CPU and bundle size, which is addressed by
route-level code splitting, no animation or state libraries, and a bundle budget
enforced in CI. This is a deliberate trade, not an oversight. If the app is ever
exposed over the public internet, revisit it then.

**One backend process, one database, two containers.** No Kubernetes, no
microservices, no Redis, no broker, no managed SaaS in the critical path. Session
state lives in Postgres, not in process memory, so a restart does not log everyone
out.

### Domain separation without ceremony

The brief requires domain logic testable without a database or a running server.
That is achieved with three plain layers, not with a hexagonal architecture
exercise:

```text
app/api/         FastAPI routers: HTTP in, DTO out. No business rules.
app/services/    Orchestration: load -> call domain -> persist -> write activity.
app/domain/      Pure Python. No FastAPI, no SQLAlchemy, no I/O.
app/db/          SQLAlchemy models and session handling only.
```

The rule that makes this real: **`app/domain/` may not import from `app/db/`,
`app/api/` or `app/services/`.** Enforce it with a test that walks the import
graph, not with a convention nobody reads. State machines, the permission matrix,
XP calculation, blocker rules and summary building all live there, so the rules
that would hurt us are tested in milliseconds.

### What this stack deliberately does not use

No Celery, no Redis, no message broker, no GraphQL, no Kubernetes, no service mesh,
no event sourcing framework, no CQRS, no repository-plus-unit-of-work generics, no
Redux, no Zustand, no MobX, no CSS-in-JS runtime. Each is a real technology with a
real place; none of them has a job in MVP 1.

## 2. Repository structure

```text
mshikaki/
|-- README.md                     # quickstart, commands, where to look
|-- AGENTS.md                     # always-on invariants for agents and humans
|-- CONTEXT.md                    # domain vocabulary: Session, Idea, Decision, Task...
|-- Makefile                      # make dev / test / check / migrate / seed
|-- docker-compose.yml            # production shape: app + db
|-- docker-compose.dev.yml        # local shape: db only (app runs natively)
|-- Dockerfile                    # multi-stage: build web, run api
|-- .env.example
|-- .dockerignore
|-- docs/
|   |-- README.md                 # index of the discovery pack and the plan
|   |-- 01..13*.md                # discovery pack (already written)
|   |-- architecture.md           # how the pieces fit, for a new developer
|   |-- deployment.md             # KBC deployment, upgrades, rollback
|   |-- development.md            # local setup, day-to-day commands
|   |-- database.md               # schema, migrations, backup/restore
|   |-- audit-trail.md            # what is recorded, the verb whitelist
|   |-- permissions.md            # roles, capability matrix, enforcement
|   |-- games.md                  # families, engine, adding content
|   |-- standards.md              # coding standards (code-review reads this)
|   `-- adr/
|       |-- 0001-react-fastapi-postgres.md
|       |-- 0002-docker-deployment-kbc.md
|       |-- 0003-cookie-auth-and-csrf.md
|       `-- 0004-audit-trail-design.md
|-- content/
|   |-- README.md                 # how to author and validate a pack
|   |-- schema.json               # pack JSON schema
|   |-- validate.py               # validator used by make check
|   `-- packs/
|       |-- trivia-general-01.json
|       |-- trivia-kenya-01.json
|       |-- trivia-sports-geo-01.json
|       |-- truefalse-01.json
|       |-- emoji-01.json
|       |-- prompts-rapidfire-01.json
|       |-- prompts-icebreakers-01.json
|       |-- prompts-name5-01.json
|       `-- hosted-activity-01.json
|-- scripts/
|   |-- backup.sh                 # pg_dump to backups/
|   |-- restore.sh                # restore from a dump
|   `-- gen-types.sh              # OpenAPI -> frontend types + freshness check
|-- backend/
|   |-- pyproject.toml            # deps, ruff, pytest config
|   |-- alembic.ini
|   |-- alembic/versions/
|   |-- app/
|   |   |-- main.py               # app factory, router registration, SPA mount
|   |   |-- config.py             # pydantic-settings
|   |   |-- cli.py                # seed, send-digest, recompute-achievements
|   |   |-- deps.py               # db session, current user, require_capability
|   |   |-- errors.py             # error codes and handlers
|   |   |-- domain/
|   |   |   |-- enums.py          # statuses, verbs, families
|   |   |   |-- permissions.py    # capability matrix (pure)
|   |   |   |-- sessions.py       # session lifecycle rules
|   |   |   |-- ideas.py
|   |   |   |-- tasks.py          # task state machine, owner rules
|   |   |   |-- blockers.py
|   |   |   |-- xp.py             # caps, weights, idempotency keys
|   |   |   |-- achievements.py   # criteria evaluation
|   |   |   |-- summary.py        # session summary builder
|   |   |   `-- activity.py       # verb whitelist + sentence formatter
|   |   |-- db/
|   |   |   |-- base.py           # naming conventions, Base
|   |   |   |-- session.py        # engine, sessionmaker
|   |   |   `-- models/           # one module per aggregate
|   |   |-- schemas/              # Pydantic request/response models
|   |   |-- services/             # orchestration + activity emission
|   |   |-- api/                  # routers, one file per resource
|   |   `-- seeds/                # idempotent seed functions
|   `-- tests/
|       |-- unit/                 # pure domain tests, no DB
|       |-- integration/          # DB-backed: audit, tenancy, permissions
|       `-- api/                  # endpoint tests via httpx ASGI
`-- frontend/
    |-- package.json
    |-- vite.config.ts            # dev proxy /api -> localhost:8000
    |-- tsconfig.json
    |-- tailwind.config.ts
    |-- src/
    |   |-- main.tsx
    |   |-- App.tsx               # routes + providers
    |   |-- api/
    |   |   |-- client.ts         # fetch wrapper: cookies, errors, CSRF header
    |   |   |-- generated.ts      # generated from OpenAPI, never hand-edited
    |   |   `-- hooks/            # one module per resource (TanStack Query)
    |   |-- components/ui/        # shadcn primitives (owned source)
    |   |-- components/           # app components (ActivityFeed, StatusBadge...)
    |   |-- features/
    |   |   |-- auth/ sessions/ runmode/ ideas/ decisions/ tasks/
    |   |   |-- projects/ games/ leaderboard/ activity/ team/
    |   |-- layouts/              # AppLayout, RunModeLayout
    |   |-- lib/                  # dates, formatting, query client
    |   `-- styles/               # tailwind entry + theme tokens
    `-- tests/
```

Why this shape: `features/` mirrors the domain so a new developer can find "everything
about tasks" in one place, `api/generated.ts` makes API drift impossible to miss,
and `content/` sits at the root because content is a product asset, not backend
code.

## 3. Docker and deployment architecture

### Production shape on a KBC server

```text
KBC SERVER (internal IP, e.g. 10.x.x.x)

docker compose project: mshikaki
|
|-- app        (image: mshikaki/app)          listens on 8000, published as PORT
|              uvicorn -> FastAPI             serves /api/*
|              static files                   serves the built React SPA
|
`-- db         (image: postgres:16-alpine)    not published to the host
               volume: pgdata                reachable only on the compose network
```

Two containers. One published port. The browser hits `http://<server-ip>:<port>/`
and both the SPA and the API come from the same origin, which means no CORS in
production and one thing for KBC's network team to allow.

**Why the SPA is served by FastAPI rather than a separate nginx container.** It
removes a container, a config file, a second port and a whole class of "why is the
proxy returning 502" problems. The whole frontend is static files plus
`index.html` fallback, which is ten lines of FastAPI. If KBC later wants separate
static caching, compression tuning, or the app behind their own reverse proxy, a
frontend nginx container or their existing proxy can be introduced then - the app
does not change.

**KBC's existing reverse proxy.** If KBC terminates HTTP(S) for internal services,
document the plug-in point in `docs/deployment.md`: point it at the published app
port, forward the `Host` header, and set the app's `ROOT_URL` environment variable
so generated links and cookie flags are correct. Do not build a proxy if one
already exists.

**Secure-context gotcha, plan for it now.** Browsers treat `http://10.x.x.x` as an
insecure origin, where `navigator.clipboard` is unavailable. The session summary's
"copy for WhatsApp" button is a P0 feature and must work there, so the export
component ships with a fallback (a selectable textarea plus `document.execCommand`
or manual copy) and a note in `docs/deployment.md` that TLS termination at KBC's
proxy removes the limitation. Discovering this in a live meeting is not acceptable.

### Environment variables

`.env.example` is the contract. Documented in `docs/deployment.md` and validated at
startup by `pydantic-settings`, which refuses to boot on a missing required value.

| Variable | Purpose | Default |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | database bootstrap | none, required |
| `DATABASE_URL` | SQLAlchemy DSN | built from the above |
| `APP_SECRET_KEY` | session token signing and CSRF | none, required |
| `APP_ENV` | `development` / `production` | development |
| `APP_PORT` | published port on the host | 8080 |
| `ROOT_URL` | externally reachable base URL | `http://localhost:8080` |
| `SESSION_COOKIE_SECURE` | set true when TLS is terminated | false |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` | daily digest | disabled if unset |
| `DIGEST_ENABLED` | turns the digest job on | false |
| `TEAM_TIMEZONE` | default timezone for new teams | `Africa/Nairobi` |
| `LOG_LEVEL` | uvicorn/SQLAlchemy verbosity | info |

### Development workflow

```bash
make dev-db          # docker compose -f docker-compose.dev.yml up -d  (postgres only)
make migrate         # alembic upgrade head
make seed            # game definitions + content packs
make api             # uvicorn --reload on :8000
make web             # vite dev server on :5173, proxies /api to :8000
make check           # ruff + pytest + tsc --noEmit + vitest + type freshness
```

Postgres runs in Docker so nobody's laptop needs it installed; the two app
processes run natively so hot reload is instant and bind-mount weirdness is
avoided. A documented `make dev-all` runs everything in Compose for anyone who
prefers that.

### Production workflow

```bash
ssh deploy@<kbc-server>
cd /opt/mshikaki
git pull
docker compose up -d --build        # entrypoint waits for db, runs migrations, starts uvicorn
docker compose ps
curl -fsS http://localhost:8080/api/health/ready
```

The entrypoint runs `alembic upgrade head` before starting uvicorn, which makes the
whole deploy one command and guarantees the schema is never behind the code. This
is safe because there is exactly one app container; the constraint is documented in
`docs/deployment.md`, together with what to change if that ever becomes untrue.

### Docker specifics

- **One Dockerfile, multi-stage**: `node:20-alpine` builds the SPA into
  `/web/dist`; `python:3.12-slim` installs backend dependencies, copies the built
  SPA into `/app/static`, and runs uvicorn. One image, one artefact, no build
  context games.
- **Postgres image**: `postgres:16-alpine`, named volume `pgdata`, no host port
  published, `POSTGRES_INITDB_ARGS` left at defaults.
- **Health checks**: `app` checks `/api/health`; `db` uses `pg_isready`. Compose
  `depends_on` with `condition: service_healthy` for the database.
- **Restart policy**: `unless-stopped` on both.
- **Logging**: json-file driver with `max-size: 10m`, `max-file: 3` on both
  services, so a busy meeting cannot fill the KBC disk.
- **Migrations**: versioned files in `backend/alembic/versions`, run by the
  entrypoint, listed in the runbook with `alembic current` and `alembic history`.
- **Backups**: `scripts/backup.sh` writes `backups/mshikaki-<timestamp>.sql.gz`
  with a 14-day rotation; documented host cron entry.

## 4. Phase 0 checklist

Goal: prove the infrastructure before building the product on it. The milestone is
a hello-world Mshikaki running on the KBC server at the intended IP:PORT.

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P0-1 | Repository skeleton: directories, `.gitignore`, `.dockerignore`, `Makefile` targets, `README.md` stub | - | S | `make help` lists the targets and the tree matches section 2 |
| P0-2 | Backend bootstrap: `pyproject.toml`, ruff + pytest config, `app/main.py`, `app/config.py` with pydantic-settings | P0-1 | S | `uvicorn app.main:app` starts locally and rejects a missing required env var with a clear message |
| P0-3 | Frontend bootstrap: Vite + React + TS, Tailwind, shadcn/ui initialisation, base theme tokens, one page | P0-1 | S | `npm run dev` renders a styled placeholder; `npm run build` produces `dist/` |
| P0-4 | Frontend dev proxy and production static mount: Vite proxy `/api`, FastAPI `StaticFiles` + SPA fallback | P0-2, P0-3 | M | In dev, the page fetches `/api/health` through the proxy; in a built image, the same page loads from `/` |
| P0-5 | Health endpoints `/api/health` and `/api/health/ready` (the second checks the DB) | P0-2 | S | Both return 200 with a DB up and `/ready` returns 503 with the DB down |
| P0-6 | Database layer: engine, sessionmaker, `Base` with naming conventions, `DATABASE_URL` handling | P0-2 | S | A pytest integration test connects to a test database and rolls back |
| P0-7 | Alembic initialisation plus a first empty migration | P0-6 | S | `alembic upgrade head` then `alembic current` shows head on a clean database |
| P0-8 | Multi-stage `Dockerfile` and `docker-compose.yml` (app + db, health checks, volume, log rotation) | P0-4, P0-7 | M | `docker compose up -d --build` serves the SPA and `/api/health` on the published port |
| P0-9 | Entrypoint script: wait for the database, run migrations, exec uvicorn | P0-8 | S | A fresh `docker compose up` on an empty volume ends healthy with no manual step |
| P0-10 | `.env.example`, startup validation, `docs/development.md` local setup | P0-8 | S | A developer who has never seen the repo goes from clone to running app using only that document |
| P0-11 | `docs/deployment.md`: KBC server, IP:PORT, upgrade, rollback, logs, reverse-proxy plug-in point, TLS note | P0-9 | M | The document lists exact commands for deploy, inspect, upgrade and rollback |
| P0-12 | `scripts/backup.sh` and `scripts/restore.sh` | P0-9 | S | A dump is taken, restored into a scratch database, and the app starts against it |
| P0-13 | `make check` plus optional CI workflow running it | P0-2, P0-3 | S | `make check` fails on a lint error, a failing test, a type error or a stale generated types file |
| P0-14 | `AGENTS.md` with the brief's invariants and working agreements | P0-1 | S | Invariants from the brief appear verbatim and are under one page |
| P0-15 | `CONTEXT.md` domain vocabulary (statuses, families, roles, skewer) | P0-14 | S | Every term used in code appears with a one-line definition |
| P0-16 | `docs/standards.md`: naming, layering, error handling, permissions, activity emission, test placement, commits | P0-14 | M | The existing `code-review` skill has a standards document to review against |
| P0-17 | ADR 0001: React + FastAPI + Postgres, including the rejected alternatives | P0-1 | S | The ADR states the decision, the reasons, and what would change it |
| P0-18 | ADR 0002: Docker Compose deployment on KBC, including the rejected alternatives | P0-11 | S | The ADR explains the two-container shape and the reverse-proxy assumption |
| P0-19 | ADR 0003: httpOnly cookie auth, SameSite, and the CSRF approach | P0-2 | S | The ADR explains why opaque server-side tokens beat JWT here |
| P0-20 | ADR 0004: audit trail design, including the database grant approach | P0-7 | S | The ADR records why activity is append-only and how it is enforced |
| P0-21 | `docs/architecture.md`, `docs/database.md`, `docs/audit-trail.md`, `docs/permissions.md`, `docs/games.md` as short practical stubs | P0-14 | M | Each answers "where do I start with this?" in under two pages |

**Phase 0 exit criteria:** on a clean KBC server,
`git clone -> cp .env.example .env -> edit -> docker compose up -d --build` produces
a running Mshikaki reachable at the internal IP:PORT, serving a page that calls the
API, with `/api/health/ready` green and a documented backup and restore. Plus
`AGENTS.md`, `CONTEXT.md`, `standards.md` and four ADRs in the repo.

**Phase 0 does not include:** any domain table beyond the empty initial migration,
any feature, any styling system beyond tokens and one page.

## 5. Phase 1 tickets - Foundation

Goal: identity, tenancy, permissions and the record spine. Nothing fun yet. Every
ticket below leaves the system in a working, deployable state.

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P1-1 | Identity migration: `organizations`, `teams`, `users`, `memberships`, `invites`, `guests` with indexes, soft delete, timestamps | P0-7 | M | `alembic upgrade head` creates all six tables; a test asserts the unique constraints on `users.email` and `(user_id, team_id)` |
| P1-2 | SQLAlchemy models for the identity tables | P1-1 | S | Models round-trip through a test database; `Base.metadata` matches the migration (autogenerate produces no diff) |
| P1-3 | Auth primitives: argon2 password hashing, opaque session tokens, `auth_sessions` table | P1-2 | M | Unit tests cover hash/verify and token issue/verify/expire; a revoked token fails |
| P1-4 | Auth API: bootstrap-register, login, logout, `GET /api/auth/me` | P1-3 | M | API tests cover success, wrong password, disabled user, expired session; `me` returns user, team, role |
| P1-5 | Cookie and CSRF handling: httpOnly, SameSite=Lax, secure flag from settings, required custom header on mutations | P1-4 | M | A mutation without the header is rejected; a cross-origin request without CORS fails; cookie flags match the environment |
| P1-6 | Team bootstrap: first user creates organisation and team; auto-create the default team on an empty install | P1-2 | M | A fresh database plus one registration yields exactly one org, one team, one owner membership |
| P1-7 | Invites: create (email or code), accept, join by code, expiry | P1-6 | M | An invited second user joins the same team with the `member` role; an expired code is rejected |
| P1-8 | Members API: list, change role, remove, and their activity records | P1-7 | M | Role change and removal write activity with old and new values, visible to admins only |
| P1-9 | Guests: create guest participants, list, claim by a later user | P1-2 | M | A guest exists without any user row and appears in a session; claiming links history without rewriting it |
| P1-10 | Permission engine: capability matrix as pure data plus `can(actor, capability, resource)` | P1-2 | M | Unit tests cover every cell of the matrix in section 11, including denials, with no database |
| P1-11 | `require_capability` dependency and denial logging | P1-10 | M | A forbidden request returns 403 with a stable error code and writes an admin-visible activity record |
| P1-12 | Activity migration and model, with indexes for entity, session and team reads | P1-1 | S | Table exists with `(team_id, occurred_at)`, `(session_id, occurred_at)` and `(target_type, target_id)` indexes |
| P1-13 | Activity domain: verb whitelist enum, payload conventions, and a pure sentence formatter | P1-12 | M | Given a verb plus payload, the formatter produces the expected sentence; unknown verbs raise |
| P1-14 | The single activity write helper, plus the service-layer convention for calling it | P1-13 | M | No service can mutate a tracked entity without an activity row; an integration test proves it for one entity as the template |
| P1-15 | Activity read API: by entity, by session, by team, cursor paginated | P1-12 | M | Pagination is stable under concurrent inserts; responses include actor, verb, description, time and payload |
| P1-16 | Database roles and grants: an app role with `INSERT`/`SELECT` only on `activity`, and no `UPDATE`/`DELETE` | P1-12 | M | An integration test attempts an update and a delete as the app role and both fail with a permission error |
| P1-17 | Frontend shell: `AppLayout`, mobile nav (five items), desktop sidebar, theme tokens, loading/empty/error components | P0-3 | M | The shell renders at 360px with no horizontal scroll and all shared states look intentional |
| P1-18 | Frontend auth: login page, session bootstrap on load, protected route wrapper, logout, redirect handling | P1-4, P1-17 | M | An unauthenticated visit redirects to login; after login the shell renders with the current user; a 401 anywhere returns to login |
| P1-19 | API client: fetch wrapper with cookies, error normalisation, CSRF header; generated types plus a `make check` freshness guard | P0-13 | M | Changing a Pydantic schema without regenerating types fails `make check` |
| P1-20 | Server-state conventions: TanStack Query setup, query-key naming, mutation invalidation rules | P1-19 | S | One documented convention exists; no component fetches directly outside the hooks layer |
| P1-21 | Team settings UI: members list, role change, invite create, invite accept, guest list | P1-8, P1-18 | M | An admin can invite a member and change a role entirely through the UI |
| P1-22 | Test harness: pytest fixtures for app client, database, factories; tenancy isolation test helper | P0-13 | M | A new endpoint can be tested in under ten lines; the tenancy helper proves cross-team reads return 404, not 403 |
| P1-23 | Audit completeness harness: a per-entity test asserting a mutation writes the expected activity row | P1-14 | S | The harness is used by at least one Phase 1 entity and is documented for Phase 2 reuse |
| P1-24 | Error handling contract: error codes, HTTP status mapping, JSON error shape, global handler | P0-2 | S | Every documented error code has a test; the frontend client maps them to user-facing messages |
| P1-25 | Structured logging with request ids and the frontend error surface | P1-24 | S | A request id appears in the response header and in the log line; a 500 shows a non-scary error state |
| P1-26 | Seeds: game definitions (6-10) plus one small content pack loaded idempotently from `content/packs` | P1-1 | M | `make seed` twice leaves the same row counts; the definitions cover all three families |
| P1-27 | Permission test suite generated from the capability matrix | P1-10, P1-22 | S | Every capability is exercised for every role; adding a capability without a test fails the suite |

**Phase 1 exit criteria:** two users in one team can register, invite, log in, see
each other, change roles, and have every mutation appear in an attributed,
immutable, team-scoped activity feed. A test proves cross-team reads fail. Game
definitions and one content pack are seeded. No feature from Phase 2 exists yet.

## 6. Phase 2 tickets - The meeting loop (the vertical slice)

Goal: run a real meeting in Mshikaki end to end. This is the most important phase
in the plan and the only one where the ticket order below is strict.

**Build order (do not reorder without a reason):** schema and domain rules first
(P2-1 to P2-5), then the session UI shell (P2-6, P2-7), then each capture type in
ascending complexity (ideas, decisions, tasks, blockers), then Run Mode, then the
summary, then traceability, then the rehearsal.

### Sessions and the meeting frame

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P2-1 | Migration and models: `sessions`, `session_participants`, `agenda_items` | P1-12 | M | Includes the partial unique index enforcing one active session per team |
| P2-2 | Session domain rules: lifecycle transitions, one-active-per-team, close and audited reopen, participant roles | P2-1 | M | Pure unit tests cover every legal and illegal transition, including double-close and reopen-after-close |
| P2-3 | Session API: create, list, get, update, start, pause, resume, close, reopen, with activity | P2-2 | M | Starting a second session returns a clear conflict error; closing writes `session.closed` |
| P2-4 | Participants API: add member, add guest, remove, mark attendance, roles | P2-1 | M | A guest and a member can both be participants; attendance changes are recorded |
| P2-5 | Agenda API: ordered items, timebox, mark covered | P2-1 | S | Reordering persists; marking covered writes activity |
| P2-6 | Sessions UI: list, create (title, date, agenda paste), next-session card on Today | P2-3 | M | Creating a session with a pasted agenda produces ordered agenda items in one screen |
| P2-7 | Session detail shell: tabs (Overview, Agenda, Ideas, Decisions, Tasks, Play, Activity) with the shared Activity component | P1-15, P2-6 | M | Every tab renders at 360px; the Activity tab shows Phase 2 activity with human sentences |

### Ideas

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P2-8 | Migration and models: `ideas`, `idea_tags` | P1-12 | S | Indexes on `(team_id, status)` and `(session_id)` |
| P2-9 | Idea domain: status transitions, promotion links, validation | P2-8 | M | Unit tests cover every transition in the brief's state machine, including revival of a rejected idea |
| P2-10 | Idea API: create, list with filters, get, update, change status, convert, delete (soft) | P2-9 | M | Converting sets `converted_to_*` and writes `idea.converted`; deleting keeps the row and records a snapshot |
| P2-11 | **Quick capture sheet**: global, thumb-reachable, title-only, optimistic, no required fields | P2-10, P1-20 | M | **Timed acceptance: a real person adds an idea from a phone in under five seconds**, with no navigation away from the current screen |
| P2-12 | Idea list and detail UI: filters, status changes, promote actions, tag editing | P2-10 | M | An idea can be created, discussed, accepted and promoted without leaving the ideas area |

### Decisions

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P2-13 | Migration, model and domain for `decisions`, including supersede links and the standalone-reason constraint | P1-12 | S | The database rejects a decision with neither a session nor a standalone reason |
| P2-14 | Decision API: record, list, get, supersede, link to idea/project/task | P2-13 | M | Superseding writes both directions of the link and one activity record on each side |
| P2-15 | Decision UI: record from an idea with pre-filled statement, standalone record, decision detail with links | P2-14, P2-12 | M | Recording a decision from an idea takes two taps and pre-fills the statement |

### Tasks and blockers

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P2-16 | Migration, model and domain for `tasks` and `task_collaborators` | P1-12 | M | Unit tests cover the task state machine and the "owner required outside backlog" rule |
| P2-17 | Task API: create with origin links, update, assign, change status, set due date and priority | P2-16 | M | Every transition writes activity; assigning to a non-member is rejected |
| P2-18 | Task UI: create from a decision, idea or session; task detail; owner picker; status control | P2-17 | M | A task created from a decision keeps all three origin links visible |
| P2-19 | Migration, model and domain for `blockers`: blocked implies an open blocker, unblocking requires resolution | P2-16 | M | Unit tests prove the status and blocker records cannot disagree in either direction |
| P2-20 | Blocker API and UI: raise with reason, resolve with resolution, surface on the task and the session | P2-19 | M | Raising a blocker moves the task to `blocked` atomically; resolving returns it to `in_progress` |

### Run Mode

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P2-21 | Run Mode shell: step state machine (Play, Capture, Decide, Assign, Close), one action per screen, screen-first layout, keyboard shortcuts, resume after refresh | P2-3, P2-7 | L | A facilitator can advance and go back through all five steps; refreshing the page resumes at the same step |
| P2-22 | Run Mode - Play step: game play record, prompt deck renderer, next/reveal, results | P1-26, P2-21 | M | A prompt deck can be played on a shared screen with the play and its participants recorded against the session |
| P2-23 | Run Mode - Capture step: live list of ideas captured from phones, polling refresh, shared-screen readable | P2-11, P2-21 | M | Ideas captured on three phones appear on the shared screen within a few seconds without a manual refresh |
| P2-24 | Run Mode - Decide step: turn ideas into decisions on screen, with the prefill flow | P2-15, P2-21 | M | A decision recorded in Run Mode appears immediately in the session's Decisions tab |
| P2-25 | Run Mode - Assign step: create tasks with owners and due dates for the room, from decisions or ideas | P2-18, P2-21 | M | Three tasks with three owners can be created from the Assign step without leaving it |

### Closing, summary and traceability

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P2-26 | Summary builder in the domain: deterministic, ordered, rule-based, no LLM | P1-15, P2-25 | L | A golden-file unit test builds a summary from a fixed activity fixture and matches exactly |
| P2-27 | Session close persists a frozen summary snapshot; regeneration is explicit, audited and marks the previous snapshot superseded | P2-26, P2-3 | M | Regenerating twice leaves one current snapshot and one superseded activity record |
| P2-28 | Summary UI and plain-text export, with the insecure-origin clipboard fallback | P2-27 | M | Copying the summary works on `http://<lan-ip>:<port>` as well as on localhost |
| P2-29 | Traceability: "Why does this exist?" panel on tasks, decisions and ideas; "What came out of this session" panel | P2-25 | M | Task to decision to idea to session is walkable in both directions from the UI, including for a task whose idea was deleted |
| P2-30 | Run Mode resilience: optimistic writes, retry, no data loss when the network drops mid-meeting | P2-23 | M | With the network disabled and re-enabled, captured items survive and no duplicate appears |
| P2-31 | Comments: flat threads on idea, decision, task and blocker with activity records | P2-12 | M | Commenting writes activity; editing a comment updates the body and records the edit |
| P2-32 | Guest participation end to end: join by code, appear in the session, play, be credited, no account | P1-9, P2-22 | M | A guest with no user row plays a game, is named in the results and appears in the summary |
| P2-33 | Phase 2 audit completeness pass: one integration test per Phase 2 entity asserting the activity row | P1-23 | M | Deleting a service's activity call makes at least one test fail |
| P2-34 | Meeting rehearsal: full loop on test data, throttled network, phone plus projector, defects filed | P2-28 | M | A written report exists with each loop step observed, plus anything skipped, and the rehearsal data is reset |

**Phase 2 exit criteria:** a real Innovations session is run by the facilitator
without help; at least one decision and three assigned tasks exist by the end; the
summary is accurate with no editing; the text export can be pasted into WhatsApp;
every object created traces back to the session; every action appears in the audit
trail. This is the point at which Mshikaki becomes genuinely useful, and it should
arrive as early as the plan allows.

## 7. Phase 3-6 tickets

### Phase 3 - Work layer

Goal: make the week between meetings work. This phase is where retention lives, so
it follows the loop rather than preceding it.

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P3-1 | My Work: owned tasks grouped as overdue, this week, later, blocked, recently done, with one-tap status changes | P2-18 | M | A user can clear their inbox of status changes without opening a single task detail page |
| P3-2 | Migration, model and API for `projects` (flat, with status and owner) | P2-16 | M | A project lists its tasks, decisions, ideas and activity |
| P3-3 | Project UI: create, list, detail with tasks, linked decisions and ideas, activity | P3-2 | M | A task created in a session can be moved into a project in two taps |
| P3-4 | Task list with filters: status, owner, project, session, due window | P2-18, P3-2 | M | Filters survive a page refresh and are shareable as a URL |
| P3-5 | Task board by status, simple columns, explicit moves | P3-4 | M | Board and list show identical data; no board configuration exists |
| P3-6 | Blocked view: team-wide blockers, who raised them, who is unblocking, age | P2-20 | M | Every open blocker has a visible owner or is explicitly flagged as unowned |
| P3-7 | Collaborators on tasks: add, remove, visibility in My Work | P2-16 | S | A collaborator sees an explicitly shared task without owning it |
| P3-8 | Priority and due date editing with activity and overdue computation in team timezone | P2-17 | S | Changing a due date records old and new; overdue respects `Africa/Nairobi` |
| P3-9 | Serious metrics view: completed, blocked, overdue, by owner, explicitly unscored and separate from the leaderboard | P3-4 | M | The view carries a visible "not a ranking" label and shares no UI with the leaderboard |
| P3-10 | Team activity feed with filters: actor, verb, entity type, date | P1-15 | M | Filters are usable on a phone and paginate by cursor |
| P3-11 | Search across ideas, decisions and tasks | P1-15 | M | Postgres full-text or `ILIKE` with an index; results are grouped by type and link to the entity |
| P3-12 | Task detail polish: history, origin links, collaborators, blockers, comments in one readable page | P2-29 | M | The whole story of a task fits on one screen section, in order, with no tab hunting |

**Phase 3 exit criteria:** a task created in a session is worked, blocked,
unblocked and completed without ever returning to the session, and its full story
is visible on its activity feed.

### Phase 4 - Play layer

Goal: fun enough that people ask for it. Everything here is cuttable without
breaking the loop, which is why it comes after Phase 3.

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P4-1 | Migrations and models: `game_definitions`, `content_packs`, `game_questions`, `game_plays`, `game_scores` | P1-26 | M | The five tables exist; game definitions already seeded from Phase 1 still resolve |
| P4-2 | Content schema, validator and importer: `content/schema.json`, `content/validate.py`, idempotent seeding by pack key | P4-1 | M | `make check` validates all packs; re-importing an edited pack updates items without duplicating them |
| P4-3 | Game library API and UI: catalogue with filters for time, energy, group size and family | P4-2, P1-17 | M | A facilitator can find a five-minute, any-mood, six-plus-player game in two taps |
| P4-4 | `host_quiz` engine in the domain: question stream, rounds, reveal, host confirmation, position calculation | P4-1 | M | Pure unit tests cover the full quiz state machine with no database |
| P4-5 | Game play UI in Run Mode: display mode plus host console (next, reveal, award) | P4-4, P2-22 | L | The room sees the question on the shared screen while the host operates a minimal console |
| P4-6 | Scoring: award to a member or guest, points, position, and a host override with a required reason, audited | P4-5 | M | An override writes `game.score_adjusted` with old and new values and the host's reason |
| P4-7 | Results: persist play results, reflect them in the session and in the summary's games section | P4-6, P2-26 | M | The summary lists each game with its winner and standings without human input |
| P4-8 | XP rules table, seeds and the pure XP calculator: caps per session/day/week, diminishing returns, facilitator weighting | P1-12 | L | Unit tests prove every cap and that the same input never yields a different award |
| P4-9 | XP award service: idempotent awards from domain events, ledger only, no stored totals | P4-8 | M | Replaying the same event twice awards once; a reversal is a new event with a reason |
| P4-10 | Achievements: definitions, criteria evaluation, awards with source references, audited revocation | P4-9 | L | Each seeded achievement has a unit test that awards it from a fixture and refuses a near-miss |
| P4-11 | Seasons: model, creation, current-season resolution, closing | P4-8 | M | A closed season freezes its standings; a new season starts empty |
| P4-12 | Leaderboard API: session, season and all-time, honouring per-user opt-out | P4-9, P4-11 | M | An opted-out user receives XP and achievements but appears in no standings |
| P4-13 | Leaderboard UI: session result after close, season standings, achievement list, opt-out toggle, permanent disclaimer | P4-12 | M | The disclaimer is visible in every leaderboard view; opting out is one tap and reversible |
| P4-14 | Daily digest email: query, template, CLI command, SMTP configuration, documented host cron entry | P3-1 | M | `python -m app.cli send-digest` sends a correct summary; with SMTP unset it exits cleanly and does nothing |
| P4-15a..i | Content authoring: nine packs, roughly 200 items total, each authored, licensed and validated | P4-2 | L each | Each pack passes `content/validate.py`, declares license and attribution, and is loaded by `make seed` |
| P4-16 | Guests in standings and XP, without accounts, excluding them from seasonal boards until they claim | P4-12, P2-32 | S | A guest wins a game and receives XP; they appear in the session board, not the season board |

**Phase 4 exit criteria:** a session with two games is played and scored; standings
and XP are correct and capped; no repeatable action earns unbounded points; an
opt-out is handled correctly; the digest sends from the server.

### Phase 5 - Traceability and adoption

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P5-1 | "Why does this exist?" applied consistently on task, decision and idea pages | P2-29 | S | All three surfaces use one shared component, including deleted-origin handling |
| P5-2 | Global activity filters UI refinement plus saved defaults per user | P3-10 | M | A team lead can answer "what did Anne do last week" in three interactions |
| P5-3 | Search UI with grouped results and keyboard access | P3-11 | M | Search is reachable from the shell and returns in under a second on seeded data |
| P5-4 | Onboarding: first-run checklist, good empty states, and a deletable sample session | P2-6 | M | A brand-new team has a useful first ten minutes with no documentation |
| P5-5 | Record charter page: what is recorded, what is not, who can see it, and the promise that it is not used for evaluation | P5-4 | S | The charter is linked from onboarding and from team settings |
| P5-6 | Guest claiming and history reattribution, as an audited event, never an in-place rewrite | P2-32 | M | Claiming links the profile and preserves the original actor on every historical record |
| P5-7 | Digest content polish: my tasks, blockers I can help with, yesterday's record | P4-14 | S | The digest is useful to a member who was not in the meeting |
| P5-8 | Summary rendering polish: print stylesheet and WhatsApp-friendly plain-text spacing | P2-28 | M | A pasted summary reads correctly in WhatsApp on a phone |
| P5-9 | Accessibility pass: focus order, labels, projector contrast, full keyboard path in Run Mode | P2-21 | M | Run Mode can be driven entirely from a keyboard, and contrast passes at projector brightness |
| P5-10 | Copy centralisation and tone pass: all user-facing strings in one place, playful where allowed, sober in the record | P1-17 | M | No user-facing string is hard-coded inside a component |

**Phase 5 exit criteria:** someone who has never used Mshikaki answers "what did we
decide about X, and who is doing it?" within two minutes of landing on Today.

### Phase 6 - Hardening

| ID | Ticket | Depends on | Size | Done when |
|---|---|---|---|---|
| P6-1 | Frontend performance: route-level code splitting, bundle budget in `make check`, no oversized dependencies | P2-21 | M | The initial bundle meets an agreed budget and a cold load on a throttled connection is timed |
| P6-2 | Slow-connection acceptance test, documented with the throttling settings used | P6-1 | S | Today and Run Mode both pass the agreed time budget on a throttled connection |
| P6-3 | Permission and tenancy coverage audit against the capability matrix | P1-27 | M | Every capability and every role has a passing test, including cross-team denial |
| P6-4 | Audit immutability verification in CI: attempt an update and a delete as the app role | P1-16 | S | CI fails if the grants are ever loosened |
| P6-5 | Backups: retention, host cron, and a rehearsed restore into a scratch database | P0-12 | M | A dated restore drill is recorded in `docs/deployment.md` |
| P6-6 | Error tracking and log review: request ids, error rate check, log rotation verified | P1-25 | S | A deliberate 500 is traceable from the UI through the logs in under a minute |
| P6-7 | Security pass: auth rate limits, password rules, cookie flags, CSRF verification, dependency audit | P1-5 | M | Each item is either fixed or explicitly accepted with a reason in the ADR |
| P6-8 | Database performance: `EXPLAIN` on the hot queries, index verification, autovacuum notes | P3-4 | M | The team feed, session view, My Work and leaderboard queries all use indexes, verified by plan output |
| P6-9 | Runbook completion: upgrade, rollback, health, common failures, troubleshooting index | P0-11 | M | Another developer can deploy a change and recover from a failed deploy using only the runbook |
| P6-10 | Full rehearsal with real devices, projector and a bad connection, followed by a written go/no-go | P2-34 | M | The go/no-go names what was verified, what was not, and any accepted risk |

**Phase 6 exit criteria:** the team runs a real session in a real room on a
mediocre connection and nothing needs explaining twice.

## 8. Database model

The authoritative schema is [04-data-model.md](04-data-model.md). This section
confirms it for the Python stack and lists the one addition and the enforcement
details that only exist at the database level.

Conventions: `uuid` primary keys generated in Python, `timestamptz` in UTC, soft
delete via `deleted_at`, `team_id` on every domain table, `text` plus `CHECK` for
statuses (not Postgres enums, so a new status is an ordinary migration), no
`ON DELETE CASCADE` except for genuinely owned children (`game_scores` ->
`game_plays`, `idea_tags` -> `ideas`, `task_collaborators` -> `tasks`).

```text
Tenancy and identity
  organizations (1) ---< teams (1) ---< memberships >--- users
                                  \---< invites
                                  \---< guests ---(optional)---> users
                                  \---< auth_sessions

The meeting
  teams ---< sessions ---< session_participants >--- (users | guests)
                    |---< agenda_items
                    |---< game_plays ---< game_scores
                    |---< ideas ---< idea_tags
                    |---< decisions
                    \---< tasks ---< blockers

The work (outlives sessions)
  teams ---< projects ---< tasks
  tasks ---> sessions (origin, nullable)
  tasks ---> ideas (origin, nullable)
  tasks ---> decisions (origin, nullable)
  tasks ---< task_collaborators >--- users
  blockers ---> tasks | ideas

The record (append-only)
  activity ---> sessions, and any target by (target_type, target_id)
  xp_rules ---< xp_events >--- users | guests
  seasons ---< xp_events, achievement_awards
  achievements ---< achievement_awards
  comments ---> (idea | decision | task | blocker | session)
  notifications (reserved for the digest)

Game content (data, not code)
  game_definitions ---< content_packs ---< game_questions
  game_plays ---> game_definitions, content_packs, sessions
```

**The one table not in the brief:** `auth_sessions` (id, user_id, token_hash,
created_at, expires_at, revoked_at, user_agent, ip). Opaque server-side sessions
instead of JWTs, because revocation matters more than statelessness in a 20-person
internal app, and it keeps the logout story trivial.

### Enforced at the database, not just in code

| Rule | Mechanism |
|---|---|
| Activity, `xp_events` and `achievement_awards` cannot be modified or deleted | The application's database role has `INSERT` and `SELECT` only on those tables |
| One active session per team | Partial unique index `unique(team_id) where status = 'active'` |
| A decision must have a session or a stated reason | `CHECK (session_id IS NOT NULL OR standalone_reason IS NOT NULL)` |
| A blocker must point at a task or an idea | `CHECK (task_id IS NOT NULL OR idea_id IS NOT NULL)` |
| One owner per task | Single `owner_id` column, never a second owner field |
| Statuses are constrained | `CHECK` constraints per status column |
| No duplicate XP for the same event | `UNIQUE (idempotency_key)` on `xp_events` |
| Session numbering per team | `UNIQUE (team_id, sequence_no)` |

### Migration discipline

- One migration per ticket at most, named `NNNN_<verb>_<subject>` (for example
  `0007_add_session_lifecycle`), never edited after it has been applied anywhere
  other than a developer's own machine.
- `alembic revision --autogenerate` output is always read before committing; model
  and migration divergence is a defect.
- A downgrade path is written whenever it is straightforward; irreversible
  migrations are labelled in the file and in the pull request.
- Seeding is not migration. Game content is imported by `app.cli seed`, which is
  idempotent and safe to rerun.

## 9. API structure

Plain REST under `/api`, cookie-authenticated, JSON with `snake_case` keys (matching
Python, so the generated TypeScript types need no name mapping). No versioning
prefix in MVP 1: there is exactly one client, and a version can be added later
without breaking anything if the client and server are always deployed together.

| Area | Endpoints | Notes |
|---|---|---|
| Health | `GET /api/health`, `GET /api/health/ready` | Liveness vs database readiness; used by Compose health checks |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` | `register` bootstraps the first organisation and team |
| Invites | `POST /api/invites`, `GET /api/invites`, `POST /api/invites/{code}/accept` | Code or email invite, expiry enforced |
| Team | `GET /api/team`, `PATCH /api/team`, `GET /api/team/members`, `PATCH /api/team/members/{id}`, `DELETE /api/team/members/{id}`, `GET /api/team/guests` | Role changes audited |
| Sessions | `GET|POST /api/sessions`, `GET|PATCH /api/sessions/{id}`, `POST /api/sessions/{id}/start|pause|resume|close|reopen`, `GET /api/sessions/{id}/summary`, `POST /api/sessions/{id}/summary/regenerate`, `GET /api/sessions/{id}/export.txt` | Lifecycle transitions are explicit endpoints, not a generic status patch |
| Participants | `GET|POST /api/sessions/{id}/participants`, `PATCH|DELETE /api/sessions/{id}/participants/{pid}` | Accepts a `user_id` or a guest payload |
| Agenda | `GET|POST /api/sessions/{id}/agenda`, `PATCH|DELETE /api/agenda/{id}`, `POST /api/agenda/{id}/cover` | Ordered by position |
| Ideas | `GET|POST /api/ideas`, `GET|PATCH|DELETE /api/ideas/{id}`, `POST /api/ideas/{id}/status`, `POST /api/ideas/{id}/convert` | Filters: status, session, tag, author |
| Decisions | `GET|POST /api/decisions`, `GET|PATCH /api/decisions/{id}`, `POST /api/decisions/{id}/supersede` | Supersede writes both links |
| Tasks | `GET|POST /api/tasks`, `GET|PATCH|DELETE /api/tasks/{id}`, `POST /api/tasks/{id}/assign`, `POST /api/tasks/{id}/status`, `GET /api/tasks/mine` | Origin links accepted on create |
| Blockers | `POST /api/tasks/{id}/blockers`, `GET /api/blockers`, `POST /api/blockers/{id}/resolve` | Raising is atomic with the task status change |
| Projects | `GET|POST /api/projects`, `GET|PATCH|DELETE /api/projects/{id}`, `GET /api/projects/{id}/work` | Detail aggregates tasks, decisions, ideas |
| Comments | `GET|POST /api/comments`, `PATCH|DELETE /api/comments/{id}` | `?target_type=&target_id=` |
| Activity | `GET /api/activity` | Query by `target_type`/`target_id`, `session_id`, or team-wide, with cursor pagination |
| Games | `GET /api/games`, `GET /api/games/packs`, `POST /api/sessions/{id}/games`, `POST /api/game-plays/{id}/next`, `POST /api/game-plays/{id}/score`, `POST /api/game-plays/{id}/finish` | Host-paced only; no per-player endpoints in MVP 1 |
| Leaderboard | `GET /api/leaderboard?scope=session|season|all`, `GET /api/achievements`, `GET /api/metrics`, `PATCH /api/me/preferences` | `metrics` is unscored and separate |
| Search | `GET /api/search?q=` | Ideas, decisions, tasks only |

### Conventions

- **Errors**: `{"error": {"code": "task.owner_required", "message": "...",
  "details": {...}}}` with a correct HTTP status. Codes are stable strings defined
  in one place and covered by tests; the frontend maps them to friendly copy.
- **Pagination**: `?limit=&cursor=`, response `{"items": [...], "next_cursor": ...}`.
  Cursor only, never offset, because activity is append-heavy.
- **Permissions**: a router declares `Depends(require_capability("task.update"))`
  or resolves the target and calls `can()`. No router contains an `if role ==`
  chain.
- **Activity**: written in the service layer, never in the router, never in a
  Pydantic validator.
- **Mutations with side effects on XP**: the service returns the domain events it
  produced, and the XP layer consumes them. Routers never award points.
- **Timestamps**: ISO 8601 UTC in responses; the frontend formats to the team
  timezone. No local-time arithmetic on the server.

## 10. Frontend structure

### Routes

| Route | Screen | Mode |
|---|---|---|
| `/login`, `/join/:code` | Auth and invite acceptance | mobile-first |
| `/` | Today: next session, my tasks, blockers, recent activity, leaderboard strip | mobile-first |
| `/sessions`, `/sessions/:id` | Session list and session detail with tabs | mobile-first |
| `/sessions/:id/run` | Run Mode | **screen-first** |
| `/work/mine` | My Work | mobile-first |
| `/work`, `/work/projects/:id` | Task list and board, project detail | mobile-first |
| `/ideas`, `/ideas/:id` | Ideas | mobile-first |
| `/play`, `/play/:playId` | Game library and play display | library list mobile, play screen-first |
| `/leaderboard` | Season, session, achievements, opt-out, unscored metrics | mobile-first |
| `/activity` | Team activity with filters | mobile-first |
| `/team` | Members, invites, guests, settings | mobile-first |

**Two layouts, not two apps.** `AppLayout` is the mobile-first shell with bottom
navigation. `RunModeLayout` is the screen-first shell: large type, high contrast,
one primary action, keyboard shortcuts (`→` advance, `Esc` back, `Space` reveal),
and a minimal facilitator control strip. Run Mode still renders usably at 360px,
because the facilitator may be on a phone.

### Shared components worth naming up front

`ActivityFeed` and `ActivityItem` (one renderer for the whole app),
`EntityLink` and `OriginTrail` (the traceability walk, including deleted-origin
states), `StatusBadge`, `OwnerPicker`, `DueDatePicker`, `CaptureSheet` (the global
quick capture), `TaskCard`, `TaskList`, `TaskBoard`, `IdeaCard`, `DecisionCard`,
`GameDisplay`, `GameHostConsole`, `LeaderboardTable`, `MetricRow`, `EmptyState`,
`ErrorState`, `LoadingState`, `ConfirmDialog`.

### State management, deliberately decided

- **Server state:** TanStack Query. It is the boring, conventional answer for
  caching, invalidation, polling in Run Mode and optimistic capture, all of which
  this app needs on day one. Hand-rolling that is more code, not less.
- **Client state:** none globally. Auth and current team come from a small React
  context populated once from `/api/auth/me`. Everything else is local component
  state or URL state.
- **Forms:** `react-hook-form` with small schemas for anything with more than three
  fields. The quick capture sheet uses plain local state because its whole point is
  being instant.
- **No Redux, no Zustand, no MobX, no CSS-in-JS runtime.**

### Design language

Tailwind tokens in one place: colour, spacing scale, radii, type scale. Edit
shadcn components in place, do not wrap them in a second abstraction layer. Generous
spacing, 16px base type, 44px minimum touch targets, motion limited to CSS
transitions and only where it confirms an action, no gradients or illustration
sprawl. The record layer (tasks, decisions, activity) stays visually sober; the fun
layer (games, leaderboard, Run Mode) is allowed to be loud.

## 11. Permission matrix

Expressed as capability strings so it can be tested as data rather than debated in
code review. `can(actor, capability, resource)` is pure and lives in
`app/domain/permissions.py`; the matrix below is the fixture the test suite drives.

| Capability | owner | admin | facilitator | member | guest |
|---|---|---|---|---|---|
| `team.view` | Y | Y | Y | Y | n, session only |
| `team.manage_members` | Y | Y | n | n | n |
| `team.manage_settings` | Y | n | n | n | n |
| `invite.create` | Y | Y | n | n | n |
| `session.create` | Y | Y | Y | Y | n |
| `session.start.own` | Y | Y | Y | Y | n |
| `session.start.any` | Y | Y | n | n | n |
| `session.close.own` | Y | Y | Y | Y | n |
| `session.close.any` | Y | Y | n | n | n |
| `session.participant.manage` | Y | Y | own session | n | n |
| `agenda.manage` | Y | Y | own session | n | n |
| `idea.create` | Y | Y | Y | Y | session only |
| `idea.edit.own` | Y | Y | Y | Y | within session window |
| `idea.edit.any` | Y | Y | own session | n | n |
| `idea.delete.any` | Y | Y | n | n | n |
| `idea.convert` | Y | Y | Y | Y | n |
| `decision.record` | Y | Y | Y | Y | n |
| `decision.edit.any` | Y | Y | own session | n | n |
| `task.create` | Y | Y | Y | Y | n |
| `task.assign.other` | Y | Y | Y | n | n |
| `task.assign.self` | Y | Y | Y | Y | n |
| `task.edit.own` | Y | Y | Y | Y | n |
| `task.edit.any` | Y | Y | Y | n | n |
| `task.status.own` | Y | Y | Y | Y | n |
| `task.status.any` | Y | Y | Y | n | n |
| `task.delete.any` | Y | Y | n | n | n |
| `blocker.raise` | Y | Y | Y | Y | n |
| `blocker.resolve` | Y | Y | Y | own/co-owned task | n |
| `comment.create` | Y | Y | Y | Y | session items |
| `project.manage` | Y | Y | Y | n | n |
| `game.launch` | Y | Y | Y | n | n |
| `game.score` | Y | Y | own session | n | n |
| `game.score.override` | Y | Y | own session | n | n |
| `content.manage` | Y | Y | n | n | n |
| `xp.rule.manage` | Y | Y | n | n | n |
| `achievement.revoke` | Y | Y | n | n | n |
| `activity.view.team` | Y | Y | Y | Y | session only |
| `activity.view.admin` | Y | Y | n | n | n |
| `metrics.view` | Y | Y | Y | Y | n |
| `leaderboard.view` | Y | Y | Y | Y | session only |

Rules that are not expressible as a single cell, and therefore need explicit tests:
ownership beats hierarchy (an admin edits another person's idea with attribution,
never silently); facilitator powers are scoped to sessions they facilitate and
expire when the session closes; a guest is bounded by scope and time; self-assigned
completion is allowed but scoring rules in [07](07-leaderboard-xp.md) apply.

## 12. Audit model

### How a mutation produces a record

```text
HTTP request
   |
   v
Router            validates shape, resolves the target, checks the capability
   |
   v
Service           loads entities, calls domain rules, persists changes
   |                       |
   |                       `--> domain raises a rule violation (no write happens)
   v
record_activity(session, actor, verb, target, payload)   <-- the only insert path
   |
   v
Single commit     data change and activity row land together or not at all
```

Rules that make it trustworthy:

1. **One transaction.** The entity change and its activity row commit together, so
   a partial state is impossible.
2. **One write path.** `services/activity.py::record_activity` is the only function
   that inserts into `activity`; it is reviewed as security-relevant code.
3. **The verb is from the whitelist.** An unknown verb raises, which turns a typo
   into a test failure instead of an unreadable history entry.
4. **The payload carries the story.** Titles, excerpts and old/new values, not just
   ids, so history stays readable after a rename or a delete.
5. **The description is generated.** A pure `describe(verb, payload) -> str` renders
   every record the same way in every surface; the frontend never composes
   sentences from raw fields.
6. **Coalescing is display-only.** Five rapid edits render as one expandable line
   while five immutable rows remain.
7. **The database refuses edits.** The app role cannot `UPDATE` or `DELETE`
   activity rows; CI asserts this by attempting both.
8. **Completeness is tested.** Each entity has an integration test that performs its
   mutations and asserts the expected activity rows; removing a call breaks a test.

### What is never recorded

Page views, searches, keystrokes, presence, notification reads, "user is online",
scroll depth, or any soft signal. The whitelist in [08](08-audit-trail.md) is the
contract and the reason the trail stays readable and non-surveillant.

## 13. Game architecture

**Content is data. Behaviour is code.** This separation is what lets the game
library grow without a migration per question.

```text
content/packs/*.json            <-- authored, validated, versioned in git
        |
        v   make seed / app.cli seed  (idempotent upsert by pack key)
content_packs ----< game_questions        <-- rows, never code
        |
game_definitions (family, config_schema)  <-- seeded rows, admin-editable later
        |
        v
game_plays (session, host, pack, status)  <-- runtime, one per play
        |
        v
game_scores (member or guest, points, position, source, adjusted_by)
```

| Change | What it costs |
|---|---|
| Add questions to an existing pack | Edit JSON, run `make check`, run `make seed`. No migration, no deploy of code |
| Add a whole new pack (for example "Kenyan music") | New JSON file plus one seed entry. No migration |
| Add a new game within an existing family | A row in `game_definitions` with a config schema. Renderer unchanged for `prompt_deck`; small renderer work for `host_quiz` variants |
| Add a new family | A new family value, a renderer component, and handling in the play state machine. This is the only case that touches code, and it should stay rare by design |

The play state machine itself (`pending -> running -> finished | abandoned`) is pure
domain code with unit tests. Scoring is host-driven in MVP 1: the host taps the
player who answered, the app computes points and position, and any correction is an
audited override with a reason. Timing bonuses are off by default because speed on
shared wifi is not a fair contest.

What stays out on purpose: per-phone answering, realtime sync, buzzers, latency
scoring, tournaments, user-authored question sets through the UI, and any game
mechanic that requires a second engine. Each is additive later; none is required
for a room of colleagues to play trivia together.

## 14. Test strategy

Tests exist to protect the rules that would hurt us if they broke, not to chase a
coverage number. The suite is three layers plus one deliberate manual practice.

### Unit - pure domain, no database, no HTTP

Fast, and where most tests should live.

| Area | What is asserted |
|---|---|
| Session lifecycle | Every legal transition works; double-close, start-while-active, close-while-planned and reopen-after-close are refused |
| Task state machine | Every transition, plus "an owner is required for anything other than backlog" |
| Blocker rules | A blocked task always has an open blocker; resolving returns the task to in-progress; two blockers on one task behave correctly |
| Origin links | Conversion sets the right links; origin links are never cleared by later edits |
| XP calculation | Caps per session, day and week; diminishing returns; facilitator weighting; an award is a pure function of its event |
| XP idempotency | The same event key yields one award; reversal produces a compensating event |
| Achievement criteria | Each seeded achievement triggers on a fixture that should earn it and refuses a near-miss |
| Permission matrix | Every capability for every role, including denials, driven by the matrix itself |
| Activity formatter | Every whitelisted verb renders the expected sentence; unknown verbs raise |
| Summary builder | Golden-file test from a fixed fixture: ordering, counts, attendance, games, tasks, blockers |
| Domain purity | `app/domain` imports nothing from `app/db`, `app/api` or `app/services` |

### Integration - real Postgres, no HTTP

Fewer, slower, and they protect the properties that only exist across a transaction.

| Area | What is asserted |
|---|---|
| Activity completeness | One test per entity: perform the mutation, assert the expected activity row |
| Audit immutability | An `UPDATE` and a `DELETE` against `activity` as the app role both fail |
| Transaction atomicity | A rule violation rolls back both the entity change and its activity row |
| Tenancy isolation | A query for another team's object returns not-found, never a forbidden-but-existing leak |
| Soft deletion | Deleting sets `deleted_at`, hides the row from list endpoints and keeps it in history |
| Frozen summary | Closing freezes the snapshot; regeneration supersedes rather than overwrites; reopening marks it stale |
| Session closing | Closing computes counts, attendance and XP exactly once, idempotently |
| Guest participation | Guests can be participants, players and collaborators without a user row; claiming preserves history |
| Leaderboard opt-out | An opted-out user earns XP and achievements but appears in no standings |
| Migration integrity | Autogenerate produces no diff after `alembic upgrade head` on a fresh database |

### API - over the ASGI app with httpx

| Area | What is asserted |
|---|---|
| Auth | Login, wrong password, expired and revoked sessions, logout |
| Permissions | Each role hitting each endpoint; 403 shape and error code |
| Validation | Bad payloads return 422 with useful details, not a stack trace |
| Lifecycle endpoints | Session transitions over HTTP, including conflict responses |
| Idempotency | A repeated award request does not double-award |
| Export | The session text export renders the expected structure |

### Frontend

- Vitest plus React Testing Library for the components where a regression would be
  embarrassing: the capture sheet, the origin trail, the activity renderer, the
  status controls, and the summary export fallback.
- One Playwright smoke test of the loop (create session, capture an idea, record a
  decision, create a task, close, read the summary). One, not a suite.

### The two tests that cannot be automated, and must still be run

1. **The five-second capture test.** A real person, a real phone, a stopwatch, from
   a standing start in a meeting context. It is a Phase 2 acceptance criterion, not
   a nice-to-have.
2. **The meeting rehearsal.** The loop on a throttled connection, on a real phone
   and a projector, with a guest and a late joiner. It catches the failures unit
   tests structurally cannot.

## 15. Deployment and runbook

Everything below is meant to be copied into `docs/deployment.md` and
`docs/development.md` during Phase 0 and kept current as those tickets land.

### First-time server setup

```bash
ssh deploy@<kbc-server>
sudo mkdir -p /opt/mshikaki && sudo chown deploy:deploy /opt/mshikaki
git clone <repo-url> /opt/mshikaki
cd /opt/mshikaki
cp .env.example .env
$EDITOR .env            # POSTGRES_PASSWORD, APP_SECRET_KEY, APP_PORT, ROOT_URL
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/api/health/ready
```

Expected result: two running containers (`app`, `db`), a healthy database, and
Mshikaki answering on the internal IP at the configured port.

### Local development

```bash
git clone <repo-url> && cd mshikaki
cp .env.example .env
make dev-db                 # postgres via docker compose -f docker-compose.dev.yml
make migrate                # alembic upgrade head
make seed                   # game definitions and content packs
make api                    # uvicorn on :8000
make web                    # vite on :5173, /api proxied to :8000
```

### Daily and release commands

| Task | Command |
|---|---|
| Run everything | `make check` (ruff, pytest, `tsc --noEmit`, vitest, type freshness) |
| Backend tests only | `make test` |
| Apply migrations | `make migrate` |
| Create a migration | `make migration name="add session lifecycle"` |
| Show migration state | `docker compose exec app alembic current && docker compose exec app alembic history` |
| Build images | `docker compose build` |
| Deploy an update | `git pull && docker compose up -d --build` |
| Watch logs | `docker compose logs -f app` (or `--tail=200 db`) |
| Shell into the app | `docker compose exec app bash` |
| Database shell | `docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB` |
| Health check | `curl -fsS http://localhost:8080/api/health/ready` |
| Send the digest manually | `docker compose exec app python -m app.cli send-digest` |

### Backups

```bash
# manual
./scripts/backup.sh                       # -> backups/mshikaki-YYYY-MM-DD-HHMM.sql.gz, 14-day rotation

# host cron, daily at 21:00 EAT
0 21 * * * cd /opt/mshikaki && ./scripts/backup.sh >> backups/backup.log 2>&1
```

Also copy the dump directory off the server to a second location. A backup on the
same disk as the database is not a backup, and the restore drill in P6-5 is what
proves it works.

### Restore

```bash
./scripts/restore.sh backups/mshikaki-2026-10-01-2100.sql.gz
# stops the app, restores into the existing database, restarts, then verifies:
curl -fsS http://localhost:8080/api/health/ready
```

### Upgrade and rollback

```bash
# upgrade
git pull
docker compose up -d --build          # entrypoint: wait for db -> alembic upgrade head -> uvicorn
docker compose ps && curl -fsS http://localhost:8080/api/health/ready

# rollback of application code
git checkout <previous-tag>
docker compose up -d --build

# rollback of a bad migration
#   prefer restoring the pre-upgrade dump over running a downgrade in a hurry.
#   Downgrades exist where they are safe, and this preference is stated in the runbook.
```

Deploy during a quiet window, not fifteen minutes before a session. A session in
progress is the one moment an upgrade must not happen.

### Troubleshooting index

| Symptom | First checks |
|---|---|
| Site does not load on the internal IP | `docker compose ps`; is the published port open in the KBC firewall; does `curl localhost:PORT` work on the server |
| `/api/health/ready` returns 503 | Database container health, `DATABASE_URL`, password in `.env`, disk space |
| App exits immediately on start | Required env var missing (`docker compose logs app`); the settings layer names the variable |
| Login succeeds then immediately fails | Cookie flags versus `SESSION_COOKIE_SECURE` when TLS is terminated upstream; check `ROOT_URL` |
| Migrations did not run | Entrypoint logs; `alembic current`; a migration file that failed halfway |
| Copy button does nothing in the summary | The browser is on an insecure origin (`http://10.x.x.x`); the fallback should have engaged - if not, that is a defect |
| Disk filling up | Container log rotation settings; `backups/` growth; Postgres WAL under the volume |
| Slow board or activity page | `EXPLAIN` the query; check the indexes from [04](04-data-model.md) are present |

## 16. Scope-cut strategy

If a phase starts expanding, cut in this order. Cutting is normal; the loop
surviving is the constraint.

| Phase | Cut first, in order |
|---|---|
| Phase 0 | Extra documentation beyond the four ADRs and the five required docs; the optional CI workflow (keep `make check`); the all-Docker development path |
| Phase 1 | Guest claiming until later; role editing UI beyond owner/member; invites by email (keep codes); structured logging beyond request ids |
| Phase 2 | Comments on decisions and blockers (keep them on ideas and tasks); agenda timeboxes; pause/resume (keep planned/active/completed); the Assign step's due-date picker (keep owner only) |
| Phase 3 | Task board (keep the list); projects entirely (keep session-scoped tasks and labels); search; team activity filters |
| Phase 4 | Achievements (keep XP and standings); seasons (keep per-session standings); `host_scored`; rich media packs; the digest's scheduling (keep the CLI command and a documented cron) |
| Phase 5 | Search UI; print stylesheet; digest polish; copy centralisation |
| Phase 6 | Database performance pass beyond the four hot queries; uptime monitoring beyond a cron health check |

Never cut: auth and team basics, the audit trail, Session Run Mode, ideas,
decisions, tasks with origin links, the summary with its text export, My Work, and
the ten invariants in [13-plan-brief.md](13-plan-brief.md). A cut that breaks the
loop is not a cut.

## Final test

**"Would I hand this repository to another developer and expect them to maintain
it?"**

The plan answers this in specific ways rather than with good intentions: two
containers instead of an orchestration story; one Dockerfile with two stages; a
conventional FastAPI layout that any Python developer recognises; REST with a
generated client type so drift is caught mechanically; one activity write path
reviewed as security-relevant code; migrations only; a runbook with the exact
commands; four ADRs that explain the choices that would otherwise be re-litigated;
and a `docs/standards.md` the existing review skill actually reads.

**"Would a team member look forward to opening Mshikaki at the start of a
meeting?"**

The plan protects this by sequencing: Run Mode is built in Phase 2 with the game,
not bolted on later, and the fun layer is allowed to be visually loud while the
record layer stays sober. The five-second capture criterion is a named acceptance
test rather than an aspiration, the summary exports as text people can paste into
WhatsApp, and the leaderboard is capped and opt-out-able so it stays a joke people
enjoy rather than a scoreboard they resent.

**The objective, restated:** the smallest system that makes meetings more enjoyable
while quietly producing useful, structured and auditable work. Everything in this
plan is either that loop, or support for it between meetings.
