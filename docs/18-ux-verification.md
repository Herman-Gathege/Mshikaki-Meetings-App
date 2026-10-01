# 18 - UX Verification: what was measured, and with what

Phase 6 asks for accessibility and bad-connection evidence rather than
assurances. These are the numbers, taken from the deployed app on 1 October 2026
at http://172.16.1.36:8090, driven through the Chrome DevTools Protocol.

## How to reproduce

```bash
# 1. A signed-in session and a live game to look at
cd backend && python -c "..."            # or register by hand and copy the cookie
# 2. Start Chrome with a debugging port and run the two audits
bash scripts/ux-audit.sh                 # structure, tap targets, throttling
bash scripts/ux-contrast-audit.sh        # keyboard focus, contrast, answer cards
```

The scripts read `/tmp/mshikaki-ux.json` (a session cookie, a session id and a
play id) and print a JSON report. They are throwaway tooling: keep them in
`scripts/` so the next person can re-run the same checks, not because they run
in CI.

## Keyboard and focus (6F)

Fourteen Tab presses on the phone-sized Today screen: every one landed on a
focusable control, and every one showed a visible 2px focus ring. Nothing was
reachable only by pointer.

## Contrast (6F)

Measured from the colours the browser actually paints, compositing translucent
card backgrounds over their real parents. Threshold is 4.5:1 for small text and
3:1 for large text.

| Screen | Sample | Before | After |
|---|---|---|---|
| Today | h1 | 17.46 | 17.46 |
| Today | section label | 6.19 | 6.19 |
| Today | brand link | **4.25** | 6.48 |
| Today | status badge | **2.58** | 5.83 |
| Today | muted meta | **2.89** | 6.55 |
| Run Mode (projector) | heading, body, buttons | 16.36 to 18.48 | unchanged |
| Game screen | question | 16.36 | 16.36 |
| Game screen | answer option | 14.16 | 14.16 |
| Game screen | timer | 6.48 | 6.48 |

Three failures were found and fixed by darkening the text tokens
(`ember-700`, `nile-700`) and using the readable muted token for meta text. The
final run reports zero failures.

## Tap targets (6F)

- Run Mode at projector size: no target under 44px.
- Game screen: answer cards are 72px tall, and the whole card is the button.
- Phone Today: the only controls under 44px are inline text links inside a
  sentence (an activity entry, "All 0"). They are treated as text, not controls,
  and the same destinations are reachable from the bottom navigation.

## Text scaling (6F)

With the browser's default font raised from 16px to 24px (which is what `rem`
units follow) and a 360px viewport: no horizontal scrolling and no element
pushed past the right edge on Today or on the game screen.

## What a screen reader is given (6F)

`scripts/ux-accessibility-tree.mjs` reads the browser's accessibility tree, which
is what a screen reader consumes.

| Screen | Landmarks | Structure | Named controls |
|---|---|---|---|
| Today | banner, main, navigation | one h1, then h2 sections with an h3 meeting title | all buttons and links named |
| Capture sheet | banner, main, navigation, **dialog: "Capture an idea"** | headings continue into the dialog | Close, Cancel, Save idea |
| Game | main | **h1 game name, h2 the question**, h2 Scores | all named, options announce as "A Mombasa" |

Two gaps were found and fixed: the game screen exposed no `main` landmark, and
the question was plain text rather than a heading. The game screen is where a
screen reader user most needs the structure, because the question is the whole
point of that screen.

## Errors and logs (6I)

Every request gets a reference. It appears in the response header, in the log
line, and in the body of a failure, so a user saying "it said something went
wrong" can be matched to the exact traceback.

```
2026-10-01 06:31:11,369 INFO mshikaki GET /api/nope -> 404 in 177ms [8de7e49ff691]
x-request-id: 8de7e49ff691
```

The interface never shows a status code. Known failures map to a sentence
("Please use your work email address"), and an unexpected one says "Something
went wrong on our side" with the reference to quote.

## The game flow, driven in a browser (6D)

`scripts/ux-game-flow.mjs` plays a round the way a room does and asserts what the
plan's acceptance test asks for. Last run, on the deployed app:

| Step | Observed |
|---|---|
| Question shown | "What is the capital city of Kenya?" |
| Progress | Question 1 of 18 |
| Timer | visible, and counting down: 20 to 17 over three seconds |
| Pick an answer | the card reports itself selected, and the whole card is the button |
| Second tap | ignored, one answer stays selected |
| Reveal | "❌ Not quite!" plus the correct answer |
| Score | the host awards a point and the score moves |
| Next question | moves to question 2, and the previous answer is cleared |
| End the game | results screen: "Game complete!", the winner, and final scores |
| Continue the meeting | links back to Run Mode for that session |

The same behaviour is covered on the server side in
`backend/tests/integration/test_game_and_minutes.py`, which also checks that
finishing twice does not award XP twice.

## The acceptance walk (Phase 6, section 39)

`scripts/ux-meeting-walkthrough.mjs` walks the steps of the plan's acceptance
test that the game-flow script does not cover. Last run, on the deployed app,
with a finished meeting that produced an idea, a decision and a task:

| Step | Observed |
|---|---|
| Enter Mshikaki | Today leads with the next meeting; the finished one appears under "From the last session" as "1 ideas · 1 decisions · 1 tasks" |
| Why does this exist | The task page offers **Decision** and **Session**; the decision offers the **Idea** and the session; the idea is marked converted and points back at the session |
| Close | The meeting reads as completed, with its summary |
| Minutes | A download link to `minutes.html` and the WhatsApp copy button |
| Final question | At question 18 of 18 the button becomes "See results →" |

Two defects were found by walking it rather than reasoning about it:

1. **The minutes download button did not exist.** The endpoint worked and the
   text export was there, so nothing looked wrong in the API; the button was
   simply never added to the summary tab by an earlier failed patch. Fixed.
2. **Buttons were nested inside links** in twelve places, which is invalid HTML
   and makes a screen reader announce one control twice. A `ButtonLink`
   primitive now renders a single element, and Today's controls are down to the
   three that are genuinely buttons.

## Bad connection (6G)

With Chrome throttled to 400 kbps and 400ms latency:

| Screen | Normal | Slow 3G |
|---|---|---|
| Run Mode | 298 ms | **1075 ms** |
| Game screen | 305 ms | **1052 ms** |
| Today | 592 ms | 576 ms |

The game screen stays around a second on a bad connection because the questions
arrive with the play and the timer runs locally. No transition between questions
touches the network.

Run Mode behaves the same way: it loads once and then only the room moves. The
first measurement of Today was 1959 ms, a cold load with an empty browser cache;
warm it settles at around 590 ms, and on a throttled connection it is unchanged
because the assets are already cached.

## What this does not prove

- A real projector, a real phone and a real room. Measured on a desktop Chrome at
  two viewport sizes only.
- Screen reader behaviour. Labels and roles were checked structurally; no screen
  reader was run.
- The human rehearsal in [17-ux.md](17-ux.md), which still needs a person who has
  never used Mshikaki.
