// The paywall. Run: node functions/api/license.test.mjs
//
// Every case is a way someone gets paid data without paying, or a way a paying customer gets locked
// out. Both are failures; the first is worse.
import { keyFrom, validate, deny } from "./_license.js";
import { bucketOf } from "./history.js";
import { webcrypto } from "node:crypto";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

let fail = 0;
const ok = (n, c) => { if (!c) fail = 1; console.log((c ? "  ok   " : "  FAIL ") + n); };

// in-memory KV double
const kv = () => {
  const m = new Map();
  return { m, get: async k => (m.has(k) ? m.get(k) : null), put: async (k, v) => void m.set(k, v) };
};
const req = (h = {}, url = "https://tashan.sh/api/history?id=pkg:x") =>
  new Request(url, { headers: h });

// ---- key extraction ----
ok("reads Bearer token", keyFrom(req({ authorization: "Bearer abc123" })) === "abc123");
ok("Bearer is case-insensitive", keyFrom(req({ authorization: "bearer abc123" })) === "abc123");
ok("reads ?key=", keyFrom(req({}, "https://tashan.sh/api/history?id=a&key=xyz")) === "xyz");
ok("no key -> empty", keyFrom(req()) === "");

// ---- the refusals that must happen without ever calling Polar ----
let called = 0;
globalThis.fetch = async () => { called++; return new Response("{}", { status: 400 }); };

let v = await validate({ POLAR_ORG_ID: "org_1" }, "");
ok("empty key denied 401, no network call", !v.ok && v.status === 401 && called === 0);

v = await validate({}, "some-key");
ok("UNCONFIGURED deployment denies everyone (fails closed)", !v.ok && v.status === 503);
ok("...and did not call Polar", called === 0);

// ---- a bad key ----
const env1 = { POLAR_ORG_ID: "org_1", TASHAN_KV: kv() };
v = await validate(env1, "bad-key");
ok("Polar 4xx -> denied 403", !v.ok && v.status === 403);
ok("negative result is cached", [...env1.TASHAN_KV.m.values()].includes("0"));
ok("cache key is a HASH, never the licence key itself",
   ![...env1.TASHAN_KV.m.keys()].some(k => k.includes("bad-key")));

// ---- Polar outage must not lock out paying customers ----
called = 0;
globalThis.fetch = async () => { called++; return new Response("nope", { status: 503 }); };
const env2 = { POLAR_ORG_ID: "org_1", TASHAN_KV: kv() };
v = await validate(env2, "good-key");
ok("Polar 5xx -> 503, not 403", !v.ok && v.status === 503);
ok("...and a 5xx is NOT cached as a negative", env2.TASHAN_KV.m.size === 0);

globalThis.fetch = async () => { throw new Error("network down"); };
v = await validate({ POLAR_ORG_ID: "org_1" }, "good-key");
ok("network throw -> 503, not a crash and not an allow", !v.ok && v.status === 503);

// ---- statuses ----
const polarSays = (body, status = 200) => { globalThis.fetch = async () => new Response(JSON.stringify(body), { status }); };

polarSays({ status: "granted" });
v = await validate({ POLAR_ORG_ID: "org_1" }, "k");
ok("granted -> allowed", v.ok);

polarSays({ status: "revoked" });
v = await validate({ POLAR_ORG_ID: "org_1" }, "k");
ok("revoked -> denied", !v.ok && v.status === 403);

polarSays({ status: "disabled" });
v = await validate({ POLAR_ORG_ID: "org_1" }, "k");
ok("any non-granted status -> denied", !v.ok);

polarSays({ status: "granted", expires_at: new Date(Date.now() - 86400000).toISOString() });
v = await validate({ POLAR_ORG_ID: "org_1" }, "k");
ok("granted but EXPIRED -> denied", !v.ok && /expired/.test(v.why));

polarSays({ status: "granted", expires_at: new Date(Date.now() + 86400000).toISOString() });
v = await validate({ POLAR_ORG_ID: "org_1" }, "k");
ok("granted and unexpired -> allowed", v.ok);

polarSays({});
v = await validate({ POLAR_ORG_ID: "org_1" }, "k");
ok("empty/garbage response -> denied (never default-allow)", !v.ok);

// ---- cache is honoured, and a poisoned positive cannot come from a denial ----
const env3 = { POLAR_ORG_ID: "org_1", TASHAN_KV: kv() };
polarSays({ status: "granted" });
await validate(env3, "k");
called = 0;
globalThis.fetch = async () => { called++; return new Response("{}", { status: 400 }); };
v = await validate(env3, "k");
ok("second call served from cache without hitting Polar", v.ok && v.cached && called === 0);

// ---- the refusal body must not leak ----
const body = await deny({ status: 403, why: "licence not valid" }).json();
ok("denial returns only an error + docs link", Object.keys(body).sort().join(",") === "docs,error");
ok("denial is no-store", deny({ status: 403, why: "x" }).headers.get("cache-control") === "no-store");

// ---- shard bucketing must agree with pipeline/push_history.py bucket_of() ----
// These exact pairs are cross-checked against the Python implementation; if either side changes
// without the other, every paying customer's lookup 404s silently.
const VECTORS = [["pkg:tavily-mcp", "2"], ["registry:ai.x/y", "11"], ["@scope/thing", "35"],
                 ["---", "7"], ["", "0"], ["plugin:Foo/Bar/baz", "29"], ["9lives", "28"],
                 ["pkg:@modelcontextprotocol/server-filesystem", "60"]];
for (const [id, want] of VECTORS) {
  ok(`bucket(${JSON.stringify(id)}) === ${want}`, bucketOf(id) === want);
}
ok("every bucket is within range", VECTORS.every(([id]) => {
  const n = Number(bucketOf(id));
  return Number.isInteger(n) && n >= 0 && n < 64;
}));

console.log(fail ? "PAYWALL FAILED" : "ok — licence gate");
process.exit(fail);
