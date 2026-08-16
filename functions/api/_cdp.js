// Coinbase Developer Platform auth — a signed JWT per request, so we can settle through the CDP
// facilitator.
//
// WHY WE NEED THIS AT ALL, when a keyless facilitator exists. Two reasons, and the second is the one
// that decides it:
//
//  1. The keyless facilitator we configured (openx402) WHITELISTS receiving addresses and refuses
//     every payment to an unregistered one — `address_not_registered`. Measured 16 Aug 2026 with 25
//     other checks green. The two other live keyless facilitators cannot parse a spec-conformant v2
//     request at all (`pipeline/x402_probe.py` has the transcript).
//  2. THE BAZAAR ONLY INDEXES WHAT THE CDP FACILITATOR SETTLES. The Bazaar is the discovery layer
//     agents search to find paid endpoints — a seller is indexed within ~30s of their first
//     confirmed settle. Settling anywhere else means no caller ever finds us, which for a service
//     whose whole distribution is being asked by an agent is worse than the whitelist.
//
// So this is not a preference between vendors. It is the difference between being payable-and-
// findable and being neither.
//
// THE FORMAT IS EXACT AND UNFORGIVING — a wrong claim is a 401 with no explanation. Per CDP's
// authentication reference:
//   header  { alg: "EdDSA", typ: "JWT", kid: <key id>, nonce: <32 hex chars> }
//   claims  { sub: <key id>, iss: "cdp", aud: ["cdp_service"], nbf: now, exp: now + 120,
//             uri: "<METHOD> <host><path>" }
// signed Ed25519 over `base64url(header).base64url(claims)`. Valid two minutes, so it is minted per
// request and never cached.
//
// NOTHING HERE IS OPTIONAL-BY-ACCIDENT. If the key id or secret is missing, no Authorization header
// is produced and the caller falls back to the keyless path unchanged — configuring half of this
// must not silently change which facilitator we talk to.

// SubjectPublicKeyInfo/PKCS8 wrapper for a bare Ed25519 seed. Fixed 16 bytes, then the 32-byte
// seed. Verified against WebCrypto's own exportKey("pkcs8") output: rebuilding from the seed
// produces byte-identical signatures.
const PKCS8_ED25519_PREFIX = new Uint8Array([
  0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
]);

const enc = new TextEncoder();

function b64url(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

const b64urlText = (str) => b64url(enc.encode(str));

function unb64(b64) {
  const bin = atob(String(b64).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function hex(n) {
  const b = new Uint8Array(n);
  crypto.getRandomValues(b);
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/** CDP hands the Ed25519 secret out as base64 of 64 bytes: seed(32) || publicKey(32). WebCrypto
 *  wants PKCS8, and only the seed goes into it — passing all 64 fails to import with an error that
 *  does not say why. */
export async function importCdpKey(secretB64) {
  const raw = unb64(secretB64);
  if (raw.length !== 64 && raw.length !== 32) {
    throw new Error(`CDP secret is ${raw.length} bytes; expected 32 (seed) or 64 (seed||public)`);
  }
  const seed = raw.slice(0, 32);
  const pkcs8 = new Uint8Array(PKCS8_ED25519_PREFIX.length + 32);
  pkcs8.set(PKCS8_ED25519_PREFIX, 0);
  pkcs8.set(seed, PKCS8_ED25519_PREFIX.length);
  return crypto.subtle.importKey("pkcs8", pkcs8, { name: "Ed25519" }, false, ["sign"]);
}

/** A Bearer token for one request. `url` decides the `uri` claim, so it must be the URL actually
 *  being called — CDP rejects a token minted for a different method or path. */
export async function cdpBearer(keyId, secretB64, method, url, now = Math.floor(Date.now() / 1000)) {
  const u = new URL(url);
  const key = await importCdpKey(secretB64);
  const header = { alg: "EdDSA", typ: "JWT", kid: keyId, nonce: hex(16) };
  const claims = {
    sub: keyId,
    iss: "cdp",
    aud: ["cdp_service"],
    nbf: now,
    exp: now + 120,
    uri: `${String(method).toUpperCase()} ${u.host}${u.pathname}`,
  };
  const signingInput = `${b64urlText(JSON.stringify(header))}.${b64urlText(JSON.stringify(claims))}`;
  const sig = new Uint8Array(await crypto.subtle.sign("Ed25519", key, enc.encode(signingInput)));
  return `${signingInput}.${b64url(sig)}`;
}

/** The Authorization header for a CDP call, or {} when this deployment is not using CDP.
 *  BOTH values or neither — a half-configured pair must not produce a token that cannot work. */
export async function cdpAuthHeader(env, method, url) {
  const id = (env.X402_CDP_KEY_ID || "").trim();
  const secret = (env.X402_CDP_KEY_SECRET || "").trim();
  if (!id || !secret) return {};
  try {
    return { authorization: `Bearer ${await cdpBearer(id, secret, method, url)}` };
  } catch (_) {
    // A malformed key must not take the paid path down with it: no header means the facilitator
    // answers 401, facilitate() throws, and charge() denies — closed, and visible in the logs.
    return {};
  }
}

export const _internals = { b64url, unb64, PKCS8_ED25519_PREFIX };
