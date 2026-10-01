/**
 * Second accessibility pass: real keyboard focus, and contrast measured from the
 * colours the browser actually paints.
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

const CONTRAST_HELPERS = `
  const canvas = document.createElement('canvas');
  canvas.width = 1; canvas.height = 1;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  function rgba(color) {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, 1, 1);
    return [...ctx.getImageData(0, 0, 1, 1).data].slice(0, 4);
  }
  function over([r, g, b, a], base) {
    const alpha = (a ?? 255) / 255;
    return [
      r * alpha + base[0] * (1 - alpha),
      g * alpha + base[1] * (1 - alpha),
      b * alpha + base[2] * (1 - alpha),
    ];
  }
  function toRgb(color) {
    const [r, g, b] = rgba(color);
    return [r, g, b];
  }
  function luminance([r, g, b]) {
    const channel = (value) => {
      const v = value / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  }
  function backdrop(node) {
    // Composite every ancestor background, root first, so translucent cards
    // (bg-white/5 over a dark screen) are measured as the browser paints them.
    const chain = [];
    let current = node;
    while (current) {
      chain.unshift(current);
      current = current.parentElement;
    }
    let base = [255, 255, 255];
    for (const element of chain) {
      const background = getComputedStyle(element).backgroundColor;
      if (!background || background.includes('rgba(0, 0, 0, 0)')) continue;
      base = over(rgba(background), base);
    }
    return base;
  }
  function ratio(node) {
    if (!node) return null;
    const style = getComputedStyle(node);
    const colour = toRgb(style.color);
    const behind = backdrop(node);
    const lighter = Math.max(luminance(colour), luminance(behind));
    const darker = Math.min(luminance(colour), luminance(behind));
    const size = parseFloat(style.fontSize);
    return {
      text: node.innerText.trim().slice(0, 34),
      ratio: Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100,
      fontSize: size,
      bold: Number(style.fontWeight) >= 600,
      large: size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 600),
    };
  }
`;

const CONTRAST_SAMPLES = `(() => {
  ${CONTRAST_HELPERS}
  const samples = [];
  const push = (label, node) => { const result = ratio(node); if (result) samples.push({ label, ...result }); };
  push('h1', document.querySelector('h1'));
  push('section label', document.querySelector('h2'));
  push('body text', document.querySelector('p'));
  push('primary button', document.querySelector('a button, button'));
  push('status badge', [...document.querySelectorAll('span.rounded-full')].find(s => /^(planned|active|completed|in progress|done|new|backlog)$/i.test(s.innerText.trim())));
  push('muted meta', [...document.querySelectorAll('p')].find(p => getComputedStyle(p).fontSize === '12px'));
  return samples.map(s => ({ ...s, passes: s.ratio >= (s.large ? 3 : 4.5) }));
})()`;

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");
await send("Network.setCookie", {
  name: "mshikaki_session",
  value: state.cookie,
  domain: "172.16.1.36",
  path: "/",
});

async function goto(path, marker) {
  await send("Page.navigate", { url: `${APP}${path}` });
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const ready = await evaluate(`Boolean(${marker})`).catch(() => false);
    if (ready) return true;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  return false;
}

const report = {};

// Keyboard focus on the phone-sized Today screen.
await send("Emulation.setDeviceMetricsOverride", {
  width: 360,
  height: 640,
  deviceScaleFactor: 1,
  mobile: true,
});
await goto("/", "document.querySelector('h1')");
await evaluate("document.body.focus()");

const focusTrail = [];
for (let step = 0; step < 14; step += 1) {
  await send("Input.dispatchKeyEvent", { type: "rawKeyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9 });
  const focused = await evaluate(`(() => {
    const node = document.activeElement;
    if (!node || node === document.body) return null;
    const style = getComputedStyle(node);
    return {
      tag: node.tagName,
      label: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 30),
      outline: style.outlineStyle,
      width: style.outlineWidth,
    };
  })()`);
  if (focused) focusTrail.push(focused);
}
report.keyboard_focus_trail = focusTrail;
report.focus_visible_count = focusTrail.filter((entry) => entry.outline === "solid").length;
report.contrast_phone_today = await evaluate(CONTRAST_SAMPLES);

// Contrast on the projector screens.
await send("Emulation.setDeviceMetricsOverride", {
  width: 1280,
  height: 720,
  deviceScaleFactor: 1,
  mobile: false,
});
await goto(`/sessions/${state.session}/run`, "document.querySelector('h1')");
report.contrast_projector_run_mode = await evaluate(CONTRAST_SAMPLES);

await goto(`/play/${state.play}`, "document.body.innerText.includes('Question')");
report.contrast_game_screen = await evaluate(`(() => {
  ${CONTRAST_HELPERS}
  const samples = [];
  const push = (label, node) => { const result = ratio(node); if (result) samples.push({ label, ...result }); };
  push('game title', document.querySelector('h1'));
  push('question', document.querySelector('p.text-2xl, p.text-4xl'));
  push('answer option', document.querySelector('ul[aria-label="Answer options"] button'));
  push('timer', document.querySelector('[role="timer"]'));
  return samples.map(s => ({ ...s, passes: s.ratio >= (s.large ? 3 : 4.5) }));
})()`);
report.game_answer_target_heights = await evaluate(
  "[...document.querySelectorAll('ul[aria-label=\"Answer options\"] button')].map(b => Math.round(b.getBoundingClientRect().height))",
);

console.log(JSON.stringify(report, null, 2));
await fs.writeFile("/tmp/mshikaki-ux-report2.json", JSON.stringify(report, null, 2));
socket.close();
