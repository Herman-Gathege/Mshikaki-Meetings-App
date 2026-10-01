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

Implemented in `frontend/src/pages/play.tsx` and `app/services/games.py`:

question -> option cards and a shared countdown -> each player locks one answer
in on their own phone -> the host reveals -> the right answers are scored ->
next question (which opens a fresh window) -> results -> back into the meeting.

The clock belongs to the question, not to a browser: `question_started_at` and
`question_seconds` live on the play, `revealed_at` closes the window, and every
phone draws the same seconds. Answering locks that player in and stops nothing
for anybody else. Answers are one row per player per question (`game_answers`),
so a second tap is the same answer rather than a second point, and the room is
never handed the answer before the reveal.

The rules are pure functions in `backend/app/domain/quiz.py`: what counts as a
right answer, what the clock says, and what a right answer is worth (ten points,
plus five for answering in the first half of the window). Prompt decks have no
right answer, so they keep the host's manual "+10".

## Scoring and XP

A quiz question scores itself when the host reveals it, and one activity line
records the reveal. Games without a right answer are scored by the host tapping a
player. Any score can be corrected with a reason, and the correction is recorded.
On finish, positions are set and XP is awarded through the ledger: participation
always earns, winning earns more, and every award is idempotent, so finishing
twice does not pay twice. Caps and diminishing returns live in
`backend/app/domain/xp.py`.

Achievements are evaluated when a session closes, so the bragging rights settle at
the end of the meeting rather than mid-game.
