# 15 - Phase 6: Human UX, Play Experience and Production Hardening

This replaces the previous one-paragraph Phase 6 in
[14-implementation-plan.md](14-implementation-plan.md). It is the authoritative
definition of the current phase.

The MVP works and is not being rebuilt. Every item below is a surgical change to
existing behaviour, APIs and data, in service of one standard:

> A first-time user should know exactly what to do, without training.

## The rule that governs every decision

**If a user needs to understand the domain model to know which button to press,
the UX has failed.** Nobody should have to learn the words session, idea,
decision, task, project, activity or XP before using Mshikaki.

Every screen answers three questions: what am I doing, what just happened, and
what do I do next.

## What must not change

The domain model, the API contracts, the frozen summary, the append-only activity
trail, the permission model, the single game engine, and the no-realtime rule.
No chat, no AI, no calendar, no second game engine, no new entity types.

## The ten workstreams

### 6A - Human UX

Plain language over domain language ("Who's doing this?" not "Assign task owner"),
one obvious action per screen, and never a technical error in front of a user.
Confusion found in rehearsal is treated as a defect.

### 6B - Mshikaki visual identity

The skewer metaphor made visible: pieces threaded onto one stick. Session to idea
to decision to task should be *seen*, not explained. Icons plus labels in
navigation, consistent cards, badges and states. Playful but never childish:
80% clarity, 15% personality, 5% surprise.

### 6C - Meeting/session UX

A session reads like a meeting, not a database row: what it is, who is in it,
what happened. A completed session leads with "What happened" and then the games,
ideas, decisions and tasks it produced.

### 6D - Game/play UX

The signature experience. Screen-first for a projector, driven by the host, with
a player-facing lifecycle that never leaks engine or database language: question,
options, timer, selection, reveal, result, next, results, and a way back into the
meeting. Host-paced confirmation is preserved; there is no per-phone realtime
play.

### 6E - Session minutes and exports

The frozen summary presented as real meeting minutes, structured in nine
sections, downloadable as a printable document, with the plain-text export kept
because it is what people paste into WhatsApp. Regeneration stays explicit and
audited.

### 6F - Accessibility and real-room usability

360px phones, keyboard navigation, focus states, contrast that survives a
projector, 44px targets, labelled forms, accessible dialogs, and no state
communicated by colour alone.

### 6G - Performance and bad-connectivity hardening

Run Mode, question transitions, capture and close tested on a throttled
connection. Content is preloaded; the timer never depends on a round trip;
duplicate submissions are prevented.

### 6H - Permission/tenancy/audit hardening

Cross-team access impossible, permissions enforced in one place, facilitator
powers session-scoped, activity append-only, attributed and contextual, soft
delete audited. UX never weakens security.

### 6I - Operational hardening

Structured logs, error visibility, backup and a rehearsed restore, health checks,
production configuration checks, and a runbook another KBC developer can follow.

### 6J - Full human rehearsal

A person who has never used Mshikaki is asked to "run a meeting", without
instruction, and every hesitation is recorded as a UX defect.

## Definition of done

Phase 6 is done when a first-time user can, unaided: understand the navigation,
start a session, play a game, capture an idea, record a decision, assign a task,
close the meeting and find the minutes.

## Status

Done and verified on the deployed app:

- **6A/6B** Plain-language journeys in Run Mode, the five primary destinations
  kept, icons in navigation, status badges that carry a word and a mark, and
  confirmations after every important action.
- **6C** Sessions list with one action per state, including Start, and Today
  rebuilt around the three questions. A completed meeting reports what happened,
  and a meeting that is not going ahead can be cancelled with a reason in the
  record.
- **6D** The full question lifecycle: options, local timer, single locked answer,
  reveal with the correct answer, host scoring, results, and Continue the
  meeting. No per-phone realtime. Driven end to end in a browser by
  `scripts/ux-game-flow.mjs` and on the server by the integration tests. Prompt
  decks follow the same screen without a reveal, because there is no answer to
  reveal.
- **6E** Nine-section minutes generated from the frozen summary, downloadable as
  a printable document, with the WhatsApp text export kept. The download button
  was missing until the acceptance walk found it.
- **6H** Append-only enforced by database trigger on `activity` and
  `xp_events`, refused actions recorded for admins, tenancy and permission tests
  in the suite, and the permission matrix unit-tested.
- **6I** Backup and restore scripts with a rehearsal step, a CI workflow that
  runs the same gate as a developer, health checks, and a deploy that applies
  migrations and seeds itself.

Open:

- **6F** Partial. Keyboard focus, contrast, tap targets, text scaling and the
  accessibility tree are measured and passing
  ([18-ux-verification.md](18-ux-verification.md)). Still to do: a real
  projector, a real phone, and listening to an actual screen reader.
- **6G** Partial. Run Mode and the game screen both hold at just over a second on
  throttled 3G, measured ([18-ux-verification.md](18-ux-verification.md)). Not yet
  tested on a real phone on a real KBC connection.
- **6J** Partial. A rehearsal by proxy walks the whole journey in a clean browser
  and found three real defects, all fixed. A second walk covers the returning
  user: signing in, creating the invite and its QR on the Team page, the projector
  view, the leaderboard and the activity trail
  ([18-ux-verification.md](18-ux-verification.md)). The human half - a person
  hesitating, and whether the room wants to come back - still needs a person. The
  checklist is in [17-ux.md](17-ux.md).
