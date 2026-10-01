# Development

## Requirements

Docker, [uv](https://docs.astral.sh/uv/), Node 20+ and GNU Make. The backend
targets Python 3.12, pinned in `backend/.python-version` so uv fetches the same
version the container uses.

## First run

```bash
cp .env.example .env          # set APP_SECRET_KEY and POSTGRES_PASSWORD
make dev-db                   # Postgres in Docker on 127.0.0.1:5432
make migrate                  # create the schema
make seed                     # game definitions and content packs
make api                      # http://localhost:8000
make web                      # http://localhost:5173, proxies /api to 8000
```

`make help` lists every command. `make check` runs lint, tests, type checks and
the format check.

## Working agreements

- The invariants in [AGENTS.md](../AGENTS.md) are not negotiable. Read them before
  changing a service.
- Domain rules go in `app/domain/`, never in a router.
- Every mutating endpoint gets a test asserting its activity row.
- `make check` passes before a commit.
- Style and review expectations: [standards.md](standards.md).

## Tests

| Command | What it runs |
|---|---|
| `make test` | Backend and frontend suites |
| `cd backend && uv run pytest` | 27 tests, unit and integration |
| `cd backend && uv run pytest tests/unit` | Pure rules, no database needed |
| `cd frontend && npm test` | Component and utility tests |
| `./scripts/ux-audit.sh` | Structure, tap targets, throttled timings |
| `./scripts/ux-contrast-audit.sh` | Focus rings, contrast, text scaling |
| `./scripts/ux-accessibility-tree.mjs` | What a screen reader is given |
| `./scripts/ux-game-flow.mjs` | Plays a game the way a room does |
| `./scripts/ux-meeting-walkthrough.mjs` | The post-meeting acceptance steps |

The integration tests need a database and skip themselves without one. The
browser audits need `/tmp/mshikaki-ux.json` with a session cookie, a session id
and a play id; see [18-ux-verification.md](18-ux-verification.md).

## Things that cost me time, so they do not cost you any

- **`TestClient` hangs on plain `httpx`.** FastAPI 0.142 with Starlette 1.7 needs
  `httpx2`, which is why both are dev dependencies.
- **`vite.config.ts` needs `@types/node`.** Otherwise `node:url` does not type
  check.
- **A Pydantic settings model as a route default becomes a second request body.**
  Always `Depends(get_settings)`.
- **Seeding must update questions in place.** A game play holds question ids; replacing
  rows empties a quiz that is running.
- **`exactOptionalPropertyTypes` is off** in `frontend/tsconfig.json`. It fights
  ordinary React prop patterns more than it catches real problems.
- **Local Docker must be running** for `make dev-db` and any compose command. In a
  restricted shell, binding sockets and the thread pool may be blocked, which
  makes FastAPI's test client and any dev server hang. If that happens, run the
  command outside the sandbox rather than debugging the app.

## Frontend notes

- Tailwind v4 with tokens in `src/styles/index.css`. Add colours there, not as
  one-off classes.
- Primitives live in `src/components/ui/kit.tsx` and are edited in place.
- Navigation is a link, not a button: use `ButtonLink` for anything that goes
  somewhere or downloads something.
- Screens must work at 360px. Run Mode is the one screen-first exception.
