# Database

PostgreSQL 16, one schema, migrations by Alembic. The schema itself is described
in [04-data-model.md](04-data-model.md) and the vocabulary in
[CONTEXT.md](../CONTEXT.md).

## Tables, grouped

| Group | Tables |
|---|---|
| Tenancy | `organizations`, `teams`, `users`, `memberships`, `invites`, `guests`, `auth_sessions` |
| The meeting | `sessions`, `session_participants`, `agenda_items` |
| Work | `ideas`, `idea_tags`, `decisions`, `projects`, `tasks`, `task_collaborators`, `blockers`, `comments` |
| Games | `game_definitions`, `content_packs`, `game_questions`, `game_plays`, `game_scores` |
| The record | `activity`, `xp_rules`, `seasons`, `xp_events`, `achievements`, `achievement_awards`, `notifications` |

Every domain table carries `team_id`. Soft delete is `deleted_at`; nothing is hard
deleted by a normal user.

## Migrations

```bash
make migrate                       # alembic upgrade head
make migration name="add x"        # autogenerate, then read it before committing
cd backend && uv run alembic current
```

Three so far:

| Revision | What it does |
|---|---|
| `0001_initial` | establishes the chain |
| `143b9ac0f90f` | identity, meetings, work, games and the record |
| `0003_append_only` | triggers that make `activity` and `xp_events` immutable |

Rules: migrations are the only way a schema change reaches an environment; never
edit a migration that has been applied anywhere but your own machine; models and
migrations must agree, and an autogenerate diff is a defect.

## Seeding content

`make seed` (and every container start) loads `content/packs/*.json`,
`game_definitions`, the XP rules and the achievements. It is idempotent and
updates questions **in place**: a game play stores the question ids it was created
with, so replacing rows would empty a quiz that is running. A test covers that.

## The append-only trigger

```sql
-- rejects UPDATE and DELETE on activity and xp_events, for every role
CREATE TRIGGER activity_append_only BEFORE UPDATE OR DELETE ON activity
  FOR EACH ROW EXECUTE FUNCTION mshikaki_reject_mutation();
```

`achievement_awards` is deliberately excluded: revoking an award sets
`revoked_at` by design, and that revocation is itself recorded in `activity`.

Verify it by trying to break it:

```bash
docker compose exec app python -c "
from app.db.session import get_session_factory
from sqlalchemy import text
db = get_session_factory()()
try:
    db.execute(text('DELETE FROM activity'))
except Exception as exc:
    db.rollback(); print('refused:', exc)
"
```

## Indexes that matter

`activity(team_id, occurred_at)`, `activity(session_id, occurred_at)`,
`activity(target_type, target_id, occurred_at)`, `tasks(team_id, status, due_date)`,
`tasks(owner_id, status)`, `xp_events(team_id, season_id, user_id)`,
`game_scores(game_play_id)`, `comments(target_type, target_id, created_at)`.

If a page feels slow, `EXPLAIN` the query before adding another index.

## Backups

See [deployment.md](deployment.md): `scripts/backup.sh` and `scripts/restore.sh`,
with the restore rehearsed rather than assumed.
