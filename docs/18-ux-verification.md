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
