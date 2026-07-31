// The device-authorisation grant. This is a credential path, so the tests are about what MUST NOT
// happen as much as what must: a code cannot mint an entitlement, an unauthenticated browser cannot
// approve, and a device code yields the key exactly once.
//
//   node functions/api/device.test.mjs
import assert from "node:assert";
import { onRequest } from "./device.js";

let pass = 0, fail = 0;
const ok = (name, fn) => {
  try { fn(); console.log("  ok   " + name); pass++; }
  catch (e) { console.log("  FAIL " + name + "\n       " + e.message); fail++; }
};
const okAsync = async (name, fn) => {
  try { await fn(); console.log("  ok   " + name); pass++; }
  catch (e) { console.log("  FAIL " + name + "\n       " + e.message); fail++; }
};

// ---- a KV double that behaves like the real one where it matters (string values, TTL ignored) ----
function kv() {
  const m = new Map();
  return {
    m,
    async get(k) { return m.has(k) ? m.get(k) : null; },
    async put(k, v) { m.set(k, String(v)); },
    async delete(k) { m.delete(k); },
  };
}

const REQ = (method, body, { cookie = null, query = "" } = {}) =>
  new Request("https://tashan.sh/api/device" + query, {
    method,
    headers: Object.assign({ "content-type": "application/json" }, cookie ? { cookie } : {}),
    body: method === "POST" ? JSON.stringify(body || {}) : undefined,
  });

const call = async (env, method, body, opts) => {
  const r = await onRequest({ request: REQ(method, body, opts), env });
  return { status: r.status, body: await r.json() };
};

// fetchLicence lives in _license.js and talks to Polar. The grant must not care HOW a licence is
// validated, only that it is — so the network is stubbed at the global level.
function withPolar(valid) {
  globalThis.fetch = async () =>
    new Response(JSON.stringify(valid ? { status: "granted", customer: { email: "a@b.c" } } : { detail: "nope" }),
      { status: valid ? 200 : 404, headers: { "content-type": "application/json" } });
}

console.log("\n── device grant ───────────────────────────────");

await okAsync("start issues a device code and a human-readable user code", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const r = await call(env, "POST", {});
  assert.equal(r.status, 200);
  assert.match(r.body.device_code, /^[0-9a-f]{64}$/, "device_code is 32 random bytes in hex");
  assert.match(r.body.user_code, /^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/, "user code: " + r.body.user_code);
  assert.equal(r.body.verify_url, "https://tashan.sh/activate");
  assert.ok(r.body.interval >= 1 && r.body.expires_in >= 60);
});

await okAsync("the user code alphabet excludes I, O, 0 and 1", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  for (let i = 0; i < 60; i++) {
    const r = await call(env, "POST", {});
    assert.ok(!/[IO01]/.test(r.body.user_code.replace("-", "")), "ambiguous glyph in " + r.body.user_code);
  }
});

await okAsync("a fresh device code polls pending", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const p = await call(env, "POST", { device_code: s.body.device_code });
  assert.equal(p.body.status, "pending");
  assert.equal(p.body.key, undefined, "a pending poll must never carry a key");
});

await okAsync("polling faster than the floor gets slow_down, not the state", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  await call(env, "POST", { device_code: s.body.device_code });          // sets `last`
  const fast = await call(env, "POST", { device_code: s.body.device_code });
  assert.equal(fast.body.status, "slow_down");
});

await okAsync("an unknown device code is expired, never pending", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const p = await call(env, "POST", { device_code: "f".repeat(64) });
  assert.equal(p.body.status, "expired");
});

console.log("\n── approval requires a real session ───────────");

await okAsync("approving WITHOUT a session cookie is refused", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const a = await call(env, "POST", { user_code: s.body.user_code, approve: true });
  assert.equal(a.status, 401, "a device code must not be able to bootstrap an entitlement");
  const p = await call(env, "POST", { device_code: s.body.device_code });
  assert.notEqual(p.body.status, "ok");
});

await okAsync("approving with a session whose licence no longer validates is refused", async () => {
  withPolar(false);
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const a = await call(env, "POST", { user_code: s.body.user_code, approve: true },
    { cookie: "tashan_s=revoked_key" });
  assert.equal(a.status, 401, "a refunded key must not arm a new machine");
});

await okAsync("approving with a valid session hands the key to that device code once", async () => {
  withPolar(true);
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const a = await call(env, "POST", { user_code: s.body.user_code, approve: true },
    { cookie: "tashan_s=live_key" });
  assert.equal(a.status, 200);
  assert.equal(a.body.state, "approved");

  const first = await call(env, "POST", { device_code: s.body.device_code });
  assert.equal(first.body.status, "ok");
  assert.equal(first.body.key, "live_key");

  // SINGLE USE. A device code that keeps yielding the key is a bearer token in shell history.
  const second = await call(env, "POST", { device_code: s.body.device_code });
  assert.equal(second.body.status, "expired");
  assert.equal(second.body.key, undefined);
});

await okAsync("the user code is consumed too — it cannot approve a second device", async () => {
  withPolar(true);
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  await call(env, "POST", { user_code: s.body.user_code, approve: true }, { cookie: "tashan_s=live_key" });
  await call(env, "POST", { device_code: s.body.device_code });         // redeems + clears both
  const again = await call(env, "POST", { user_code: s.body.user_code, approve: true },
    { cookie: "tashan_s=live_key" });
  assert.equal(again.status, 404);
});

await okAsync("denying reports denied and stores no key", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const d = await call(env, "POST", { user_code: s.body.user_code, deny: true });
  assert.equal(d.body.state, "denied");
  const p = await call(env, "POST", { device_code: s.body.device_code });
  assert.equal(p.body.status, "denied");
  assert.equal(p.body.key, undefined);
});

console.log("\n── code handling ──────────────────────────────");

await okAsync("a code is matched case- and dash-insensitively", async () => {
  withPolar(true);
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const messy = s.body.user_code.toLowerCase().replace("-", " ");
  const a = await call(env, "POST", { user_code: messy, approve: true }, { cookie: "tashan_s=live_key" });
  assert.equal(a.status, 200, "a customer who omits the dash or types lowercase is still right");
});

await okAsync("GET ?code= says whether a code exists, and leaks nothing else", async () => {
  const env = { TASHAN_KV: kv(), POLAR_ORG_ID: "org" };
  const s = await call(env, "POST", {});
  const hit = await call(env, "GET", null, { query: "?code=" + s.body.user_code });
  assert.equal(hit.body.found, true);
  assert.deepEqual(Object.keys(hit.body), ["found"], "lookup must not describe the session behind it");
  const miss = await call(env, "GET", null, { query: "?code=ZZZZ-9999" });
  assert.equal(miss.body.found, false);
});

await okAsync("without KV the grant refuses rather than degrading to something weaker", async () => {
  const r = await call({ POLAR_ORG_ID: "org" }, "POST", {});
  assert.equal(r.status, 503, "no store means no single-use guarantee — fail closed");
});

await okAsync("GET without a code is a 400, not a crash", async () => {
  const env = { TASHAN_KV: kv() };
  const r = await call(env, "GET", null, { query: "" });
  assert.equal(r.status, 400);
});

console.log(`\n${pass}/${pass + fail} device-grant checks passed` + (fail ? ` · ${fail} FAILED` : " · all green"));
process.exit(fail ? 1 : 0);
