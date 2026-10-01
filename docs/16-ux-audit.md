# 16 - UX Audit: where Mshikaki makes people think

Written before the Phase 6 changes, from reading the code and walking the flow.
Each row is a defect against the standard "a first-time user knows what to do".

| Screen | Purpose | Problem | Fix |
|---|---|---|---|
| Shell | Get anywhere | Icon-less one-word nav, no way to see what is live | Icons with labels, and the running session always visible |
| Today | Start the day | Reads like a dashboard; the next meeting is one card among many | Lead with the next meeting, then my things, then what came out of the last one |
| Sessions list | Pick a meeting | Every row looks the same whether it is finished or live | Show state in words and colour, with one clear action per row |
| Session page | Understand a meeting | Tabs of records; a completed meeting does not tell its story | Lead with "What happened", then the skewer: games, ideas, decisions, tasks |
| Run Mode | Run the meeting | Steps are numbered tabs; the journey is never stated | Name the journey: Let's play, What are we thinking, What did we decide, Who's got this, That's a wrap |
| Game screen | Play | A prompt and a score list. No options, no timer, no reveal, no result | Full question lifecycle: options as cards, timer, reveal, per-question result, results screen, continue-to-meeting |
| Capture | Get an idea in | No feedback that it worked | Instant confirmation, then get out of the way |
| Summary | Read the minutes | Plain text only, no structure, nothing to download | Nine-section minutes, printable download, text export kept |
| Errors | Anywhere | Server codes shown as-is | Human sentence plus the code in the logs |
| Empty states | Anywhere | "Nothing yet" | Say what it is for and what to do, with a little personality |

## What was deliberately left alone

The five primary destinations, the domain model, the API shapes, the frozen
summary, the permission rules and the host-paced game engine. The audit found
presentation problems, not architecture problems.
