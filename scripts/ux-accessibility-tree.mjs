/**
 * What a screen reader is given: roles, names and structure.

 * Run this after a change that adds controls, headings or a dialog. It is a
 * structural check, not a substitute for listening to a real screen reader.
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
  return result.result.value;
}
async function goto(path, marker) {
  await send("Page.navigate", { url: `${APP}${path}` });
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const ready = await evaluate(`Boolean(${marker})`).catch(() => false);
    if (ready) return;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
}

/** Reads the accessibility tree and returns the parts worth asserting on. */
async function inspect() {
  const tree = await send("Accessibility.getFullAXTree");
  const nodes = tree.nodes.filter((node) => !node.ignored);
  const named = (role) =>
    nodes
      .filter((node) => node.role?.value === role)
      .map((node) => (node.name?.value ?? "").trim());
  const buttons = named("button");
  return {
    landmarks: nodes
      .filter((node) => ["main", "navigation", "banner", "dialog"].includes(node.role?.value))
      .map((node) => `${node.role.value}: ${(node.name?.value ?? "").trim() || "(no name)"}`),
    headings: nodes
      .filter((node) => node.role?.value === "heading")
      .map((node) => `h${node.properties?.find((p) => p.name === "level")?.value?.value ?? "?"}: ${(node.name?.value ?? "").trim().slice(0, 40)}`),
    buttonsWithoutNames: buttons.filter((name) => !name).length,
    buttonNames: buttons.filter(Boolean).slice(0, 12),
    linksWithoutNames: nodes
      .filter((node) => node.role?.value === "link")
      .filter((node) => !(node.name?.value ?? "").trim()).length,
    dialogs: named("dialog"),
  };
}

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");
await send("Accessibility.enable");
await send("Network.setCookie", {
  name: "mshikaki_session",
  value: state.cookie,
  domain: "172.16.1.36",
  path: "/",
});
await send("Emulation.setDeviceMetricsOverride", {
  width: 360,
  height: 640,
  deviceScaleFactor: 1,
  mobile: true,
});

const report = {};

await goto("/", "document.querySelector('h1')");
report.today = await inspect();

// The quick-capture sheet must announce itself as a dialog with a name.
await evaluate(
  "[...document.querySelectorAll('button')].find(b => b.innerText.includes('Idea'))?.click()",
);
await new Promise((resolve) => setTimeout(resolve, 800));
report.capture_sheet = await inspect();

await goto(`/play/${state.play}`, "document.body.innerText.includes('Question')");
report.game = await inspect();

console.log(JSON.stringify(report, null, 2));
await fs.writeFile("/tmp/mshikaki-a11y-tree.json", JSON.stringify(report, null, 2));
socket.close();
