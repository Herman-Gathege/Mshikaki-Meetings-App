/**
 * Two things the addition asked to verify and the other walks do not cover:
 * what a participant sees while a game is running, and the portfolio badge.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-gamesync.json", "utf8"));
const PORTFOLIO = "https://my-portfolio-7v1e.onrender.com/";

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

async function openClient(cookie, { width = 1280, height = 800 } = {}) {
  const { browserContextId } = await send("Target.createBrowserContext");
  const { targetId } = await send("Target.createTarget", { url: "about:blank", browserContextId });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Page.enable", {}, sessionId);
  await send("Runtime.enable", {}, sessionId);
  await send("Network.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 500 }, sessionId);
  await send("Network.setCookie", { name: "mshikaki_session", value: cookie, domain: "172.16.1.36", path: "/" }, sessionId);
  return { sessionId, targetId };
}

const evaluateIn = async (sessionId, expression) => {
  const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }, sessionId);
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
};

const go = async (sessionId, path, marker, attempts = 100) => {
  await send("Page.navigate", { url: `${APP}${path}` }, sessionId);
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluateIn(sessionId, `Boolean(${marker})`).catch(() => false)) return true;
    await pause(250);
  }
  return false;
};

const notes = [];
const note = (step, value) => notes.push({ step, ...value });

// The game stage: the facilitator is on the shared screen, participants are not.
const facilitator = await openClient(state.facilitator);
const participant = await openClient(state.participant, { width: 390, height: 820 });

await go(facilitator.sessionId, `/sessions/${state.session}/run`, "document.body.innerText.includes('Run Mode')");
await pause(1500);
note("1 facilitator on the Play stage", {
  stage: await evaluateIn(facilitator.sessionId, "document.querySelector('[aria-current=\"step\"]')?.innerText.replace(/\\s+/g,' ').trim() ?? null"),
  offeredGameChooser: await evaluateIn(facilitator.sessionId, "/Start the game/.test(document.body.innerText)"),
});

await go(participant.sessionId, `/sessions/${state.session}/run`, "document.body.innerText.includes('Run Mode')");
await pause(1800);
note("2 participant on the Play stage", {
  stage: await evaluateIn(participant.sessionId, "document.querySelector('[aria-current=\"step\"]')?.innerText.replace(/\\s+/g,' ').trim() ?? null"),
  toldWatchTheScreen: await evaluateIn(participant.sessionId, "/running a game|Watch the shared screen/i.test(document.body.innerText)"),
  offeredGameChooser: await evaluateIn(participant.sessionId, "/Start the game/.test(document.body.innerText)"),
  toldToFollowAlong: await evaluateIn(participant.sessionId, "/Follow along with the facilitator/i.test(document.body.innerText)"),
});

// The portfolio badge, on the desktop sidebar.
await go(participant.sessionId, "/", "document.querySelector('h1')");
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false }, participant.sessionId);
await pause(1200);
note("3 the badge on the desktop sidebar", await evaluateIn(participant.sessionId, `(() => {
  const badge = [...document.querySelectorAll('a')].find(a => /My Portfolio/i.test(a.innerText));
  if (!badge) return { found: false };
  const rect = badge.getBoundingClientRect();
  return {
    found: true,
    href: badge.getAttribute('href'),
    target: badge.getAttribute('target'),
    rel: badge.getAttribute('rel'),
    visible: rect.width > 0 && rect.height > 0,
    label: badge.innerText.replace(/\\s+/g, ' ').trim(),
    correctUrl: badge.getAttribute('href') === ${JSON.stringify(PORTFOLIO)},
  };
})()`));

// And on the phone, through the menu.
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 820, deviceScaleFactor: 1, mobile: true }, participant.sessionId);
await pause(1200);
await evaluateIn(participant.sessionId, "[...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Menu')?.click()");
await pause(900);
note("4 the badge on a phone", await evaluateIn(participant.sessionId, `(() => {
  const badge = [...document.querySelectorAll('a')].find(a => /My Portfolio/i.test(a.innerText));
  if (!badge) return { found: false };
  const rect = badge.getBoundingClientRect();
  return { found: true, visible: rect.width > 0 && rect.height > 0, target: badge.getAttribute('target'), rel: badge.getAttribute('rel') };
})()`));

// Clicking it must not take Mshikaki anywhere.
const before = await send("Target.getTargets");
await evaluateIn(participant.sessionId, "[...document.querySelectorAll('a')].find(a => /My Portfolio/i.test(a.innerText)).click()");
await pause(2500);
const after = await send("Target.getTargets");
const pageTargetsBefore = before.targetInfos.filter((t) => t.type === "page").length;
const pageTargetsAfter = after.targetInfos.filter((t) => t.type === "page").length;
note("5 clicking it", {
  openedANewTab: pageTargetsAfter > pageTargetsBefore,
  currentTabUnchanged: (await evaluateIn(participant.sessionId, "location.origin")) === APP,
  currentPath: await evaluateIn(participant.sessionId, "location.pathname"),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-portfolio-report.json", JSON.stringify(notes, null, 2));
socket.close();
