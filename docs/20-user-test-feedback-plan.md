# What the user test asked for, and how we would build it

Feedback from the first real user test, checked against the code rather than the
memory of it. Every item below has the evidence that produced it, the smallest
change that would satisfy it, and a test that would prove it works.

Nothing here is built yet. Three items need a decision from you first, and they
are marked **DECIDE**.

## What the test found, verified

| # | What you reported | What the code actually does | Severity |
|---|---|---|---|
| 1 | An existing account that scans the QR never appears in the attendees | `joining.join()` only creates a `session_participants` row on the sign-up path. The "Sign in instead" link goes to `/login` and drops the code, so signing in joins the team but never the meeting | P0 |
| 2 | A finished meeting "times out" instead of showing the meeting | The session page offers **Review Run Mode** for a completed meeting, and Run Mode instantly bounces completed meetings back with a toast. The button leads nowhere. The API is fine (27 ms) | P1 |
| 3 | "Anything else never appears in the minutes" | Minutes contain notes, ideas, decisions, actions, blockers, outcomes, game standings and attendance. They omit **comments**, **who answered what**, and **the trail of who did what** | P1 |
| 4 | When everyone has answered, the answer should show itself | The host screen already knows when the room is in (`answered.of` vs `answered.count`) but only uses it to relabel the button. Revealing is always a host tap | P1 |
| 5 | Locking an answer should not be automatic; you should be able to change it | `submit_answer` returns the existing row when a player answers twice, so the first tap is final | P2 |
| 6 | @ should assign names from the joiner list | Composer bodies are plain text. No mention is parsed, and the `notifications` table is unused (reserved for the digest) | P2 |
| 7 | Notes should be assignable, editable, and have states | `notes` has body, author and agenda item only. It has `updated_at`, so editing is nearly free; assignment and status do not exist | P2 |
| 8 | Similar actions for ideas | Ideas already have status (`new`, `discussing`, `accepted`, `parked`, `rejected`, `converted`) and editing, but only on the idea page. Inside the meeting, an idea can be added and not acted on | P2 |
| 9 | A section for adding questions to the session | There is no endpoint or screen for questions at all. Content comes from `content/packs/*.json` through `app.cli seed`, and `content.manage` exists but is unused | P1 |
| 10 | A standardised way of recording the round winner | Scoring is automatic (10 points, +5 for speed) and standings are aggregates. No round has a recorded winner; `position` is only set when the whole game finishes | P1 |
| 11 | After moving on, you should be able to visit the previous agenda item | The server can already jump to any item (`/agenda/{item}/current`), but the agenda screen has no previous control and covered items are not reachable | P2 |
| 12 | Add socket.io for realtime events | Everything is polling: stage 4 s, a live question 2 s, participants 10 s. There are no WebSockets, by an explicit rule in the MVP brief | **DECIDE** |

## Decisions I need before building

### D1. Realtime: socket.io, or make the polling smarter? (item 12)

The MVP brief says, in two places, "Do not introduce WebSockets or another
realtime system", and the deployment is deliberately one container plus
Postgres. Socket.io also has a wrinkle: the server is Python, so it would be
`python-socketio` mounted on the existing FastAPI app, not the Node library.

| Option | Cost | Effect |
|---|---|---|
| A. Keep polling, tune it | a day, no new dependency | stage changes still up to 4 s; a live question 2 s. Participants already see their own tap instantly |
| B. `python-socketio` on the same app | 2–3 days, one new dependency, no new container | stage, answers and reveals land in well under a second |
| C. A Node socket.io service beside the app | 4–5 days, second runtime and port to deploy | same as B, with more to break and more to explain to the next developer |

**My recommendation: B, if you want it now, done as a contained addition** — one
`/socket.io` endpoint and one client hook for the three meeting-critical streams
(stage, game state, notes/ideas), with polling left in place as the fallback so
a dropped socket cannot strand the room. C is not worth it here. A is what we
have, and it is honest to say the room may feel a beat behind.

### D2. Are notes becoming tasks? (item 7)

An assignable note with a status is most of a task. Two readings of your ask:

- **A. Notes carry an owner and a state** (pending, done, backlog) but stay notes.
  Meeting-shaped, quick, and the minutes can group them. Risk: two things that
  look like work, one of which never appears on the work board.
- **B. Tagging a note creates a task** linked to the note, the agenda item and the
  session. One place for work; notes stay scratchpad. Risk: the room has to
  understand the moment a note becomes work.

**My recommendation: A, with one guard rail** — a note marked done stays in the
minutes, and only the meeting's own record shows it. If you would rather keep one
kind of work, say so and we do B.

### D3. Scope of adding questions (item 9)

Two shapes:

- **A. Per-session questions**: the facilitator writes questions for this meeting
  only. Smallest thing that satisfies the ask.
- **B. Team content library**: questions are saved to the team and reusable in any
  meeting, with the existing licence and attribution fields kept.

**My recommendation: B, built as A first.** It reuses `content_packs` (already
has `created_by`, `license`, `attribution`) by adding a nullable `team_id`, so
seed packs stay global and a team's own packs are theirs. Same screens, and the
questions do not die with the meeting.

## The plan

### Phase A — what the test broke (do first)

| # | Ticket | Why | Acceptance test |
|---|---|---|---|
| A1 | **Join a meeting with the account you already have** (P0) | Attendance records are the product. Today the tester's name is missing from the room | An existing user scans the code, is offered "Join as Herman", and appears in the attendee list with a `session.participant_joined` trail row. Signing in from the join page carries the code and lands in the meeting |
| A2 | **A finished meeting opens and can be reviewed** (P1) | "Review Run Mode" currently bounces; the tester called it a timeout | A completed session shows its agenda, outcomes, notes, decisions, actions and game in a read-only review. No spinner dead-end, no bounce loop |
| A3 | **Minutes include the rest of the meeting** (P1) | The tester's downloaded minutes were missing what they saw | Comments on ideas and decisions, each round's winner, and a "who did what" line appear in HTML, PDF and text |
| A4 | **Reveal when the room is in** (P1) | The room waits on the host | With every player answered, the answer reveals itself; the host can still skip early; the clock still ends the round when somebody is away |

### Phase B — the room's asks

| # | Ticket | Why | Acceptance test |
|---|---|---|---|
| B1 | **Change your answer until the clock stops** (P2) | A mis-tap currently locks you out | Tapping another option replaces the answer and says it can still change; after the reveal it cannot |
| B2 | **Previous agenda item** (P2) | Facilitators jump back to a covered item | "Previous" and clicking a covered item move the room back; participants follow |
| B3 | **Notes: edit, assign, states** (P2) | The tester asked for it directly | A note can be edited, given an owner from the room, and marked pending / done / backlog, surviving a refresh and appearing in the minutes |
| B4 | **@ mentions from the joiner list** (P2) | Assigning by name is how people actually talk | Typing @ offers the room's people; the saved note names them; the trail records who was named |
| B5 | **Act on an idea inside the meeting** (P2) | Ideas can be accepted or parked without leaving the agenda | Accept, park, reject and convert work from the agenda screen, reusing the existing endpoints |

### Phase C — the bigger asks

| # | Ticket | Why | Acceptance test |
|---|---|---|---|
| C1 | **Questions for the session** (P1) | No question authoring exists at all | The facilitator writes questions in the app, starts the game from them, and the minutes show them |
| C2 | **A standard winner per round** (P1) | "so that the participants are actually being recorded truthfully as the winner of the round" | Every round names its winner from the answers, ties are handled the same way every time, and the minutes record it |
| C3 | **Realtime** (DECIDE) | The tester asked for socket.io | A player's answer and the facilitator's stage change appear on every screen in under a second, with polling as the fallback |

## How C2 would work, since it needs a rule

The honest options for a quiz round, in order of preference:

1. **Most points that round wins**, which is already what the scoring measures:
   a right answer is 10, +5 for answering in the first half. Ties go to the
   fastest correct answer, and a tie that is also equal in speed names both.
2. **First correct answer wins**, which ignores the scoring we already have.
3. **The host picks**, which is the thing you said you did not want.

I would build 1 and record it: `game.answer_revealed` already fires, so the
winner is written at the same moment and appears on the host screen, the player
screens and in the minutes.

## What this plan deliberately does not do

- No chat, no calendar, no dashboards, no time tracking, no new project concepts.
- No second meeting engine, and no new state-management library.
- No change to the permission model beyond one row (`session.join.self`) so a
  team member can add themselves to a live meeting, which is a permission the
  matrix test will cover like every other row.
- No rewrite of the game engine: C2 and A4 are additions to the reveal step.

## Order of work, and what lands first

1. **A1 and A2** — the two things that a room would notice immediately, and both
   are small. A day together with tests.
2. **A4, A3** — the game reveal and the minutes.
3. **B1–B5** — the meeting ergonomics, which are independent of each other.
4. **C1, C2** — question authoring and the round winner.
5. **C3** — realtime, once you have decided, and ideally after the room has been
   used once more so we know whether the lag is actually felt.

## Risks

| Risk | Why it matters | What I would do |
|---|---|---|
| The join change touches the most used path | A broken join is worse than the bug | Keep the register path untouched, add the signed-in path beside it, and test both |
| Run Mode's release logic has careful guards | A wrong guard bounces the facilitator mid-meeting | Add the read-only review as a separate branch, and keep the existing tests green |
| Adding `team_id` to content packs | Seed packs are global today | Nullable column, `NULL` means global, and the seeder keeps writing global packs |
| Realtime changes the deployment story | One container is a selling point | Only if C3 is chosen, mounted on the existing app, with polling kept as the fallback |
