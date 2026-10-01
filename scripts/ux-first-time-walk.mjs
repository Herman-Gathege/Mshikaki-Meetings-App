/**
 * A first-time-user rehearsal, run by proxy.

 * The plan asks for a person who has never used Mshikaki to be told "run a
 * meeting" and observed. This script does what a machine can do of that: a clean
 * browser with no cookie, walking the whole journey the way a newcomer would,
 * recording what is visible on each screen and flagging anything that makes them
 * guess.

 * It cannot tell you whether the room enjoyed it. It can tell you whether the
 * words are there.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-firsttime.json", "utf8"));

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

/** What a person can see: the heading, the buttons, and anything that leaks. */
async function screen() {
  return evaluate(`(() => {
    const text = document.body.innerText;
    return {
      heading: document.querySelector('h1')?.innerText ?? null,
      firstLine: text.split('\\n').map(l => l.trim()).filter(Boolean).slice(0, 3),
      buttons: [...document.querySelectorAll('button, a')]
        .map(node => node.innerText.trim())
        .filter(t => t && t.length < 40)
        .slice(0, 14),
      fields: [...document.querySelectorAll('input, select, textarea')]
        .map(node => node.getAttribute('aria-label') || node.previousElementSibling?.innerText || node.placeholder || node.type)
        .slice(0, 8),
      leaks: ['undefined', 'NaN', '[object Object]', 'Invalid Date', 'TypeError', 'Unprocessable', '422 ', '500 ', 'null']
        .filter(token => text.includes(token)),
    };
  })()`);
}

async function click(phrase) {
  // Phone-width labels wrap, so "Who's got this" arrives as "Who's got\nthis".
  // Compare on collapsed whitespace the way a person reads it.
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
  return evaluate(`(() => {
    const node = document.querySelector(${JSON.stringify(selector)});
    if (!node) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(node, ${JSON.stringify(value)});
    node.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
}

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: 390,
  height: 820,
  deviceScaleFactor: 1,
  mobile: true,
});
// No cookie is planted: this is a newcomer with a link.
await send("Network.clearBrowserCookies");

const notes = [];
const note = (step, value) => {
  notes.push({ step, ...value });
};

// 1. Somebody scans the code on the projector.
await go(`/join/${state.code}`, "document.querySelector('h1')");
note("1 scanned the code", await screen());

// 2. They give a name, a work email and a password, and join.
await fill("input[type=text], input:not([type])", "Anne");
// A newcomer each run: the same address twice would be an existing account.
const newcomer = `anne.${Date.now()}@kbc.co.ke`;
await fill("input[type=email]", newcomer);
await fill("input[type=password]", "a-good-password");
await pause(300);
note("2 filled the form", {
  readyToJoin: await evaluate(
    "!document.querySelector('button:not([disabled])')?.innerText?.includes('Joining')",
  ),
  button: await evaluate(
    "[...document.querySelectorAll('button')].map(b => b.innerText.trim()).find(t => t.includes('Join')) ?? null",
  ),
});
await click("Join");
await pause(2500);
note("3 after joining", await screen());

// 3. They are in the meeting. Can they see how to start it?
note("4 the meeting page", {
  url: await evaluate("location.pathname"),
  canStart: await evaluate("Boolean([...document.querySelectorAll('button')].find(b => /Start/i.test(b.innerText)))"),
  visibleToThem: await evaluate("document.body.innerText.includes('Herman') || document.body.innerText.includes('Anne')"),
});
await click("Start");
await pause(2500);
note("5 pressed start", await screen());

// 4. Run Mode. Pressing start should have taken them here.
note("6 run mode", {
  url: await evaluate("location.pathname"),
  steps: await evaluate("[...document.querySelectorAll('nav button')].map(b => b.innerText.trim())"),
  heading: await evaluate("document.querySelector('h2')?.innerText ?? null"),
  gamesOffered: await evaluate("document.querySelectorAll('select option').length"),
  nextAction: await evaluate(
    "[...document.querySelectorAll('button')].map(b => b.innerText.trim()).find(t => /Next:/i.test(t)) ?? null",
  ),
});

// 5. Capture an idea, from the capture step, the way the room does.
await click("What are we thinking");
await pause(1000);
await click("Capture an idea");
await pause(900);
note("7 capture sheet opened", {
  heading: await evaluate("document.querySelector('h2')?.innerText ?? null"),
  fields: await evaluate(
    "[...document.querySelectorAll('input, textarea')].map(n => n.placeholder || n.type)",
  ),
});
await fill("input[type=text], input:not([type])", "Automate the radio schedule reminders");
await pause(300);
await click("Save idea");
await pause(2500);
note("8 captured an idea", {
  url: await evaluate("location.pathname"),
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
});

// 6. Back into the meeting, then decide, assign and close.
await go(`/sessions/${state.session}/run`, "document.body.innerText.includes('play')");
await click("What did we decide");
await pause(1200);
note("9 decide step", {
  heading: await evaluate("document.querySelector('h2')?.innerText ?? null"),
  offers: await evaluate(
    "[...document.querySelectorAll('button')].map(b => b.innerText.trim()).slice(0, 6)",
  ),
});
await click("Record decision");
await pause(900);
await click("Save decision");
await pause(2000);
note("10 recorded a decision", {
  decided: await evaluate("document.body.innerText.includes('Recorded') || document.body.innerText.includes('decision')"),
});

await click("Who's got this");
await pause(1200);
note("11 assign step", {
  heading: await evaluate("document.querySelector('h2')?.innerText ?? null"),
  fields: await evaluate(
    "[...document.querySelectorAll('input, select')].map(n => n.previousElementSibling?.innerText || n.placeholder || n.type).slice(0, 5)",
  ),
} );
await fill("input[type=text], input:not([type])", "Draft the reminder spec");
await pause(300);
note("11b owner picker", {
  present: await evaluate("document.querySelectorAll('select').length"),
});
await evaluate(`(() => {
  const select = document.querySelector('select');
  if (!select) return false;
  const option = [...select.options].find(o => o.value);
  if (!option) return false;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
  setter.call(select, option.value);
  select.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
})()`);
await pause(300);
await click("Assign it");
await pause(2200);
note("12 assigned a task", {
  assigned: await evaluate("document.body.innerText.includes('Draft the reminder spec')"),
});

await click("That's a wrap");
await pause(1200);
note("13 close step", {
  heading: await evaluate("document.querySelector('h2')?.innerText ?? null"),
  offers: await evaluate(
    "[...document.querySelectorAll('button')].map(b => b.innerText.trim()).slice(0, 5)",
  ),
});
await click("Close the session");
await pause(3000);
note("14 closed the meeting", {
  closed: await evaluate("document.body.innerText.includes('That\\'s a wrap') || document.body.innerText.includes('summary')"),
});

// 7. Back on the session page: can they find the minutes?
await go(`/sessions/${state.session}`, "document.body.innerText.includes('Summary')");
await click("Summary");
await pause(1500);
note("15 minutes", {
  downloadOffered: await evaluate(
    "[...document.querySelectorAll('a')].some(a => (a.getAttribute('href') || '').includes('minutes.html'))",
  ),
  whatsappOffered: await evaluate(
    "[...document.querySelectorAll('button')].some(b => b.innerText.includes('WhatsApp'))",
  ),
  summaryReadable: await evaluate("document.body.innerText.length > 200"),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-firsttime-report.json", JSON.stringify(notes, null, 2));
socket.close();
