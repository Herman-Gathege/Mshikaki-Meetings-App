/**
 * The work layer through the screens: advancing a task, blocking and unblocking,
 * projects, capturing an idea from wherever you are, and searching for it.

 * These paths have API tests. This walk exists because the API answering
 * correctly and the screen offering the right thing are different claims.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-work.json", "utf8"));

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

async function go(path, marker, attempts = 80) {
  await send("Page.navigate", { url: `${APP}${path}` });
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluate(`Boolean(${marker})`).catch(() => false)) return true;
    await pause(200);
  }
  return false;
}

/** Clicks the first control whose text contains the phrase, whitespace collapsed. */
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

async function fill(selector, value) {
  // Prefer a field inside an open dialog, and never a hidden one: the header
  // search box sits in the DOM on narrow screens while being invisible.
  return evaluate(`(() => {
    const dialog = document.querySelector('[role=dialog]');
    const scope = dialog ?? document;
    const node = [...scope.querySelectorAll(${JSON.stringify(selector)})]
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
await send("Emulation.setDeviceMetricsOverride", {
  width: 390,
  height: 820,
  deviceScaleFactor: 1,
  mobile: true,
});
await send("Network.clearBrowserCookies");

// Sign in the way a returning user does.
await go("/login", "document.querySelector('h1')");
await fill("input[type=email]", state.email);
await fill("input[type=password]", state.password);
await pause(300);
await evaluate(`(() => {
  [...document.querySelectorAll('button')].filter(b => b.innerText.trim() === 'Sign in').pop()?.click();
})()`);
await pause(3000);

// 1. My work: is the task there, and can a waiting one be advanced?
await go("/work", "document.querySelector('h1')");
await pause(1500);
note("1 work page", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  tabs: await evaluate(
    "[...document.querySelectorAll('nav button, button')].map(b => b.innerText.trim()).filter(t => /my work|all tasks|board/i.test(t))",
  ),
  myTasks: await evaluate(
    "[...document.querySelectorAll('li')].map(li => li.innerText.replace(/\\s+/g,' ').trim()).filter(t => /compliance|venue/i.test(t)).slice(0, 3)",
  ),
  leaks: await evaluate(leaks),
});
// Advance the backlog task, not the one we are about to block.
await evaluate(`(() => {
  const row = [...document.querySelectorAll('li')].find(li => /Book the venue/.test(li.innerText));
  const button = row && [...row.querySelectorAll('button')].find(b => /Advance/.test(b.innerText));
  button?.click();
})()`);
await pause(2000);
note("2 advanced a task", {
  toast: await evaluate("[...document.querySelectorAll('p')].map(p => p.innerText).find(t => /Done|progress/i.test(t)) ?? null"),
  statusNow: await evaluate(
    "[...document.querySelectorAll('span')].map(s => s.innerText).find(t => /done|in progress|blocked|backlog/i.test(t)) ?? null",
  ),
});

// 2. Blocking and unblocking, on the task page.
await go(`/tasks/${state.task}`, "document.querySelector('h1')");
await pause(1500);
note("3 task page", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  showsOwner: await evaluate("/Herman/.test(document.body.innerText)"),
  showsOrigin: await evaluate("/Why does this exist/i.test(document.body.innerText)"),
  offersBlocking: await evaluate("Boolean(document.querySelector('input[placeholder*=\"stopping\"]'))"),
});
await fill("input[placeholder*='stopping']", "Waiting on the finance figures");
await pause(300);
await click("Mark blocked");
await pause(2200);
note("4 blocked it", {
  statusNow: await evaluate(
    "[...document.querySelectorAll('span')].map(s => s.innerText).find(t => /blocked|in progress|done/i.test(t)) ?? null",
  ),
  reasonShown: await evaluate("/Waiting on the finance figures/.test(document.body.innerText)"),
});

await go("/work", "document.querySelector('h1')");
await pause(2000);
note("5 the blockers section", {
  listed: await evaluate("/Waiting on the finance figures/.test(document.body.innerText)"),
  offersResolve: await evaluate("Boolean([...document.querySelectorAll('button')].find(b => /Resolve/i.test(b.innerText)))"),
});
await click("Resolve");
await pause(800);
await evaluate(`(() => {
  const field = [...document.querySelectorAll('input')].find(i => /cleared|what/i.test(i.placeholder || ''));
  if (!field) return false;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(field, 'Finance sent the figures');
  field.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`);
await pause(400);
await evaluate(`(() => {
  const button = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Resolve');
  button?.click();
})()`);
await pause(2200);
note("6 resolved the blocker", {
  gone: await evaluate("!/Waiting on the finance figures/.test(document.body.innerText)"),
  smoothSailing: await evaluate("/Smooth sailing/i.test(document.body.innerText)"),
});

// 3. A project, with a task inside it.
await go("/work", "/Projects/i.test(document.body.innerText)");
await pause(1200);
await click("New project");
await pause(800);
await fill("input", "Studio upgrade");
await pause(300);
await evaluate(`(() => {
  const button = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Create');
  button?.click();
})()`);
await pause(2500);
note("7 created a project", {
  listed: await evaluate("/Studio upgrade/.test(document.body.innerText)"),
  leaks: await evaluate(leaks),
});

// 4. Capture an idea from a normal page, and find it with search.
await click("Planning");
await pause(600);
await evaluate("window.history.back()");
await pause(1500);
await go("/work", "document.querySelector('h1')");
await pause(1000);
await click("+ Idea");
await pause(900);
note("8 capture from anywhere", {
  sheetOpen: await evaluate("/Capture an idea/i.test(document.body.innerText)"),
  fields: await evaluate("[...document.querySelectorAll('input, textarea')].map(n => n.placeholder || n.type).slice(0, 3)"),
});
await fill("input[type=text], input:not([type])", "Rotate the standby presenter");
await pause(300);
await click("Save idea");
await pause(2500);
note("9 saved it", {
  url: await evaluate("location.pathname"),
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
});

await go("/search", "document.querySelector('h1')");
await pause(1000);
await fill("input", "Rotate the standby");
await pause(2500);
note("10 search", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  found: await evaluate("/Rotate the standby presenter/i.test(document.body.innerText)"),
  leaks: await evaluate(leaks),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-work-report.json", JSON.stringify(notes, null, 2));
socket.close();
