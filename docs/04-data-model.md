# 04 - Data Model

This is the minimum viable schema. It is written as implementation-neutral
pseudocode: enough to review and build from, not enough to copy blindly into a
framework-specific migration.

## Platform decisions

| Decision | Choice | Why |
|---|---|---|
| Database | **PostgreSQL** | JSONB for game config and activity payloads, real constraints, `timestamptz`, and it fits a relational domain better than a document store |
| Primary keys | `uuid` (v7/ULID) generated in the app | Sortable, safe to expose, no round trip to generate |
| Timestamps | `timestamptz`, stored UTC | Displayed in the team's timezone |
| Enums | `text` + `CHECK` constraint | Adding a status should be an ordinary migration; avoid native enum types for evolving sets |
| Deletion | `deleted_at timestamptz` soft delete everywhere | Audit trail and traceability require that history survives |
| Multi-tenancy | `team_id` on every domain table + mandatory filter | Row Level Security is a later phase; the column must exist from the first migration |
| JSONB | Allowed only for: activity payloads, game config, summary snapshots, achievement criteria, XP rule params | Never for fields that need querying or joining |
| Money / attachments / AI | Not modelled | Out of scope |

## Conventions

- Every table: `id uuid pk`, `created_at timestamptz not null default now()`,
  `updated_at timestamptz not null default now()`.
- Domain tables additionally: `team_id uuid not null references teams(id)`,
  `deleted_at timestamptz null`.
- Foreign keys are always explicit, `on delete restrict` by default. Cascades are
  used only for genuinely owned children (e.g. `game_score` -> `game_play`).
- Polymorphic references (`target_type`, `target_id`) are text + uuid with no FK,
  constrained by application code and a check on `target_type`. This trades
  referential integrity for one activity table instead of eight.

## Tables

### Tenancy

```text
organizations(id, name, slug unique, settings jsonb, created_at, updated_at)

teams(id, organization_id -> organizations, name, slug, description,
      timezone default 'Africa/Nairobi', settings jsonb, created_at, updated_at)

users(id, email citext unique, display_name, avatar_url, password_hash null,
      provider text null, locale, timezone,
      leaderboard_opt_out bool default false, last_seen_at,
      created_at, updated_at, deleted_at)

memberships(id, user_id -> users, team_id -> teams,
            role text check in ('owner','admin','facilitator','member'),
            status text check in ('invited','active','suspended'),
            joined_at, created_at, updated_at,
            unique(user_id, team_id))

invites(id, team_id -> teams, email citext null, code text unique, role text,
        invited_by -> users, expires_at, accepted_at, accepted_by, created_at)

guests(id, team_id -> teams, display_name, email citext null,
       linked_user_id -> users null, created_by -> users, created_at)
```

Notes: `users.email` is unique globally; a user can belong to several teams, so
"KBC Innovations" never becomes a column. Guests are team-scoped so the same
"Anne" typed twice in two teams cannot collide.

### Sessions

```text
sessions(id, team_id, title, sequence_no int, status text check in
         ('planned','active','paused','completed','cancelled'),
         scheduled_at timestamptz, started_at, ended_at,
         facilitator_id -> users, location text, timezone text,
         summary_snapshot jsonb null, summary_generated_at timestamptz null,
         created_by -> users, created_at, updated_at, deleted_at,
         unique(team_id, sequence_no))

session_participants(id, session_id -> sessions, user_id -> users null,
                     guest_id -> guests null,
                     role text check in ('facilitator','participant','observer'),
                     attended bool default false, joined_at, left_at, created_at,
                     check (user_id is not null or guest_id is not null))

agenda_items(id, session_id -> sessions, position int, title, notes,
             timebox_minutes int null, covered_at timestamptz null,
             created_at, updated_at)
```

Partial unique index for "one active session per team":
`unique(team_id) where status = 'active'`.

### Games

```text
game_definitions(id, key text unique, name, family text check in
                 ('prompt_deck','host_quiz','host_scored'), description,
                 config_schema jsonb, min_players, max_players, typical_minutes,
                 energy text, tags text[], source_type text, license text,
                 attribution text, active bool default true)

content_packs(id, game_definition_key text -> game_definitions(key), title,
              description, language text default 'en', license text not null,
              attribution text, source_url text, is_seed bool default false,
              created_by -> users null, created_at, updated_at, deleted_at)

game_questions(id, content_pack_id -> content_packs, position int,
               prompt text not null, answer text null, choices jsonb null,
               media_url text null, category text, difficulty text,
               explanation text null, created_at, updated_at)

game_plays(id, session_id -> sessions, game_definition_key text,
           content_pack_id null, host_id -> users,
           mode text, status text check in
           ('pending','running','finished','abandoned'),
           settings jsonb, started_at, ended_at, created_at)

game_scores(id, game_play_id -> game_plays on delete cascade,
            user_id -> users null, guest_id -> guests null,
            points int default 0, correct_count int, position int,
            source text check in ('auto','host'), adjusted_by -> users null,
            adjustment_reason text null, created_at)
```

### Work artefacts

```text
ideas(id, team_id, session_id null -> sessions, title, description,
      created_by -> users, status text check in
      ('new','discussing','accepted','parked','rejected','converted'),
      converted_to_type text null, converted_to_id uuid null,
      created_at, updated_at, deleted_at)

idea_tags(id, idea_id -> ideas on delete cascade, tag text,
          unique(idea_id, tag))

decisions(id, team_id, session_id null -> sessions, statement text not null,
          rationale text, decided_by -> users, decided_at timestamptz,
          supersedes_id -> decisions null, superseded_by_id -> decisions null,
          standalone_reason text null, created_at, updated_at, deleted_at,
          check (session_id is not null or standalone_reason is not null))

projects(id, team_id, name, description,
         status text check in ('active','paused','done'),
         owner_id -> users, created_at, updated_at, deleted_at)

tasks(id, team_id, project_id null -> projects, session_id null -> sessions,
      idea_id null -> ideas, decision_id null -> decisions, title, description,
      owner_id -> users null, status text check in
      ('backlog','in_progress','blocked','done','cancelled'),
      priority text check in ('low','normal','high','urgent') default 'normal',
      due_date date null, completed_at timestamptz null,
      cancelled_reason text null, created_by -> users, position int null,
      created_at, updated_at, deleted_at)

task_collaborators(id, task_id -> tasks on delete cascade, user_id -> users,
                   created_at, unique(task_id, user_id))

blockers(id, team_id, task_id null -> tasks, idea_id null -> ideas,
         reason text not null, raised_by -> users, raised_at timestamptz,
         resolved_by -> users null, resolved_at timestamptz null,
         resolution text null, created_at, updated_at,
         check (task_id is not null or idea_id is not null))

comments(id, team_id, target_type text check in
         ('idea','decision','task','blocker','session'),
         target_id uuid, author_id -> users, body text not null,
         created_at, updated_at, edited_at, deleted_at)
```

### The record

```text
activity(id, team_id, session_id null -> sessions,
         actor_type text check in ('user','guest','system'), actor_id uuid null,
         verb text not null, target_type text not null, target_id uuid null,
         payload jsonb, occurred_at timestamptz not null default now(),
         source text, visibility text default 'team' check in
         ('team','participants','admin'))

xp_rules(id, key text unique, label, amount int, cap_per_session int null,
         cap_per_day int null, cap_per_week int null, active bool default true,
         params jsonb)

seasons(id, team_id, name, starts_at, ends_at,
        status text check in ('upcoming','active','closed'))

xp_events(id, team_id, user_id -> users null, guest_id -> guests null,
          amount int not null, reason_key text -> xp_rules(key),
          source_type text, source_id uuid, awarded_by -> users null,
          season_id null -> seasons, occurred_at,
          idempotency_key text unique,
          check (user_id is not null or guest_id is not null))

achievements(id, key text unique, name, description, emoji, criteria jsonb,
             rarity text, active bool default true, scope text default 'team')

achievement_awards(id, achievement_id -> achievements, user_id null,
                   guest_id null, team_id, season_id null, awarded_at,
                   source_type text, source_id uuid, awarded_by -> users null,
                   revoked_at null, revoke_reason null)

notifications(id, user_id -> users, team_id, type, payload jsonb,
              created_at, sent_at, read_at)
```

## Indexes that matter

| Index | Serves |
|---|---|
| `activity(team_id, occurred_at desc)` | Team activity feed |
| `activity(session_id, occurred_at)` | Session history |
| `activity(target_type, target_id, occurred_at desc)` | "Activity on this task" |
| `tasks(team_id, status, due_date)` | Board and overdue views |
| `tasks(owner_id, status)` | Personal task list |
| `tasks(session_id)` | Session outputs |
| `tasks(idea_id)`, `tasks(decision_id)` | Back-link resolution |
| `sessions(team_id, scheduled_at desc)` | Session list |
| `game_scores(game_play_id)` | Results |
| `xp_events(team_id, season_id, user_id)` | Leaderboard aggregation |
| `comments(target_type, target_id, created_at)` | Threads |
| `memberships(team_id, role)` | Permission checks |

## Audit immutability

Enforce in the database, not only in code:

- The application's database role gets `INSERT` and `SELECT` on `activity`, but no
  `UPDATE` and no `DELETE`.
- Same for `xp_events` and `achievement_awards`.
- A separate maintenance role (used only by migrations) can prune. Pruning is an
  explicit, audited operational procedure, never a code path.

## Seed data required on day one

MVP 1 must never show an empty games screen.

| Seed | Size | Notes |
|---|---|---|
| Game definitions | 6-10 | Covering all three families; only two must be playable |
| General + Kenyan trivia questions | 60-80 | Author or license; attribution recorded |
| Rapid-fire / funny prompt cards | 40-60 | Low-risk, all original |
| "Name 5 things", true/false, emoji sets | 30-50 | Cheap engagement, no licensing risk |
| Achievements | 8-12 | See [07](07-leaderboard-xp.md) |
| XP rules | one per source | With caps set conservatively |

Content authoring is real work and is repeatedly underestimated. Budget it
explicitly rather than treating it as filler.

## Size and retention reality check

- One session produces roughly 40-120 activity rows, 3-8 ideas, 1-4 decisions,
  4-12 tasks, and 1-3 game plays.
- A weekly team over three years: order 15,000 activity rows and a few thousand
  domain rows. This is nothing for Postgres. Partitioning and archival are
  premature; the only thing to design for now is the indexes above.
- The expensive thing is not volume, it is **cold data being unavailable when
  someone asks "what did we decide in March?"** - which argues for search and
  export, not for pruning.

## Migration and versioning

- Migrations are the only way schema changes reach an environment. No manual
  database edits, including in development; they get silently lost and then
  reappear as production bugs.
- Every migration is reversible or explicitly marked irreversible with a reason.
- Seed content is versioned data, not a migration: content packs get updates
  without a schema change.
- Before the first real session: restore a backup into a scratch database and
  confirm the app starts against it. Untested backups are not backups.
