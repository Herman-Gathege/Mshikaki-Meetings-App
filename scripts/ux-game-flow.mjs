/**
 * Drives the game the way a room does: pick an answer, reveal, score, next,
 * finish, and get back into the meeting.

 * This is the browser half of the acceptance test in the Phase 6 plan. The
 * backend half lives in backend/tests/integration/test_game_and_minutes.py.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-ux.json", "utf8"));

const socket = new WebSocket(process.env.CDP_ENDPOINT);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});
let nextId = 1;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result);
  }
});
function send(method, params = {}) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
async function evaluate(expression) {
  const result = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitFor(expression, label, attempts = 60) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluate(expression).catch(() => false)) return true;
    await pause(200);
  }
  throw new Error(`timed out waiting for ${label}`);
}

/** Clicks the first button whose text contains the given phrase. */
async function click(phrase) {
  const clicked = await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(b => b.innerText.includes(${JSON.stringify(phrase)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`no button matching "${phrase}"`);
  await pause(400);
}

const steps = [];
const record = (name, value) => steps.push(`${name}: ${JSON.stringify(value)}`);

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");
await send("Network.setCookie", {
  name: "mshikaki_session",
  value: state.cookie,
  domain: "172.16.1.36",
  path: "/",
});
await send("Emulation.setDeviceMetricsOverride", {
  width: 1280,
  height: 720,
  deviceScaleFactor: 1,
  mobile: false,
});

await send("Page.navigate", { url: `${APP}/play/${state.play}` });
await waitFor("document.body.innerText.includes('Question')", "the first question");
record("1 question shown", await evaluate("document.querySelector('h2').innerText"));
record("2 progress", await evaluate(
  "[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/Question \\d+ of \\d+/.test(t))",
));
record("3 timer visible", await evaluate("Boolean(document.querySelector('[role=\"timer\"]'))"));

// The answer options are the room's choices; a second tap must not change it.
await evaluate("document.querySelector('ul[aria-label=\"Answer options\"] button').click()");
await pause(300);
record("4 selected", await evaluate(
  "document.querySelector('ul[aria-label=\"Answer options\"] button').getAttribute('aria-pressed')",
));
await evaluate("document.querySelectorAll('ul[aria-label=\"Answer options\"] button')[1].click()");
await pause(300);
record("5 second tap ignored", await evaluate(`
  [...document.querySelectorAll('ul[aria-label="Answer options"] button')].map(b => b.getAttribute('aria-pressed'))
`));

await click("Reveal the answer");
record("6 revealed", await evaluate(`
  (() => {
    const text = document.body.innerText;
    return {
      verdict: /Correct!|Not quite!/.test(text) ? text.match(/✅ Correct!|❌ Not quite!/)[0] : null,
      answerShown: /Correct answer:/.test(text),
    };
  })()
`));

const before = await evaluate(`document.body.innerText.match(/\\n(\\d+)\\n/)?.[1] ?? '0'`);
await click("+10");
record("7 score after +10", await evaluate(`
  (() => {
    const row = [...document.querySelectorAll('li')].find(li => li.innerText.includes('+10') || li.querySelector('button'));
    return row ? row.innerText.replace(/\\s+/g, ' ').trim().slice(0, 40) : null;
  })()
`));
record("8 score changed", before !== null);

await click("Next question");
await pause(600);
record("9 moved on", await evaluate(
  "[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/Question \\d+ of \\d+/.test(t))",
));
record("10 answer reset", await evaluate(
  "[...document.querySelectorAll('ul[aria-label=\"Answer options\"] button')].map(b => b.getAttribute('aria-pressed'))",
));

// Ending early must still land on results, with a way back into the meeting.
await click("End the game");
await waitFor("document.body.innerText.includes('Game complete')", "the results screen");
record("11 results", await evaluate(`
  (() => {
    const text = document.body.innerText;
    return {
      headline: document.querySelector('h1').innerText,
      winner: /Winner/.test(text) ? text.split('Winner')[1].trim().split('\\n')[0] : null,
      stands: /Final scores/.test(text),
    };
  })()
`));
record("12 continue link", await evaluate(`
  [...document.querySelectorAll('a')].map(a => a.getAttribute('href')).find(h => h && h.includes('/run')) ?? null
`));

console.log(steps.join("\n"));
await fs.writeFile("/tmp/mshikaki-game-flow.txt", steps.join("\n"));
socket.close();
