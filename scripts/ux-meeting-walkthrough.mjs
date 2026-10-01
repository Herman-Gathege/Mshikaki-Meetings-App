/**
 * The acceptance walk in a browser: what a person does after the meeting.

 * Covers the Phase 6 acceptance steps that the game-flow script does not:
 * a finished meeting appearing on Today, the record reading back from a task to
 * the meeting that created it, and the last question leading to results.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-acc.json", "utf8"));

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

async function go(path, marker) {
  await send("Page.navigate", { url: `${APP}${path}` });
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (await evaluate(`Boolean(${marker})`).catch(() => false)) return true;
    await pause(200);
  }
  throw new Error(`timed out loading ${path}`);
}

const results = [];
const record = (name, value) => results.push({ step: name, ...value });

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
  width: 390,
  height: 780,
  deviceScaleFactor: 1,
  mobile: true,
});

// S. A closed meeting is visible on Today, under what the last session produced.
await go("/", "document.querySelector('h1')");
record("Today after closing", {
  fromLastSession: await evaluate(`
    (() => {
      const text = document.body.innerText;
      const start = text.indexOf('FROM THE LAST SESSION');
      return start === -1 ? null : text.slice(start, start + 120).split('\\n').filter(Boolean).slice(0, 3);
    })()
  `),
});

// T. Why does this task exist: task -> decision -> idea -> session.
await go(`/tasks/${state.task}`, "document.body.innerText.includes('Why does this exist')");
record("Task page trail", {
  trail: await evaluate(`
    (() => {
      const heading = [...document.querySelectorAll('h2')].find(h => h.innerText.includes('Why does this exist'));
      if (!heading) return null;
      const card = heading.closest('section, article, div');
      return [...card.querySelectorAll('a')].map(a => a.innerText.trim() + ' -> ' + a.getAttribute('href'));
    })()
  `),
  origins: await evaluate(
    "[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && (h.startsWith('/decisions/') || h.startsWith('/sessions/') || h.startsWith('/ideas/')))",
  ),
});

// Follow the trail to the decision, then to the idea it came from.
await go(`/decisions/${state.decision}`, "document.querySelector('h1')");
record("Decision page", {
  statement: await evaluate("document.querySelector('section p, main p')?.innerText ?? null"),
  linksBack: await evaluate(
    "[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && (h.startsWith('/ideas/') || h.startsWith('/sessions/')))",
  ),
});
await go(`/ideas/${state.idea}`, "document.querySelector('h1')");
record("Idea page", {
  title: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  status: await evaluate("[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>['converted','accepted'].includes(t)) ?? null"),
  linksBack: await evaluate(
    "[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && h.startsWith('/sessions/'))",
  ),
});

// Q/R. The frozen record and its download.
await go(`/sessions/${state.done}`, "document.body.innerText.includes('Summary')");
await evaluate(
  "[...document.querySelectorAll('nav button, button')].find(b => b.innerText.trim() === 'Summary')?.click()",
);
await pause(900);
record("Minutes", {
  downloadHref: await evaluate(
    "[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).find(h => h && h.includes('minutes.html')) ?? null",
  ),
  whatsappButton: await evaluate("Boolean([...document.querySelectorAll('button')].find(b => b.innerText.includes('WhatsApp')))"),
  summaryShown: await evaluate("document.body.innerText.includes('Decisions (1)') || document.body.innerText.includes('*Decisions*') || document.body.innerText.includes('Decisions')"),
});

// J. Playing through to the last question offers results, not another next.
await go(`/play/${state.play}`, "document.body.innerText.includes('Question')");
for (let index = 0; index < state.total; index += 1) {
  const label = await evaluate(
    "[...document.querySelectorAll('button')].map(b => b.innerText.trim()).find(t => t.includes('Next question') || t.includes('See results'))",
  );
  if (!label) break;
  if (label.includes("See results")) break;
  await evaluate(
    "[...document.querySelectorAll('button')].find(b => b.innerText.includes('Next question'))?.click()",
  );
  await pause(220);
}
record("Last question", {
  progress: await evaluate(
    "[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/Question \\d+ of \\d+/.test(t)) ?? null",
  ),
  offer: await evaluate(
    "[...document.querySelectorAll('button')].map(b => b.innerText.trim()).find(t => t.includes('See results')) ?? null",
  ),
});

console.log(JSON.stringify(results, null, 2));
await fs.writeFile("/tmp/mshikaki-acc-report.json", JSON.stringify(results, null, 2));
socket.close();
