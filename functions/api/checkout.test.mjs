// The post-purchase sign-in. This endpoint turns a checkout id — a value that rides in a redirect
// URL and lands in browser history — into a signed-in session, using an org token that can read
// every customer's record. The tests are almost entirely about what it must REFUSE.
//
//   node functions/api/checkout.test.mjs
import assert from "node:assert";
import { onRequest } from "./checkout.js";

let pass = 0, fail = 0;
const ok = async (name, fn) => {
  try { await fn(); console.log("  ok   " + name); pass++; }
  catch (e) { console.log("  FAIL " + name + "\n       " + e.message); fail++; }
};

function kv() {
  const m = new Map();
  return { m, async get(k) { return m.has(k) ? m.get(k) : null; },
           async put(k, v) { m.set(k, String(v)); }, async delete(k) { m.delete(k); } };
}

// A Polar double. `co` is the checkout it returns; `keys` the licence keys.
function polarStub({ co, keys = [{ status: "granted", key: "tashan_live" }], sessionToken = "cst_1" }) {
  const seen = [];
  globalThis.fetch = async (u, init = {}) => {
    const url = String(u);
    seen.push({ url, auth: (init.headers || {}).authorization });
    const J = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json" } });
    if (url.includes("/checkouts/")) return co ? J(co) : new Response("", { status: 404 });
    if (url.includes("/customer-sessions/")) return J({ token: sessionToken });
    if (url.includes("/customer-portal/license-keys")) return J({ items: keys });
    return new Response("", { status: 404 });
  };
  return seen;
}

const PAID = { status: "succeeded", customer_id: "cus_1", modified_at: new Date().toISOString() };

const call = (env, id = "co_1") =>
  onRequest({ request: new Request(`https://tashan.sh/api/checkout?id=${id}`), env });

const cookieOf = (r) => r.headers.get("set-cookie") || "";
const locOf = (r) => r.headers.get("location") || "";

console.log("\n── post-purchase sign-in ──────────────────────");

await ok("a paid checkout signs the customer in and never echoes the key", async () => {
  polarStub({ co: PAID });
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.equal(r.status, 302);
  assert.match(locOf(r), /\/welcome$/);
  assert.match(cookieOf(r), /tashan_s=tashan_live/);
  assert.match(cookieOf(r), /HttpOnly/, "the session cookie must not be script-readable");
  assert.match(cookieOf(r), /Secure/);
  assert.equal(await r.text(), "", "the licence key must never appear in a response body");
});

await ok("the customer-portal call uses the CUSTOMER session token, never the org token", async () => {
  const seen = polarStub({ co: PAID });
  await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  const portal = seen.find(s => s.url.includes("license-keys"));
  assert.equal(portal.auth, "Bearer cst_1", "org token must not reach the customer-portal API");
});

console.log("\n── what it must refuse ────────────────────────");

await ok("SINGLE USE — a replayed checkout id gets nothing", async () => {
  polarStub({ co: PAID });
  const env = { POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() };
  const first = await call(env);
  assert.match(cookieOf(first), /tashan_s=/);
  const replay = await call(env);
  assert.equal(cookieOf(replay), "", "a leaked URL must not sign anyone in twice");
  assert.match(locOf(replay), /e=used/);
});

await ok("an UNPAID checkout signs nobody in", async () => {
  polarStub({ co: { ...PAID, status: "open" } });
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.equal(cookieOf(r), "", "starting a checkout must not grant a session");
  assert.match(locOf(r), /e=unpaid/);
});

await ok("a STALE checkout is refused", async () => {
  const old = new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString();
  polarStub({ co: { ...PAID, modified_at: old } });
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.equal(cookieOf(r), "");
  assert.match(locOf(r), /e=stale/);
});

await ok("a configured site with an unresolvable id does not blame its own config", async () => {
  polarStub({ co: null });                       // Polar 404s the checkout
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.ok(!locOf(r).includes("unconfigured"),
            "that would send the operator hunting a binding that is fine");
});

await ok("without KV it refuses rather than issue a replayable session", async () => {
  polarStub({ co: PAID });
  const r = await call({ POLAR_ORG_TOKEN: "oat" });
  assert.equal(cookieOf(r), "", "no single-use store means no session");
  // ?e=unconfigured, not a bare /welcome. A missing binding used to be indistinguishable from a
  // checkout id that simply did not resolve, so the only way to discover that auto-sign-in was off
  // was a paying customer landing on a paste form — and nothing outside the site could tell.
  assert.match(locOf(r), /\/welcome\?e=unconfigured$/);
});

await ok("without the org token it falls back to /welcome, not an error page", async () => {
  polarStub({ co: PAID });
  const r = await call({ TASHAN_KV: kv() });
  assert.equal(r.status, 302);
  assert.match(locOf(r), /\/welcome\?e=unconfigured$/, "say it is us, not a bad link");
  assert.equal(cookieOf(r), "");
});

await ok("an unknown checkout id signs nobody in", async () => {
  polarStub({ co: null });
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.equal(cookieOf(r), "");
});

await ok("a customer with no licence key is not handed someone else's", async () => {
  polarStub({ co: PAID, keys: [] });
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.equal(cookieOf(r), "");
});

await ok("a granted key is preferred over a revoked one", async () => {
  polarStub({ co: PAID, keys: [{ status: "revoked", key: "dead" }, { status: "granted", key: "live" }] });
  const r = await call({ POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() });
  assert.match(cookieOf(r), /tashan_s=live/);
});

await ok("no id at all just goes to /welcome", async () => {
  polarStub({ co: PAID });
  const r = await onRequest({ request: new Request("https://tashan.sh/api/checkout"),
                             env: { POLAR_ORG_TOKEN: "oat", TASHAN_KV: kv() } });
  assert.match(locOf(r), /\/welcome/);
  assert.equal(cookieOf(r), "");
});

console.log(`\n${pass}/${pass + fail} checkout checks passed` + (fail ? ` · ${fail} FAILED` : " · all green"));
process.exit(fail ? 1 : 0);
