/**
 * Accessibility and throttled-connection checks against the deployed app,
 * driven through the Chrome DevTools Protocol.
 *
 * Evidence for Phase 6F (accessibility, real-room usability) and 6G (performance
 * on a bad connection).
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const CDP = process.env.CDP_ENDPOINT;
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-ux.json", "utf8"));

const socket = new WebSocket(CDP);
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

async function viewport(width, height) {
  await send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 500,
  });
}

async function goto(path, { waitFor } = {}) {
  const started = Date.now();
  await send("Page.navigate", { url: `${APP}${path}` });
  const marker = waitFor ?? "document.querySelector('main, h1')";
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const ready = await evaluate(`Boolean(${marker})`).catch(() => false);
    if (ready) break;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return Date.now() - started;
}

// Checks that run inside the page.
const TARGET_SIZE_CHECK = `(() => {
  const tooSmall = [];
  for (const node of document.querySelectorAll('button, a, [role="button"], input, select, textarea')) {
    const rect = node.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    if (rect.height < 44) tooSmall.push({ label: (node.innerText || node.getAttribute('aria-label') || node.tagName).trim().slice(0, 40), height: Math.round(rect.height) });
  }
  return tooSmall;
})()`;

const UNLABELLED_CHECK = `(() => {
  const nameless = [];
  for (const node of document.querySelectorAll('button, a[href], [role="button"]')) {
    const text = (node.innerText || '').trim();
    const aria = node.getAttribute('aria-label') || node.getAttribute('title');
    const imgAlt = node.querySelector('img[alt]:not([alt=""])');
    const svgTitle = node.querySelector('svg > title');
    if (!text && !aria && !imgAlt && !svgTitle) nameless.push(node.outerHTML.slice(0, 90));
  }
  return nameless;
})()`;

const HEADING_CHECK = `(() => {
  const headings = [...document.querySelectorAll('h1, h2, h3')].map(h => h.tagName + ': ' + h.innerText.trim().slice(0, 48));
  return { h1Count: document.querySelectorAll('h1').length, headings };
})()`;

const FOCUS_CHECK = `(() => {
  const input = document.querySelector('input, button, a[href]');
  if (!input) return null;
  input.focus();
  const style = getComputedStyle(input);
  return { tag: input.tagName, outlineWidth: style.outlineWidth, outlineStyle: style.outlineStyle, outlineColor: style.outlineColor };
})()`;

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");

// Sign in by planting the session cookie the API gave us.
await send("Network.setCookie", {
  name: "mshikaki_session",
  value: state.cookie,
  domain: "172.16.1.36",
  path: "/",
});

const report = {};

// 1. Phone size: Today
await viewport(360, 640);
report.today_phone_ms = await goto("/", { waitFor: "document.body.innerText.includes('Today')" });
report.today_targets_too_small = await evaluate(TARGET_SIZE_CHECK);
report.today_unlabelled_controls = await evaluate(UNLABELLED_CHECK);
report.today_headings = await evaluate(HEADING_CHECK);
report.focus_ring = await evaluate(FOCUS_CHECK);

// 2. Projector size: Run Mode
await viewport(1280, 720);
report.run_mode_ms = await goto(`/sessions/${state.session}/run`, {
  waitFor: "document.body.innerText.includes('play')",
});
report.run_mode_targets_too_small = await evaluate(TARGET_SIZE_CHECK);
report.run_mode_heading = await evaluate("document.querySelector('h1')?.innerText ?? null");
report.run_mode_steps = await evaluate(
  "[...document.querySelectorAll('nav button')].map(b => b.innerText.trim())",
);

// 3. Projector size: the game screen
report.game_ms = await goto(`/play/${state.play}`, {
  waitFor: "document.body.innerText.includes('Question')",
});
report.game_question = await evaluate("document.querySelector('h1')?.innerText ?? null");
report.game_progress = await evaluate(
  "[...document.querySelectorAll('span')].map(s => s.innerText).find(t => /Question \\d+ of \\d+/.test(t)) ?? null",
);
report.game_options = await evaluate(
  "[...document.querySelectorAll('ul[aria-label=\"Answer options\"] button')].map(b => b.innerText.trim())",
);
report.game_timer_present = await evaluate("Boolean(document.querySelector('[role=\"timer\"]'))");
report.game_option_targets_too_small = await evaluate(TARGET_SIZE_CHECK);

// 4. A bad connection: slow 3G, then reload the game screen.
await send("Network.emulateNetworkConditions", {
  offline: false,
  latency: 400,
  downloadThroughput: (400 * 1024) / 8,
  uploadThroughput: (400 * 1024) / 8,
});
report.game_ms_slow_3g = await goto(`/play/${state.play}`, {
  waitFor: "document.body.innerText.includes('Question')",
});
await viewport(1280, 720);
report.run_mode_ms_slow_3g = await goto(`/sessions/${state.session}/run`, {
  waitFor: "document.body.innerText.includes('play')",
});
await viewport(360, 640);
report.today_ms_slow_3g = await goto("/", { waitFor: "document.body.innerText.includes('Today')" });
await send("Network.emulateNetworkConditions", {
  offline: false,
  latency: 0,
  downloadThroughput: -1,
  uploadThroughput: -1,
});

await fs.writeFile("/tmp/mshikaki-ux-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
socket.close();
