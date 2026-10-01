/**
 * Two real browsers, one meeting: does the room follow the facilitator?

 * The plan is explicit that multi-user synchronisation must not be claimed
 * without being tested. This drives two isolated browser contexts in one Chrome,
 * each with its own session cookie: Herman facilitating, Anne participating.
 */

import fs from "node:fs/promises";

const APP = process.env.APP_URL ?? "http://172.16.1.36:8090";
const state = JSON.parse(await fs.readFile("/tmp/mshikaki-sync.json", "utf8"));

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

/** A browser context with its own cookies, like two people on two devices. */
async function openClient(name, cookie) {
  const { browserContextId } = await send("Target.createBrowserContext");
  const { targetId } = await send("Target.createTarget", {
    url: "about:blank",
    browserContextId,
  });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Page.enable", {}, sessionId);
  await send("Runtime.enable", {}, sessionId);
  await send("Network.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 820,
    deviceScaleFactor: 1,
    mobile: true,
  }, sessionId);
  await send(
    "Network.setCookie",
    { name: "mshikaki_session", value: cookie, domain: "172.16.1.36", path: "/" },
    sessionId,
  );
  return {
    name,
    sessionId,
    evaluate: async (expression) => {
      const result = await send(
        "Runtime.evaluate",
        { expression, awaitPromise: true, returnByValue: true },
        sessionId,
      );
      if (result.exceptionDetails) throw new Error(`${name}: ${result.exceptionDetails.text}`);
      return result.result.value;
    },
    go: async (path, marker) => {
      await send("Page.navigate", { url: `${APP}${path}` }, sessionId);
      for (let attempt = 0; attempt < 100; attempt += 1) {
        if (await base_evaluate(sessionId, `Boolean(${marker})`).catch(() => false)) return true;
        await pause(250);
      }
      return false;
    },
  };
}

async function base_evaluate(sessionId, expression) {
  const result = await send(
    "Runtime.evaluate",
    { expression, awaitPromise: true, returnByValue: true },
    sessionId,
  );
  return result.result.value;
}

async function clickIn(client, phrase) {
  return base_evaluate(
    client.sessionId,
    `(() => {
      const wanted = ${JSON.stringify(phrase)}.replace(/\\s+/g, ' ').toLowerCase();
      const node = [...document.querySelectorAll('button, a')]
        .find(n => n.innerText.replace(/\\s+/g, ' ').toLowerCase().includes(wanted));
      if (!node) return false;
      node.click();
      return true;
    })()`,
  );
}

/** What the current step is, however the client renders it. */
const currentStep = `(() => {
  const current = document.querySelector('[aria-current="step"]');
  return current ? current.innerText.replace(/\\s+/g, ' ').trim() : null;
})()`;

const notes = [];
const note = (step, value) => notes.push({ step, ...value });

const herman = await openClient("facilitator", state.facilitator);
const anne = await openClient("participant", state.participant);
const url = `/sessions/${state.session}`;

// The facilitator runs the meeting.
await herman.go(`${url}/run`, "document.body.innerText.includes('Run Mode')");
await pause(1500);
note("1 the facilitator's screen", {
  stage: await herman.evaluate(currentStep),
  hasControls: await herman.evaluate(
    "Boolean([...document.querySelectorAll('button')].find(b => /Next:/i.test(b.innerText)))",
  ),
});

// The participant opens the meeting from the session page.
await anne.go(url, "document.querySelector('h1')");
await pause(1800);
note("2 the participant's session page", {
  offeredAwayIn: await anne.evaluate(
    "Boolean([...document.querySelectorAll('a,button')].find(n => /Follow the meeting/i.test(n.innerText)))",
  ),
  toldWhoRunsIt: await anne.evaluate("/runs this meeting/.test(document.body.innerText)"),
});
await clickIn(anne, "Follow the meeting");
await pause(2500);
note("3 the participant follows into Run Mode", {
  url: await anne.evaluate("location.pathname"),
  stage: await anne.evaluate(currentStep),
  toldToFollowAlong: await anne.evaluate("/Follow along with the facilitator/i.test(document.body.innerText)"),
  hasNextControl: await anne.evaluate(
    "Boolean([...document.querySelectorAll('button')].find(b => /Next:/i.test(b.innerText)))",
  ),
  hasBackControl: await anne.evaluate(
    "Boolean([...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Back'))",
  ),
});

// The facilitator moves the room.
await clickIn(herman, "What did we decide");
await pause(1500);
note("4 the facilitator moves to Decide", {
  stage: await herman.evaluate(currentStep),
});
await pause(6000);
note("5 the participant after polling", {
  stage: await anne.evaluate(currentStep),
  page: await anne.evaluate(
    "document.body.innerText.includes('facilitator is recording') ? 'decide stage' : 'something else'",
  ),
});

// Move on again, to prove it keeps following.
await clickIn(herman, "Who's got this");
await pause(7000);
note("6 the participant follows again", {
  stage: await anne.evaluate(currentStep),
});

// And the release.
await clickIn(herman, "That's a wrap");
await pause(2000);
await clickIn(herman, "Close the session and write the summary");
await pause(7000);
note("7 after that's a wrap", {
  facilitatorUrl: await herman.evaluate("location.pathname"),
  participantUrl: await anne.evaluate("location.pathname"),
  participantReleased: await anne.evaluate("location.pathname.includes('/run') === false"),
  participantHasNavigation: await anne.evaluate(
    "Boolean([...document.querySelectorAll('nav a')].find(a => /Today/i.test(a.innerText)))",
  ),
});

console.log(JSON.stringify(notes, null, 2));
await fs.writeFile("/tmp/mshikaki-sync-report.json", JSON.stringify(notes, null, 2));
socket.close();
