/**
 * The paths a returning user takes: signing in, producing the QR that everybody
 * else scans, and reading the record afterwards.

 * The other walks plant a cookie to skip the front door and use an invite code
 * made through the API. This one uses the screens.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-returning.json", "utf8"));

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
  return evaluate(`(() => {
    const node = document.querySelector(${JSON.stringify(selector)});
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

// 1. A returning user opens the app and signs in with the form.
await go("/", "document.querySelector('h1')");
note("1 opening the app signed out", {
  url: await evaluate("location.pathname"),
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  offersSignIn: await evaluate("/sign in/i.test(document.body.innerText)"),
});
await fill("input[type=email]", state.email);
await fill("input[type=password]", state.password);
await pause(300);
// The page has a mode tab and a submit button, both reading "Sign in". The submit
// is the last one, and the one that fills the width.
await evaluate(`(() => {
  const submit = [...document.querySelectorAll('button')]
    .filter(b => b.innerText.trim() === 'Sign in')
    .pop();
  if (!submit) return false;
  submit.click();
  return true;
})()`);
await pause(3000);
note("2 after signing in", {
  url: await evaluate("location.pathname"),
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  leaks: await evaluate(leaks),
});

// 2. The facilitator produces the code everybody else scans.
await go("/team", "/Create code/i.test(document.body.innerText)");
note("3 the team page", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  offersAnInvite: await evaluate("Boolean([...document.querySelectorAll('button')].find(b => /Create code/i.test(b.innerText)))"),
  membersListed: await evaluate("document.querySelectorAll('li').length"),
});
await click("Create code");
await pause(2500);
note("4 created an invite", {
  showsCode: await evaluate("/[A-Z0-9]{8,}/.test(document.body.innerText)"),
  qrDrawn: await evaluate("document.querySelectorAll('svg').length"),
  joinLinkShown: await evaluate("/\\/join\\//.test(document.body.innerText)"),
  offersBigView: await evaluate("Boolean([...document.querySelectorAll('button')].find(b => /Show big/i.test(b.innerText)))"),
});

// 3. The projector view: open it, check it is readable and closable.
await click("Show big");
await pause(1200);
note("5 the projector QR", {
  dialogOpen: await evaluate("Boolean(document.querySelector('[role=dialog]'))"),
  saysScan: await evaluate("/Scan to join/i.test(document.body.innerText)"),
  qrIsLarge: await evaluate(`(() => {
    const svg = document.querySelector('[role=dialog] svg');
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    return Math.round(Math.min(rect.width, rect.height));
  })()`),
  closeOffered: await evaluate("Boolean([...document.querySelectorAll('button')].find(b => /Close/i.test(b.innerText)))"),
});
await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
await pause(800);
note("6 escaped the projector view", {
  dialogClosed: await evaluate("!document.querySelector('[role=dialog]')"),
  backOnTheTeamPage: await evaluate("location.pathname === '/team'"),
});

// 4. The record afterwards: bragging rights and the trail.
await go("/leaderboard", "document.querySelector('h1')");
await pause(1500);
note("7 the leaderboard", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  standings: await evaluate(
    "[...document.querySelectorAll('li')].map(li => li.innerText.replace(/\\s+/g, ' ').trim()).filter(Boolean).slice(0, 3)",
  ),
  disclaimer: await evaluate("/not a performance measure|for fun/i.test(document.body.innerText)"),
  leaks: await evaluate(leaks),
});

await go("/activity", "document.querySelector('h1')");
await pause(1800);
note("8 the activity trail", {
  heading: await evaluate("document.querySelector('h1')?.innerText ?? null"),
  entries: await evaluate(
    "[...document.querySelectorAll('ol li')].map(li => li.innerText.replace(/\\s+/g, ' ').trim()).filter(Boolean).slice(0, 3)",
  ),
  readable: await evaluate("/created|moved|recorded|completed|joined/i.test(document.body.innerText)"),
  leaks: await evaluate(leaks),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-returning-report.json", JSON.stringify(notes, null, 2));
socket.close();
