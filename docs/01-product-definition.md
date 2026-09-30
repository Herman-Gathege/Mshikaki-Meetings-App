# 01 - Product Definition

## One sentence

Mshikaki is a small web app where a team plays a quick game to warm up, then turns
the conversation that follows into ideas, decisions and assigned work - with a
record of who did what, automatically.

## The problem

Teams do not lack meetings. They lack the memory of meetings.

- Decisions get made verbally and evaporate. Two weeks later: "Who decided this?"
  "We discussed it but I don't remember what we agreed."
- Action items are spoken aloud, written in someone's notebook, and never
  assigned, so nothing happens and nobody is accountable.
- Meetings are also boring. People come in late, disengage, and the same two
  people talk.
- Minutes, when they exist at all, are manual, late, and written by whoever was
  unlucky. They capture the least important 20% of what happened.

Existing tools solve parts of this badly for this context. Heavy project tools
require training and daily discipline the team will not sustain. Chat tools
capture everything and remember nothing structured. Quiz tools are fun but produce
no work.

Mshikaki's bet: **fun is the wedge, and the audit trail is the value.** People show
up for the game. They leave with the record.

## The core loop

```
PLAY -> CONNECT -> THINK -> DISCUSS -> DECIDE -> ASSIGN -> DO -> RECORD
```

`RECORD` is not a step someone performs. It is the shadow of the other steps, cast
automatically by the system.

Every MVP 1 feature must be justifiable as "a step in this loop" or "supporting
the loop between meetings". If it is neither, it is out of scope.

## Who it is for

**Design target:** a team of roughly 5-25 people who meet regularly (weekly or
fortnightly), have a facilitator, and produce a mix of decisions and small pieces
of work.

**First real user:** the Innovations ICT team at KBC. This shapes the defaults -
English with Kenyan context, low-bandwidth friendliness, meet-in-a-room use, mixed
seniority and mixed technical confidence - but the architecture must not assume
KBC, ICT, or KBC's org structure. Teams, roles and game content are all data.

**Primary personas:**

| Persona | Wants | Cares about |
|---|---|---|
| Facilitator ("host") | To run a smooth, energetic session without being a note-taker | Low setup, no dead air, a summary at the end |
| Member ("player") | To be heard, to not be given homework verbally | 5-second capture on a phone, clarity about what they own |
| Lead / manager | To see what was decided and what is actually moving | Traceability, blockers surfaced early |
| Late joiner / absent colleague | To catch up without asking anyone | Session summary, activity feed, back-links |
| Guest participant | To take part once without an account | Zero-friction entry, clear limits |

## What Mshikaki is deliberately not

The positioning matters more than the feature list, because it is what stops the
product becoming an ever-growing enterprise suite.

| Not | Because |
|---|---|
| Jira / Asana / Linear | No epics, sprints, story points, custom workflows. Three status concepts, maximum. |
| Trello | Boards are one view of tasks, not the model. No "everything is a card". |
| Notion / Confluence | Documents are generated from what happened, not authored as a parallel truth. |
| Slack / WhatsApp | Mshikaki never tries to win the conversation. It captures the outcome of conversations that happen in the room. |
| Kahoot | Games exist to warm people up, not to be a quiz business. One small engine, not a games platform. |
| A performance system | The leaderboard is a cultural joke with scoreboards. Serious metrics live in a separate, unscored view. |

## Product principles

1. **One loop, not a suite.** Eight steps, one flow. New features attach to the
   loop instead of beside it.
2. **Fun is the entry fee, the record is the rent.** If a session produces no
   decisions or tasks, the app still earned its place by being a good meeting. If
   it produces tasks but no record, it failed.
3. **Meeting-shaped, not ticket-shaped.** The primary unit is a Session with a
   start and an end, not an infinite backlog.
4. **Capture in five seconds.** Adding an idea mid-discussion must never require a
   form, a category decision, or losing your train of thought. Everything is
   completable later.
5. **Mobile for capture, big screen for play.** Phones are how individuals add and
   read. A shared screen is how the room plays and reviews together.
6. **Every piece of work remembers where it came from.** Task -> Decision -> Idea
   -> Session must be walkable in both directions.
7. **The record is automatic or it does not exist.** Never ask a human to write
   minutes. If the system cannot observe an event, the event did not happen in the
   system.
8. **Zero training.** A team should run a real session on their first day,
   facilitated by someone who has seen the app once.
9. **Cheap on data and tolerant of bad wifi.** A 20-person room on shared
   bandwidth is the design constraint, not an edge case.
10. **No guilt mechanics.** No streaks that shame, no "you are behind" nagging, no
    overdue counts as public shaming. Pressure comes from people, not from red
    badges.

## Identity and tone

The name is a skewer. That metaphor is worth keeping, because it is exactly what
the product does: **a skewer threads separate pieces onto one stick so you can see
the whole thing at once.**

- Session summary = the skewer: attendance, games, ideas, decisions, tasks,
  blockers threaded together in order.
- Traceability = "this task is a piece on the Session #12 skewer."
- Tone: warm, competitive, self-aware, English-first, Kenyan-contextual. Trash talk
  allowed in the game layer; never in the task or decision layer.
- Deliberately avoid inventing Kiswahili terms to sound local. Use Kiswahili only
  where a word is genuinely well-understood; otherwise plain English. (See
  [09](09-risks-and-open-questions.md), open question 7.)

## Success criteria for MVP 1

The only meaningful test is whether Innovations runs a real weekly session in it.

**Adoption**

- One full session (Planning -> Active -> Completed) is run start to finish in the
  app, with no parallel notebook or WhatsApp thread carrying the real record.
- The facilitator does not need help during that session.
- Time from "start session" to "first task assigned" is under 45 minutes of a real
  meeting, without the tool dominating the meeting.

**Output quality**

- The session summary, generated automatically, is good enough to send to someone
  who missed the meeting, with no editing by a human.
- At least 80% of tasks created in the app still have a live owner and a status
  that reflects reality two weeks later.
- Every task can be traced to a session, and where relevant to an idea and a
  decision.
- Zero manual minute-writing.

**Engagement**

- At least one game is played in a majority of sessions that reach the Active
  state - without the facilitator being told to do it.
- People use the leaderboard voluntarily, and nobody has complained that it feels
  like surveillance.

## Anti-criteria: what would mean we got it wrong

- The team keeps using a notebook or WhatsApp for the real record while politely
  clicking through Mshikaki.
- The facilitator spends the meeting on the laptop instead of the room.
- The audit trail exists but nobody ever reads it.
- The app is used for two weeks and then dropped for a session, and the record has
  a hole that cannot be reconstructed.
- The leaderboard changes how people behave on real work in a way people resent.
