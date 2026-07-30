// Polar webhook verification — the security boundary. Run: node functions/api/polar.test.mjs
//
// Every case here is a way a forged or stale delivery could be accepted. A verifier that fails OPEN
// hands anyone who can POST to the endpoint the ability to grant themselves entitlement.
import { verify, safeEqual, entitlementFrom } from "./polar.js";
import { webcrypto } from "node:crypto";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

let fail = 0;
const ok = (name, cond) => { if (!cond) fail = 1; console.log((cond ? "  ok   " : "  FAIL ") + name); };

// Polar's secret is base64; the HMAC key is the DECODED bytes.
const SECRET_BYTES = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]);
const SECRET_B64 = Buffer.from(SECRET_BYTES).toString("base64");
const NOW = 1800000000;

async function sign(id, ts, body, keyBytes = SECRET_BYTES) {
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-256" },
                                            false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${ts}.${body}`));
  return Buffer.from(new Uint8Array(mac)).toString("base64");
}

const BODY = JSON.stringify({ type: "subscription.active", data: { customer: { email: "A@Example.com" } } });
const ID = "evt_123";

const hdr = (id, ts, sig) => ({ "webhook-id": id, "webhook-timestamp": String(ts), "webhook-signature": sig });

// --- the happy path -------------------------------------------------------------------------
const good = await sign(ID, NOW, BODY);
ok("valid signature passes", (await verify(SECRET_B64, hdr(ID, NOW, `v1,${good}`), BODY, NOW)).ok);
ok("secret with whsec_ prefix passes",
   (await verify("whsec_" + SECRET_B64, hdr(ID, NOW, `v1,${good}`), BODY, NOW)).ok);
ok("multiple signatures — any one matching passes (secret rotation)",
   (await verify(SECRET_B64, hdr(ID, NOW, `v1,AAAA v1,${good}`), BODY, NOW)).ok);
ok("within tolerance passes", (await verify(SECRET_B64, hdr(ID, NOW, `v1,${good}`), BODY, NOW + 299)).ok);

// --- everything that must FAIL --------------------------------------------------------------
ok("tampered body fails",
   !(await verify(SECRET_B64, hdr(ID, NOW, `v1,${good}`), BODY.replace("active", "revoked"), NOW)).ok);
ok("wrong secret fails",
   !(await verify(Buffer.from(new Uint8Array(16)).toString("base64"),
                  hdr(ID, NOW, `v1,${good}`), BODY, NOW)).ok);
ok("replayed old delivery fails (outside tolerance)",
   !(await verify(SECRET_B64, hdr(ID, NOW, `v1,${good}`), BODY, NOW + 301)).ok);
ok("future-dated delivery fails",
   !(await verify(SECRET_B64, hdr(ID, NOW, `v1,${good}`), BODY, NOW - 301)).ok);
ok("signature bound to webhook-id — reusing it under another id fails",
   !(await verify(SECRET_B64, hdr("evt_OTHER", NOW, `v1,${good}`), BODY, NOW)).ok);
ok("signature bound to timestamp — same sig at another ts fails",
   !(await verify(SECRET_B64, hdr(ID, NOW + 10, `v1,${good}`), BODY, NOW + 10)).ok);
ok("missing headers fail", !(await verify(SECRET_B64, hdr("", "", ""), BODY, NOW)).ok);
ok("unset secret fails (unconfigured must not accept everything)",
   !(await verify(undefined, hdr(ID, NOW, `v1,${good}`), BODY, NOW)).ok);
ok("unknown signature version fails",
   !(await verify(SECRET_B64, hdr(ID, NOW, `v2,${good}`), BODY, NOW)).ok);
ok("bare signature without version fails",
   !(await verify(SECRET_B64, hdr(ID, NOW, good), BODY, NOW)).ok);

// THE BASE64 TRAP: signing with the ASCII of the secret string instead of its decoded bytes is the
// classic hand-rolled mistake. It must not verify.
const asciiSig = await sign(ID, NOW, BODY, new TextEncoder().encode(SECRET_B64));
ok("secret used as raw ASCII instead of decoded base64 fails",
   !(await verify(SECRET_B64, hdr(ID, NOW, `v1,${asciiSig}`), BODY, NOW)).ok);

// --- helpers ---------------------------------------------------------------------------------
ok("safeEqual true for equal", safeEqual("abc", "abc"));
ok("safeEqual false for different length", !safeEqual("abc", "abcd"));
ok("safeEqual false for non-strings", !safeEqual(null, null));

ok("grant event maps to active + lowercased email",
   JSON.stringify(entitlementFrom(JSON.parse(BODY))) ===
   JSON.stringify({ email: "a@example.com", state: "active", type: "subscription.active" }));
ok("revoke event maps to inactive",
   entitlementFrom({ type: "subscription.revoked", data: { customer: { email: "b@x.io" } } }).state === "inactive");
ok("unrelated event maps to null (acknowledged, not acted on)",
   entitlementFrom({ type: "product.updated", data: { customer: { email: "b@x.io" } } }) === null);
ok("event with no customer email maps to null",
   entitlementFrom({ type: "order.paid", data: {} }) === null);

// ---- the handler, end to end: signed delivery -> entitlement in KV ------------------------------
// verify() was covered above; onRequestPost was not, and it is the half that actually grants access.
{
  const { onRequestPost } = await import("./polar.js");
  const kv = () => { const m = new Map(); return { m, get: async (k) => m.get(k) ?? null,
                                                   put: async (k, v) => void m.set(k, v) }; };
  const SECRET = Buffer.from(new Uint8Array([9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5, 6])).toString("base64");
  const deliver = async (env, event, { tamper = false, id = "evt_1" } = {}) => {
    const body = JSON.stringify(event);
    const ts = Math.floor(Date.now() / 1000);
    const key = await crypto.subtle.importKey("raw", Buffer.from(SECRET, "base64"),
      { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${ts}.${body}`));
    const sig = Buffer.from(new Uint8Array(mac)).toString("base64");
    return onRequestPost({ env, request: new Request("https://tashan.sh/api/polar", {
      method: "POST", body: tamper ? body + " " : body,
      headers: { "webhook-id": id, "webhook-timestamp": String(ts), "webhook-signature": `v1,${sig}` },
    }) });
  };

  const sub = (type, email) => ({ type, data: { customer: { email } } });

  let env = { POLAR_WEBHOOK_SECRET: SECRET, TASHAN_KV: kv() };
  let res = await deliver(env, sub("subscription.active", "Buyer@Example.com"));
  ok("a signed subscription.active is accepted", res.status === 200);
  const granted = JSON.parse(env.TASHAN_KV.m.get("ent:buyer@example.com") || "{}");
  ok("entitlement is written, keyed by lowercased email", granted.state === "active");

  // THE REFUND PATH. Polar can refund on its own within 60 days to head off a chargeback, so this
  // must revoke without us doing anything — otherwise a refunded customer keeps paid access.
  res = await deliver(env, sub("order.refunded", "buyer@example.com"), { id: "evt_2" });
  ok("a refund is accepted", res.status === 200);
  ok("...and revokes the entitlement",
     JSON.parse(env.TASHAN_KV.m.get("ent:buyer@example.com")).state === "inactive");

  res = await deliver(env, sub("subscription.revoked", "buyer@example.com"), { id: "evt_3" });
  ok("a revoked subscription also revokes access",
     JSON.parse(env.TASHAN_KV.m.get("ent:buyer@example.com")).state === "inactive");

  // A tampered body must never reach the store.
  const before = env.TASHAN_KV.m.size;
  res = await deliver(env, sub("subscription.active", "attacker@evil.com"), { tamper: true, id: "evt_4" });
  ok("a tampered delivery is rejected 403", res.status === 403);
  ok("...and writes nothing", env.TASHAN_KV.m.size === before);

  // An unknown event type is acknowledged, never 5xx — Polar disables an endpoint after 10 non-2xx.
  res = await deliver(env, { type: "product.updated", data: {} }, { id: "evt_5" });
  ok("an unrelated event is acknowledged 2xx", res.status >= 200 && res.status < 300);

  // No KV bound yet must still 2xx, for the same reason.
  res = await deliver({ POLAR_WEBHOOK_SECRET: SECRET }, sub("order.paid", "x@y.z"), { id: "evt_6" });
  ok("an unbound KV still acknowledges rather than 5xx-ing the endpoint into being disabled",
     res.status >= 200 && res.status < 300);

  // Unparseable JSON: acknowledge, since retrying will not make it parse.
  const ts = Math.floor(Date.now() / 1000);
  const k2 = await crypto.subtle.importKey("raw", Buffer.from(SECRET, "base64"),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const m2 = await crypto.subtle.sign("HMAC", k2, new TextEncoder().encode(`evt_7.${ts}.{oops`));
  res = await onRequestPost({ env, request: new Request("https://tashan.sh/api/polar", {
    method: "POST", body: "{oops",
    headers: { "webhook-id": "evt_7", "webhook-timestamp": String(ts),
               "webhook-signature": `v1,${Buffer.from(new Uint8Array(m2)).toString("base64")}` } }) });
  ok("malformed JSON is acknowledged, not retried forever", res.status >= 200 && res.status < 300);
}

console.log(fail ? "POLAR WEBHOOK FAILED" : "ok — polar webhook (verification + handler + refund path)");
process.exit(fail);
