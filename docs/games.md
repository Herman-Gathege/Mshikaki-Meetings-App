# Games

The design is argued in [06-games.md](06-games.md) and the rules for the fun layer in
[07-leaderboard-xp.md](07-leaderboard-xp.md). This is how to work on them.

## Families

| Family | Playable in MVP 1 | Examples |
|---|---|---|
| `prompt_deck` | yes | Rapid Fire, Get to Know, Name 5 Things |
| `host_quiz` | yes | Kenyan Trivia, General Trivia, True or False, Emoji Guess |
| `host_scored` | catalogue plus manual scores | charades, guest-judged activities |

Timers, teams and rounds are modifiers, not families. Only one engine exists, and
it is host-paced: there is no per-phone realtime play.

## Content is data

```json
{
  "key": "trivia-kenya-01",
  "game_key": "trivia-kenya",
  "title": "Kenyan Trivia - Volume 1",
  "license": "original",
  "attribution": "Written for Mshikaki by the Innovations team",
  "items": [
    { "prompt": "What is the capital city of Kenya?", "answer": "Nairobi",
      "choices": ["Mombasa", "Nairobi", "Kisumu", "Nakuru"], "category": "geography" }
  ]
}
```

Add or edit a pack in `content/packs/`, then `make seed`. No migration, no deploy
of code, and no frontend change. `license` and `attribution` are required: a pack
without them does not ship.

Currently seeded: 8 packs, 129 items, including answer options for both quiz
packs, so the option cards have something to show.

## Adding a new game type

Within an existing family: add a `game_definitions` row in
`backend/app/seeds/__init__.py` and a content pack. Nothing else.

A new family would need a renderer, and that is the only case that touches code.
Design it so it does not need a migration.

## The question lifecycle

Implemented in `frontend/src/pages/play.tsx`, host-paced, verified by
`scripts/ux-game-flow.mjs`:

question and progress -> answer option cards -> timer -> single locked answer ->
reveal with the correct answer -> host scores the players who got it right ->
next question (which clears the previous answer) -> results -> back into the
meeting.

The timer runs locally and the questions arrive with the play, so playing does not
depend on the network. Starting an answer twice is impossible: the client locks
after the first choice and the plan never creates a second one.

## Scoring and XP

The host awards points by tapping a player, and can correct any score with a
reason, which is recorded. On finish, positions are set and XP is awarded through
the ledger: participation always earns, winning earns more, and every award is
idempotent, so finishing twice does not pay twice. Caps and diminishing returns
live in `backend/app/domain/xp.py`.

Achievements are evaluated when a session closes, so the bragging rights settle at
the end of the meeting rather than mid-game.
