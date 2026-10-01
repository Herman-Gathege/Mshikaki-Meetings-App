/**
 * The promise the product is named after: an idea becomes work.

 * Walks the idea page on its own, without Run Mode: accept it, record the
 * decision it produced, turn it into a task, and check that the record shows the
 * line back to where it came from. Then the agenda, which the meeting runs on.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-promote.json", "utf8"));

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
  const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function go(path, marker, attempts = 80) {
  await send("Page.navigate", { url: `${APP}${path}` });
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluate(`Boolean(${marker})`).catch(() => false)) return true;
    await pause(200);
  }
  return false;
}

async function click(phrase) {
  return evaluate(`(() => {
    const wanted = ${JSON.stringify(phrase)}.replace(/\\s+/g, ' ').toLowerCase();
    const node = [...document.querySelectorAll('button, a')]
      .find(n => n.innerText.replace(/\\s+/g, ' ').toLowerCase().includes(wanted));
    if (!node) return false;
    node.click();
    return true;
  })()`);
}

/** Types into a visible field, preferring one inside an open dialog. */
async function fill(selector, value) {
  return evaluate(`(() => {
    const dialog = document.querySelector('[role=dialog]');
    const node = [...(dialog ?? document).querySelectorAll(${JSON.stringify(selector)})]
      .filter(candidate => candidate.offsetParent !== null)[0];
    if (!node) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(node, ${JSON.stringify(value)});
    node.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
}

const notes = [];
const note = (step, value) => notes.push({ step, ...value });
const leaks = `['undefined','NaN','[object Object]','Invalid Date','TypeError'].filter(t => document.body.innerText.includes(t))`;

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 820, deviceScaleFactor: 1, mobile: true });
await send("Network.clearBrowserCookies");

await go("/login", "document.querySelector('h1')");
await fill("input[type=email]", state.email);
await fill("input[type=password]", state.password);
await pause(300);
await evaluate(`(() => { [...document.querySelectorAll('button')].filter(b => b.innerText.trim() === 'Sign in').pop()?.click(); })()`);
await pause(3000);

// 1. The idea, as it stands.
await go(`/ideas/${state.idea}`, "document.querySelector('h1')");
await pause(1500);
note("1 the idea page", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  status: await evaluate(
    "[...document.querySelectorAll('span')].map(s => s.innerText).find(t => /^(new|discussing|accepted|parked|rejected|converted)$/.test(t.trim())) ?? null",
  ),
  offers: await evaluate("[...document.querySelectorAll('button')].map(b => b.innerText.trim()).slice(0, 8)"),
  leaks: await evaluate(leaks),
});

// 2. Accept it, the way a team agrees on something.
await click("Mark accepted");
await pause(2200);
note("2 accepted it", {
  status: await evaluate(
    "[...document.querySelectorAll('span')].map(s => s.innerText).find(t => /^(new|discussing|accepted|parked|rejected|converted)$/.test(t.trim())) ?? null",
  ),
  confirmed: await evaluate("[...document.querySelectorAll('p')].map(p => p.innerText).find(t => /Nice one|Accepted|Marked/i.test(t)) ?? null"),
});

// 3. Record the decision it produced.
await click("Record decision");
await pause(900);
await fill("input", "Proceed with automated reminders");
await pause(400);
await click("Save decision");
await pause(2500);
note("3 recorded a decision", {
  status: await evaluate(
    "[...document.querySelectorAll('span')].map(s => s.innerText).find(t => /^(new|discussing|accepted|parked|rejected|converted)$/.test(t.trim())) ?? null",
  ),
  becameA: await evaluate(
    "/became a decision/i.test(document.body.innerText) ? 'decision' : null",
  ),
  decisionOnThePage: await evaluate("/Proceed with automated reminders/.test(document.body.innerText)"),
});

// 4. Turn it into a task, with a different title.
await fill("input[placeholder*='Task title']", "Draft the reminder spec");
await pause(300);
await click("Create task");
await pause(2500);
note("4 created a task from the idea", {
  trailOffers: await evaluate(
    "[...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && (h.startsWith('/tasks/') || h.startsWith('/decisions/') || h.startsWith('/sessions/'))).slice(0, 4)",
  ),
  leaks: await evaluate(leaks),
});

// 5. The agenda, which is what the meeting runs on.
await go(`/sessions/${state.session}`, "/Agenda/.test(document.body.innerText)");
await pause(1200);
await click("Agenda");
await pause(1500);
note("5 the agenda tab", {
  existing: await evaluate(
    "[...document.querySelectorAll('li')].map(li => li.innerText.replace(/\\s+/g,' ').trim()).filter(Boolean).slice(0, 4)",
  ),
  offersAdding: await evaluate("Boolean(document.querySelector('input[placeholder*=\"agenda\" i]'))"),
});
await fill("input[placeholder*='agenda' i]", "Any other business");
await pause(300);
await click("Add");
await pause(2200);
note("6 added an agenda item", {
  listed: await evaluate("/Any other business/.test(document.body.innerText)"),
});
await click("Covered");
await pause(2200);
note("7 marked it covered", {
  covered: await evaluate("/line-through/.test(document.body.innerHTML) || /Covered/.test(document.body.innerText)"),
  leaks: await evaluate(leaks),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-promote-report.json", JSON.stringify(notes, null, 2));
socket.close();
