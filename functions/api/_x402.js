// x402 — pay-per-request, for callers that are software.
//
// WHY THIS EXISTS. A licence key assumes a human: someone signs up, stores a credential, and amortises
// $6/mo over a month of use. An agent deciding once whether to install a package has no account, no
// credential store and no reason to hold a subscription — it wants to pay a fraction of a cent for
// one answer and move on. x402 is the standard for exactly that: HTTP 402 carries the price, the
// client retries with a signed payment, a facilitator verifies and settles.
//
// IMPLEMENTED AGAINST specs/x402-specification-v2.md and specs/transports-v2/{http,mcp}.md from
// github.com/coinbase/x402, read directly rather than remembered. v2 is what the field names below
// follow: `amount` (atomic units, string), CAIP-2 `network`, and the PAYMENT-REQUIRED /
// PAYMENT-SIGNATURE / PAYMENT-RESPONSE header trio. v1's `maxAmountRequired` and `X-PAYMENT` are a
// different generation; we do not claim to speak it.
//
// ==================================================================================================
// IT IS DORMANT UNTIL A WALLET EXISTS, AND THAT IS THE POINT.
//
// Settlement needs an address we control (`X402_PAY_TO`) and a facilitator. We have neither yet, and
// creating a wallet is a decision for the CEO, not a thing to improvise in a deploy. So:
//
//   configured()  false  ->  no `accepts`, no PAYMENT-REQUIRED header. The 402 still quotes the
//                            subscription price and the free endpoints, exactly as it does today.
//   configured()  true   ->  the same 402 additionally carries a spec-shaped PaymentRequired, and
//                            paid routes verify and settle.
//
// Advertising payment options we cannot settle would be a door that looks open and is not — worse
// than no door, because the agent burns a signature and gets nothing. Everything here is written and
// tested so that turning it on is setting three secrets, not writing code under time pressure.
// ==================================================================================================

import { cdpAuthHeader } from "./_cdp.js";

// One definition of what each paid thing costs. Atomic units, because that is what the wire carries:
// USDC has 6 decimals, so $0.01 is "10000". Keeping the human price beside it means the two cannot
// drift, and `usd` is what the JSON fallback and the docs quote.
export const PRICED = {
  "capability-history": {
    usd: 0.01,
    atomic: "10000",
    description: "The full score history for one capability, every point we have recorded.",
  },
  // `security-detail` WAS HERE AT $0.01 AND HAS BEEN REMOVED — it sold data we publish for free.
  // redact_paid() had already moved advisory ids, severities, fixing versions and the install
  // command into the public export, and /v0.1/lookup returns all of them per capability with no
  // account. The 402 quoting this price even listed /data/lookup.json in its own `free` block as a
  // source of those exact fields.
  //
  // What is left on this ladder is coherent, and that is the point: EVERY priced resource sells
  // either TIME (a series, a direction of travel) or ASSEMBLY (selection, pinning, a config). None
  // of them sells the current state of anything, because the current state is the free tier and the
  // free tier is the distribution.
  "capability-kit": {
    usd: 0.25,
    atomic: "250000",
    description: "A ready-to-run kit for one job: which capabilities to install, pinned to the "
               + "version the advisory scan actually cleared, with a config for your host.",
  },
  "config-audit": {
    usd: 0.05,
    atomic: "50000",
    description: "Audit a whole config: for every capability you run, what changed since a date "
               + "you name, and what to move to.",
  },
};

const VERSION = 2;
const SCHEME = "exact";
const TIMEOUT_S = 60;

export function config(env) {
  return {
    payTo: (env.X402_PAY_TO || "").trim(),
    network: (env.X402_NETWORK || "").trim(),
    asset: (env.X402_ASSET || "").trim(),
    facilitator: (env.X402_FACILITATOR || "").trim().replace(/\/+$/, ""),
    // "USD Coin", NOT "USDC". This is the EIP-712 domain name the client signs against, and it must
    // equal the token contract's own `name()` exactly or the signature does not verify. USDC's
    // contract on Base — mainnet AND Sepolia — is named "USD Coin"; the ticker is not the name.
    // Confirmed 16 Aug 2026 from facilitator.openx402.ai/supported, which publishes the domain per
    // network: eip155:8453 and eip155:84532 both report name "USD Coin", version "2".
    //
    // The old default was "USDC", which is wrong on the only two networks we would plausibly use.
    // Nothing would have LOOKED broken: all four secrets set, `configured()` true, a spec-shaped
    // `accepts` array quoted on every 402 — and every payment silently failing to verify. Override
    // per network where the name genuinely differs (Monad's is "USDC"); check_payments.py compares
    // this against the facilitator's own answer so a mismatch is named rather than discovered.
    assetName: (env.X402_ASSET_NAME || "USD Coin").trim(),
    assetVersion: (env.X402_ASSET_VERSION || "2").trim(),
  };
}

// ALL FOUR OR NONE. A payTo with no facilitator would quote a price we cannot verify a payment
// against, which is the failure mode this whole file is arranged to avoid.
export function configured(env) {
  const c = config(env);
  return Boolean(c.payTo && c.network && c.asset && c.facilitator);
}

const b64 = (obj) => btoa(unescape(encodeURIComponent(JSON.stringify(obj))));

function unb64(s) {
  try {
    return JSON.parse(decodeURIComponent(escape(atob(s))));
  } catch {
    return null;                       // malformed header: treated as "no payment", never as a pass
  }
}

/** The PaymentRequired object — the v2 body/structuredContent shape, identical on both transports. */
export function paymentRequired(env, key, resourceUrl, error = "payment required") {
  const p = PRICED[key];
  if (!p || !configured(env)) return null;
  const c = config(env);
  return {
    x402Version: VERSION,
    error,
    resource: { url: resourceUrl, description: p.description, mimeType: "application/json" },
    accepts: [{
      scheme: SCHEME,
      network: c.network,
      amount: p.atomic,
      asset: c.asset,
      payTo: c.payTo,
      maxTimeoutSeconds: TIMEOUT_S,
      extra: { name: c.assetName, version: c.assetVersion },
    }],
    extensions: {},
  };
}

export const requiredHeader = (pr) => (pr ? { "payment-required": b64(pr) } : {});

/** The client's signed payload, from the HTTP header or the MCP `_meta` field. */
export function paymentFrom(request) {
  const h = request.headers.get("payment-signature");
  return h ? unb64(h) : null;
}

export const paymentFromMeta = (params) =>
  (params && params._meta && params._meta["x402/payment"]) || null;

async function facilitate(env, path, payload, requirements) {
  const c = config(env);
  const url = c.facilitator + path;
  // CDP's facilitator needs a signed JWT per request; every keyless one ignores the header. Minted
  // per call because the token is valid for two minutes, and returns {} when this deployment has no
  // CDP key — so the keyless path is byte-identical to what it was.
  const auth = await cdpAuthHeader(env, "POST", url);
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", ...auth },
    body: JSON.stringify({ x402Version: VERSION, paymentPayload: payload,
                           paymentRequirements: requirements }),
  });
  // THE STATUS, IN THE MESSAGE. This threw a bare "…returned HTTP 401" that charge() flattened to
  // `verification_unavailable`, and a caller — including our own payment check — could not tell an
  // outage from a rejected credential. Those need opposite fixes: one is "wait", the other is "your
  // key is wrong". 401/403 is specifically called out because with an authenticated facilitator it
  // is the single most likely failure and the least self-evident.
  if (!r.ok) {
    const kind = (r.status === 401 || r.status === 403) ? "credential_rejected" : "http_" + r.status;
    throw new Error(path + " " + kind + " (HTTP " + r.status + ")");
  }
  return r.json();
}

/**
 * Verify, run the work, then settle — in that order, and FAIL CLOSED at every step.
 *
 * Ordering is the whole design. Verifying first means we never do the work for a payment that was
 * never valid. Settling AFTER means we never charge for work that threw. And per the MCP transport
 * spec, a settlement that fails after the work ran must NOT return the content: the caller has not
 * paid, and handing it over anyway makes the price advisory.
 *
 * Any error — a refusal, a malformed response, a facilitator that is simply down — denies. An
 * outage must never become a free tier, and it must never become a charge for nothing either.
 */
export async function charge(env, pr, payload, work) {
  const requirements = pr.accepts[0];
  let v;
  try {
    v = await facilitate(env, "/verify", payload, requirements);
  } catch (e) {
    // THE REASON IS THE DIAGNOSTIC. Three failures wear the same word otherwise, and they need
    // three different fixes: a refused credential (your key is wrong), an HTTP error (the
    // facilitator is unhappy), and never reaching it at all (bad URL, DNS, TLS). The last one is
    // what we actually hit — a 401 would have said so, and did not.
    const m = String(e);
    const reason =
      m.includes("credential_rejected") ? "verification_credential_rejected" :
      /http_\d+/.test(m)               ? "verification_" + (m.match(/http_\d+/) || [""])[0] :
                                         "verification_unreachable";
    return { ok: false, reason, detail: m };
  }
  // AN EXPLICIT YES, OR NOTHING. This used to deny only when the facilitator said `isValid: false`
  // or `valid: false` — which means ANY other shape was treated as a pass. A facilitator that
  // answered `{"error": "..."}`, or `{"status":"invalid"}`, or `{}` on some edge, would have had
  // its refusal read as approval and we would have run the work and served the content for free.
  // The stub in the tests returns the exact field the code looked for, so nothing ever showed it.
  //
  // Verified against the live facilitator on 16 Aug 2026: openx402 answers
  // `{"isValid":false,"invalidReason":"…"}`, so the old code happened to be correct FOR THIS ONE.
  // That is luck, and luck is not a thing to leave in the paid path. Now a payment passes only on a
  // positive assertion, and every other answer — including an unrecognised one — denies.
  const said_yes = v && (v.isValid === true || v.valid === true);
  if (!said_yes) {
    return { ok: false,
             reason: (v && (v.invalidReason || v.errorReason)) || "payment_invalid",
             detail: (v && (v.invalidMessage || v.errorMessage)) || undefined };
  }

  const result = await work();

  let s;
  try {
    s = await facilitate(env, "/settle", payload, requirements);
  } catch (e) {
    return { ok: false, reason: "settlement_unavailable", detail: String(e) };
  }
  if (!s || s.success === false) {
    return { ok: false, reason: (s && s.errorReason) || "settlement_failed" };
  }
  return { ok: true, result, settlement: s };
}

export const responseHeader = (settlement) =>
  (settlement ? { "payment-response": b64(settlement) } : {});

// ---- self-test (no network, no credentials) -------------------------------------------------------
// Run: node functions/api/_x402.test.mjs
export const _internals = { b64, unb64 };
