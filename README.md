# Mshikaki

> "We came to the meeting to play. Somehow we left with assigned tasks."

A small, playful collaboration tool for team sessions: play an icebreaker, capture
ideas, record decisions, assign real work, and end up with an automatic audit trail
of everything that happened.

```
PLAY -> CONNECT -> THINK -> DISCUSS -> DECIDE -> ASSIGN -> DO -> RECORD
```

The fun layer gets people into the room. The record is why it exists.

## Status

MVP 1 is built, tested and deployed. It runs on the KBC intranet at
**http://172.16.1.36:8090** (see [docs/deployment.md](docs/deployment.md) for the
server, and [docs/15-phase-6.md](docs/15-phase-6.md) for where the current phase
stands).

## Run it yourself

```bash
cp .env.example .env          # set APP_SECRET_KEY and POSTGRES_PASSWORD
make dev-db                   # Postgres in Docker on 127.0.0.1:5432
make migrate                  # create the schema
make seed                     # game definitions and content packs
make api                      # API on http://localhost:8000
make web                      # frontend on http://localhost:5173
```

`make check` runs lint, tests and type checks. `make help` lists everything.
Requirements and troubleshooting: [docs/development.md](docs/development.md).

## What it does

| Piece | What a person sees |
|---|---|
| Sessions | Plan a meeting, run it in Run Mode, close it for the minutes |
| Games | A library of icebreakers and quizzes, host-paced on a shared screen |
| Ideas | Capture in one line, from a phone, mid-conversation |
| Decisions | Record what the team agreed, and what came of it |
| Tasks | One owner, a due date, blockers, and where it came from |
| Record | Every meaningful action, in order, attributed, uneditable |
| Bragging rights | XP, achievements and a seasonal leaderboard. For fun |

## Repository layout

| Path | What lives there |
|---|---|
| `backend/` | FastAPI: `api/` routers, `services/` orchestration, `domain/` pure rules, `db/` models |
| `frontend/` | React + TypeScript + Vite SPA, one folder per feature |
| `content/` | Game content packs as JSON, validated and seeded |
| `docs/` | The discovery pack, the plan, the operational runbooks |
| `scripts/` | Backup, restore, and the browser audits |

## Documentation

| Document | Read it when |
|---|---|
| [docs/architecture.md](docs/architecture.md) | You want to know how the pieces fit |
| [docs/development.md](docs/development.md) | You are running it locally |
| [docs/deployment.md](docs/deployment.md) | You are deploying or recovering it on the KBC server |
| [docs/database.md](docs/database.md) | You are changing the schema or loading content |
| [docs/audit-trail.md](docs/audit-trail.md) | You are touching anything that must be recorded |
| [docs/permissions.md](docs/permissions.md) | You are changing who may do what |
| [docs/games.md](docs/games.md) | You are adding content or a game type |
| [docs/standards.md](docs/standards.md) | You are about to write code |
| [docs/17-ux.md](docs/17-ux.md) | You are changing how it feels, and the rehearsal checklist |
| [docs/18-ux-verification.md](docs/18-ux-verification.md) | You want the measured evidence, or to re-run the audits |
| [docs/14-implementation-plan.md](docs/14-implementation-plan.md) | You want the plan and the phase history |
| [docs/README.md](docs/README.md) | You want the product thinking behind all of it |
| [AGENTS.md](AGENTS.md) | You are an agent, or you want the non-negotiable rules |
| [CONTEXT.md](CONTEXT.md) | You need the domain vocabulary |

## Tests

```bash
make check                                   # everything a developer runs
cd backend && uv run pytest                  # backend, including the permission matrix
cd frontend && npm test                      # component tests
./scripts/ux-audit.sh                        # structure, tap targets, throttled timings
./scripts/ux-contrast-audit.sh               # focus rings, contrast, text scaling
./scripts/ux-meeting-walkthrough.mjs         # the post-meeting acceptance steps
```

## Deliberately not built

No chat, no calendars, no file attachments, no AI, no per-phone realtime play, no
custom workflows, no portfolio management. The reasons are in
[docs/02-mvp-scope.md](docs/02-mvp-scope.md), and that document is a contract:
new scope enters by removing scope.
