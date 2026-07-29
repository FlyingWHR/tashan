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

console.log(fail ? "POLAR WEBHOOK FAILED" : "ok — polar webhook verification");
process.exit(fail);
