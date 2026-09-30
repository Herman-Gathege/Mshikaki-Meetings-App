# 06 - Game Architecture

## Principle

Games are the **engagement layer**, not the product. They are allowed to be
pointless. The only requirements are: everyone can participate, nobody is
embarrassed, and it takes five minutes.

The single biggest risk in this document set is games. Software that lets a room
play a quiz together is closer to a realtime multiplayer product than to a task
tracker, and it can quietly consume more effort than sessions, ideas, decisions and
tasks combined. This architecture is designed to cap that cost.

## Game families

Every game type in the brief collapses into one of three families. That is the
whole classification scheme - do not add a fourth without a concrete game that
cannot be expressed in these three.

| Family | How it plays | Scoring | Examples from the brief |
|---|---|---|---|
| `prompt_deck` | Host reveals a card, people answer aloud. No right answer. | none / optional host award | rapid-fire questions, funny random questions, "name 5 things" (loosely), memory starters |
| `host_quiz` | Host reveals a question, room answers, host confirms the correct answer, points awarded | host-paced, correct answers | trivia (Kenyan, general, sports, geography, history), true/false, emoji guessing, "who said it?", picture guessing, music, riddles with answers |
| `host_scored` | Host runs an activity that is judged by a human | host judgement | riddles without answers, guessing games, charades-style, team challenges, judged word games |

Timer, team-vs-team, rounds and difficulty are **modifiers** applied to any
family, not new families.

## The MVP 1 decision: one playable engine, one non-playable format

**In MVP 1:**

1. `prompt_deck` - fully playable. Cards on the shared screen, host taps next.
   Optional "award a point" for a good answer. No per-phone anything.
2. `host_quiz` - fully playable. The room answers out loud, the host taps the
   player who got it, the app keeps score and shows the leaderboard at the end.
3. `host_scored` - catalogue entry and manual score entry only. The host enters
   final standings by hand.

**Not in MVP 1:**

- Per-phone answering, live buzzers, realtime sync, per-question latency,
  anti-cheat, spectator screens, chat during play.
- User-authored question sets through the UI (JSON seed and admin import only).
- Tournaments, brackets, brackets between teams, cross-session ladders for games.

### Why not per-phone play yet

- It needs a realtime transport, reconnection handling, and a per-player identity
  and scoring model that survives a dropped connection mid-answer.
- Network fairness becomes a product problem: a speed bonus on shared wifi
  rewards whoever is nearest the router, and the room notices.
- It multiplies the test matrix (iOS Safari + Android Chrome + projector
  browsers) exactly where the app is least critical to its own value.

The data model in [03](03-domain-model.md) already stores `game_play`,
`game_scores` and per-player rows, so adding per-phone play later is an additive
change, not a rewrite. The **only** thing to protect now is that a play does not
assume "one device, one score".

## The engine

One engine, driven by configuration, with three renderers:

```text
game_definition (key, family, config_schema)
        |
        v
content_pack (title, language, license, attribution)
        |
        v
game_questions[] (prompt, answer, choices, media, category, difficulty)
        |
        v
game_play (session, host, mode, settings)  ---> renderer chosen by family
        |
        v
game_scores[] (player, points, correct_count, position, source, adjusted_by)
```

### Adding a new game type

Adding game type number 11 should require:

1. A `game_definitions` row with a `config_schema`.
2. A `content_pack` with content.
3. Zero or small renderer changes if it fits an existing family.

If adding a game type requires a migration or a new backend endpoint, the
abstraction is wrong.

### Host always wins

Every automated score must be overridable by the host, and every override is
audited (`source`, `adjusted_by`, `adjustment_reason`). Real rooms are messy: the
host may need to award a point to a guest who shouted the answer, or fix a
mis-tap. A game engine that cannot be corrected in front of an audience will make
the host look foolish, which kills adoption faster than any missing feature.

### Room reality: offline tolerance

- A content pack is loaded into the host's browser before play starts, so a mid-quiz
  wifi drop does not stop the game.
- Scores are held locally during play and flushed when the connection returns.
- Media-heavy content (music, pictures) is optional per pack and marked with size
  so the host can avoid it on a bad connection. Images: single, compressed,
  lazy-loaded. Audio: short clips, licensed only.
- No game in MVP 1 requires any player other than the host to have connectivity.

## Content

Content is the expensive part, and the licensed part.

| Rule | Detail |
|---|---|
| Every pack declares a license | `content_pack.license` and `attribution` are non-null. Unknown licence means the pack does not ship |
| No lyrics, no film quotes, no magazine questions | Copyright risk without a licence. Write original variants instead |
| Original content is preferred | Cheap to write, no attribution, and it can be genuinely Kenyan |
| Local and global mix | A Kenyan team that only gets Kenyan trivia and only gets UK/US trivia are both badly served. Aim for roughly 50/50 per pack |
| Language | English-first. Kiswahili appears where it is genuinely common (proverbs, place names, food). Do not machine-translate a pack and call it localised |
| Age and seniority mix | Nothing that requires social media knowledge or current pop-culture from one narrow decade, since the team spans ages |
| Never embarrassing | No questions about a specific person in the room without their consent |
| Media is the exception | A pack with images or audio is a "rich pack": small file sizes, no external hotlinks |

### Starter content budget

Estimates for shipping MVP 1 without an empty library:

- 3 trivia packs x 20-25 questions (general, Kenya, sports/geography)
- 1 true/false pack, 20 items
- 1 emoji / picture pack, 15-20 items
- 3 prompt decks x 15-20 cards (rapid-fire, funny icebreakers, "name 5 things")
- 1 host-scored activity, 10 prompts, manual scoring

That is roughly 200 content items. Treat this as a deliverable with an owner, not
as something to write at the end if there is time.

## Scoring fairness

- **Correct beats fast.** Speed bonuses are capped at a small share of points and
  are off by default. A shared laptop with a trackpad is not a fair speed contest.
- **No negative scoring** unless a specific game is designed around it, and never
  in a way that punishes a participant for playing.
- **Participation earns something.** Turning up and playing is worth a small fixed
  amount; it is the participation-as-engagement signal that XP is for. See
  [07](07-leaderboard-xp.md) for caps.
- **Position over points** is what is displayed for games: 1st, 2nd, 3rd. Nobody
  remembers XP totals; everybody remembers who lost.

## Game results and the session

When a play finishes:

- The session records: game, pack, duration, players, standings.
- The session summary includes a single line per game, plus the winner.
- XP is awarded via `xp_events` with caps per session, so a game-heavy session
  cannot dominate the season.
- Guests who played appear in standings and can receive XP without an account.

## What the game layer must not do

- Must not become the reason sessions happen. If the team stops playing games and
  still records decisions and tasks, Mshikaki is still working.
- Must not introduce its own user concepts (no separate "player" account).
- Must not gate the meeting loop behind connectivity or content.
- Must not leak into serious metrics. Games are never used to evaluate anyone.
- Must not require a facilitator to memorise rules inside the app. A game card
  must be runnable by someone who has never played it: how long, how many people,
  what the host says first.
