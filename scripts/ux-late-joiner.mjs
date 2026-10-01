/**
 * Somebody scans the code while the meeting is already running.

 * They should land on the stage the room is on, not on a stale session page or a
 * dashboard, and they should be able to participate from wherever they arrived.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-late.json", "utf8"));

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
function send(method, params = {}, sessionId) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const { browserContextId } = await send("Target.createBrowserContext");
const { targetId } = await send("Target.createTarget", {
  url: "about:blank",
  browserContextId,
});
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
await send("Page.enable", {}, sessionId);
await send("Runtime.enable", {}, sessionId);
await send("Network.enable", {}, sessionId);
await send(
  "Emulation.setDeviceMetricsOverride",
  { width: 390, height: 820, deviceScaleFactor: 1, mobile: true },
  sessionId,
);

const evaluate = async (expression) => {
  const result = await send(
    "Runtime.evaluate",
    { expression, awaitPromise: true, returnByValue: true },
    sessionId,
  );
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
};
const go = async (url, marker, attempts = 100) => {
  await send("Page.navigate", { url }, sessionId);
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluate(`Boolean(${marker})`).catch(() => false)) return true;
    await pause(250);
  }
  return false;
};
const click = (phrase) =>
  evaluate(`(() => {
    const wanted = ${JSON.stringify(phrase)}.replace(/\\s+/g, ' ').toLowerCase();
    const node = [...document.querySelectorAll('button, a')]
      .find(n => n.innerText.replace(/\\s+/g, ' ').toLowerCase().includes(wanted));
    if (!node) return false;
    node.click();
    return true;
  })()`);
const fill = (selector, value) =>
  evaluate(`(() => {
    const node = [...document.querySelectorAll(${JSON.stringify(selector)})]
      .filter(candidate => candidate.offsetParent !== null)[0];
    if (!node) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(node, ${JSON.stringify(value)});
    node.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);

const notes = [];
const note = (step, value) => notes.push({ step, ...value });

// Nothing is planted: this is a phone that just scanned the code on the screen.
await go(`${APP}/join/${state.code}`, "document.querySelector('h1')");
note("1 scanned the code", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  toldWhichMeeting: await evaluate("/you are joining/i.test(document.body.innerText)"),
  leaks: await evaluate("['undefined','NaN','[object Object]','TypeError'].filter(t => document.body.innerText.includes(t))"),
});

await fill("input:not([type=email]):not([type=password])", "Latecomer");
await fill("input[type=email]", `latecomer.${Date.now()}@kbc.co.ke`);
await fill("input[type=password]", "a-good-password");
await pause(400);
await click("Join and open the meeting");
await pause(4000);

note("2 where they landed", {
  url: await evaluate("location.pathname"),
  inRunMode: await evaluate("location.pathname.endsWith('/run')"),
  stage: await evaluate(
    "(() => { const current = document.querySelector('[aria-current=\"step\"]'); return current ? current.innerText.replace(/\\s+/g,' ').trim() : null; })()",
  ),
  toldToFollowAlong: await evaluate("/Follow along with the facilitator/i.test(document.body.innerText)"),
  canCapture: await evaluate(
    "Boolean([...document.querySelectorAll('button')].find(b => /Capture an idea/i.test(b.innerText)))",
  ),
  hasControls: await evaluate(
    "Boolean([...document.querySelectorAll('button')].find(b => /Next:/i.test(b.innerText)))",
  ),
});

// They can take part from where they arrived.
await click("Capture an idea");
await pause(1200);
await fill("input:not([type=email]):not([type=password])", "I joined late and this is my idea");
await pause(400);
await click("Save idea");
await pause(3000);
note("3 took part immediately", {
  url: await evaluate("location.pathname"),
  ideaSaving: await evaluate("/I joined late/.test(document.body.innerText)"),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-late-report.json", JSON.stringify(notes, null, 2));
socket.close();
