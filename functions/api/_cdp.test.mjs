// CDP auth. A wrong claim here is a 401 with no explanation, and a 401 means charge() denies — so
// every payment fails and the log says "verification_unavailable". These assertions are the spec,
// written down: header, claims, expiry, uri format, and a signature that actually verifies.
//
//   node functions/api/_cdp.test.mjs
import assert from "node:assert";
import { webcrypto } from "node:crypto";
if (!globalThis.crypto) globalThis.crypto = webcrypto;

const { cdpBearer, cdpAuthHeader, importCdpKey, _internals } = await import("./_cdp.js");

let pass = 0, fail = 0;
const ok = async (name, fn) => {
  try { await fn(); console.log("  ok   " + name); pass++; }
  catch (e) { console.log("  FAIL " + name + "\n       " + e.message); fail++; }
};

const dec = (b64) => JSON.parse(Buffer.from(String(b64).replace(/-/g, "+").replace(/_/g, "/"), "base64")
                                     .toString("utf8"));

// A real Ed25519 keypair, exported the way CDP hands one out: base64 of seed(32) || public(32).
const kp = await webcrypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
const pkcs8 = new Uint8Array(await webcrypto.subtle.exportKey("pkcs8", kp.privateKey));
const seed = pkcs8.slice(16);
const pub = new Uint8Array(await webcrypto.subtle.exportKey("raw", kp.publicKey));
const SECRET = Buffer.concat([Buffer.from(seed), Buffer.from(pub)]).toString("base64");
const KEY_ID = "organizations/abc/apiKeys/def";
const URL_ = "https://api.cdp.coinbase.com/platform/v2/x402/verify";

console.log("\n── CDP bearer token ───────────────────────────");

await ok("mints a three-part JWT", async () => {
  const t = await cdpBearer(KEY_ID, SECRET, "POST", URL_);
  assert.equal(t.split(".").length, 3, t.slice(0, 40));
});

await ok("header carries EdDSA, JWT, the key id and a nonce", async () => {
  const h = dec((await cdpBearer(KEY_ID, SECRET, "POST", URL_)).split(".")[0]);
  assert.equal(h.alg, "EdDSA");
  assert.equal(h.typ, "JWT");
  assert.equal(h.kid, KEY_ID);
  assert.match(h.nonce, /^[0-9a-f]{32}$/, "nonce must be 16 random bytes as hex: " + h.nonce);
});

await ok("...and the nonce is different every time (it is replay protection)", async () => {
  const a = dec((await cdpBearer(KEY_ID, SECRET, "POST", URL_)).split(".")[0]).nonce;
  const b = dec((await cdpBearer(KEY_ID, SECRET, "POST", URL_)).split(".")[0]).nonce;
  assert.notEqual(a, b);
});

await ok("claims match CDP's reference exactly", async () => {
  const c = dec((await cdpBearer(KEY_ID, SECRET, "POST", URL_, 1_700_000_000)).split(".")[1]);
  assert.equal(c.sub, KEY_ID);
  assert.equal(c.iss, "cdp");
  assert.deepEqual(c.aud, ["cdp_service"]);
  assert.equal(c.nbf, 1_700_000_000);
  assert.equal(c.exp, 1_700_000_120, "tokens are valid for 2 minutes");
});

await ok("the uri claim is '<METHOD> <host><path>' — no scheme, no query", async () => {
  const c = dec((await cdpBearer(KEY_ID, SECRET, "post",
                                 URL_ + "?ignored=1")).split(".")[1]);
  assert.equal(c.uri, "POST api.cdp.coinbase.com/platform/v2/x402/verify", c.uri);
});

await ok("a token minted for /verify does not claim /settle", async () => {
  const v = dec((await cdpBearer(KEY_ID, SECRET, "POST", URL_)).split(".")[1]).uri;
  const s = dec((await cdpBearer(KEY_ID, SECRET, "POST",
    "https://api.cdp.coinbase.com/platform/v2/x402/settle")).split(".")[1]).uri;
  assert.notEqual(v, s);
  assert.ok(s.endsWith("/settle"), s);
});

await ok("the signature verifies against the public key", async () => {
  const t = await cdpBearer(KEY_ID, SECRET, "POST", URL_);
  const [h, c, sig] = t.split(".");
  const bytes = Buffer.from(sig.replace(/-/g, "+").replace(/_/g, "/"), "base64");
  const okSig = await webcrypto.subtle.verify("Ed25519", kp.publicKey, bytes,
                                              new TextEncoder().encode(`${h}.${c}`));
  assert.ok(okSig, "CDP would reject this token");
});

await ok("a tampered payload no longer verifies", async () => {
  const [h, , sig] = (await cdpBearer(KEY_ID, SECRET, "POST", URL_)).split(".");
  const evil = Buffer.from(JSON.stringify({ sub: "someone-else", iss: "cdp" })).toString("base64url");
  const bytes = Buffer.from(sig.replace(/-/g, "+").replace(/_/g, "/"), "base64");
  const okSig = await webcrypto.subtle.verify("Ed25519", kp.publicKey, bytes,
                                              new TextEncoder().encode(`${h}.${evil}`));
  assert.equal(okSig, false);
});

await ok("accepts a bare 32-byte seed as well as the 64-byte form", async () => {
  const bare = Buffer.from(seed).toString("base64");
  await importCdpKey(bare);                       // must not throw
  const t = await cdpBearer(KEY_ID, bare, "POST", URL_);
  assert.equal(t.split(".").length, 3);
});

await ok("a secret of the wrong length is rejected loudly, not signed with", async () => {
  await assert.rejects(() => importCdpKey(Buffer.from("short").toString("base64")), /expected 32/);
});

console.log("\n── the header, and staying dormant ────────────");

await ok("no key id and no secret means NO Authorization header", async () => {
  assert.deepEqual(await cdpAuthHeader({}, "POST", URL_), {});
});

await ok("HALF a configuration produces no header — never a token that cannot work", async () => {
  assert.deepEqual(await cdpAuthHeader({ X402_CDP_KEY_ID: KEY_ID }, "POST", URL_), {});
  assert.deepEqual(await cdpAuthHeader({ X402_CDP_KEY_SECRET: SECRET }, "POST", URL_), {});
});

await ok("both set produces a Bearer header", async () => {
  const h = await cdpAuthHeader({ X402_CDP_KEY_ID: KEY_ID, X402_CDP_KEY_SECRET: SECRET },
                                "POST", URL_);
  assert.match(h.authorization, /^Bearer [\w-]+\.[\w-]+\.[\w-]+$/);
});

await ok("a malformed secret yields no header rather than throwing into the paid path", async () => {
  // charge() must still reach the facilitator, get a 401, and DENY. Throwing here would surface as
  // an unhandled error instead of a clean refusal.
  const h = await cdpAuthHeader({ X402_CDP_KEY_ID: KEY_ID, X402_CDP_KEY_SECRET: "!!!not base64!!!" },
                                "POST", URL_);
  assert.deepEqual(h, {});
});

console.log(`\n  ${pass} passing, ${fail} failing\n`);
process.exit(fail ? 1 : 0);
