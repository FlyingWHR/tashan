// node functions/api/_x402.test.mjs
//
// The money path. Every assertion here is about refusing to hand over paid data, because the two
// ways this can be wrong are not symmetric: quoting a price we cannot settle wastes an agent's
// signature, and serving content for a payment that did not clear is simply giving it away.
import assert from "node:assert";
import {
  PRICED, config, configured, paymentRequired, requiredHeader, paymentFrom, paymentFromMeta,
  charge, responseHeader, _internals,
} from "./_x402.js";

let n = 0;
const ok = (name, cond, extra = "") => {
  n++;
  assert.ok(cond, name + (extra ? " — " + extra : ""));
  console.log("  ok   " + name);
};

const LIVE = {
  X402_PAY_TO: "0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
  X402_NETWORK: "eip155:8453",
  X402_ASSET: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  X402_FACILITATOR: "https://facilitator.example/",
};

// ---- dormant until a wallet exists ---------------------------------------------------------------
ok("unconfigured: not configured()", !configured({}));
ok("unconfigured: quotes no accepts at all",
   paymentRequired({}, "capability-history", "https://tashan.sh/api/history") === null);
ok("unconfigured: emits no PAYMENT-REQUIRED header",
   Object.keys(requiredHeader(null)).length === 0);
for (const missing of ["X402_PAY_TO", "X402_NETWORK", "X402_ASSET", "X402_FACILITATOR"]) {
  const env = { ...LIVE };
  delete env[missing];
  ok("partial config is NOT configured (missing " + missing + ")", !configured(env),
     "a price we cannot settle is worse than no price");
}

// ---- the v2 shape, field for field ---------------------------------------------------------------
{
  const pr = paymentRequired(LIVE, "config-audit", "https://tashan.sh/v0.1/audit");
  ok("x402Version is 2", pr.x402Version === 2);
  ok("resource carries url, description and mimeType",
     pr.resource.url && pr.resource.description && pr.resource.mimeType === "application/json");
  const a = pr.accepts[0];
  ok("accepts[0] has every REQUIRED v2 field",
     a.scheme === "exact" && a.network === "eip155:8453" && typeof a.amount === "string"
     && a.asset && a.payTo && typeof a.maxTimeoutSeconds === "number",
     JSON.stringify(a));
  ok("amount is atomic units as a STRING, not a float",
     a.amount === "50000" && typeof a.amount === "string",
     "0.05 USDC at 6 decimals; a float here loses money to rounding");
  ok("no v1 field names leak in (maxAmountRequired is a different generation)",
     !("maxAmountRequired" in a));
  const header = requiredHeader(pr);
  ok("PAYMENT-REQUIRED is base64 of the same object",
     JSON.stringify(_internals.unb64(header["payment-required"])) === JSON.stringify(pr));
}

// ---- prices are one definition -------------------------------------------------------------------
for (const [k, p] of Object.entries(PRICED)) {
  const atomic = String(Math.round(p.usd * 1e6));
  ok(`${k}: atomic units match the USD price`, p.atomic === atomic,
     `${p.usd} USD should be ${atomic} atomic, file says ${p.atomic}`);
  ok(`${k}: says what it sells`, p.description.length > 30);
}

// ---- reading the client's payment ----------------------------------------------------------------
{
  const req = (h) => new Request("https://tashan.sh/x", { headers: h });
  ok("no PAYMENT-SIGNATURE reads as no payment", paymentFrom(req({})) === null);
  ok("a MALFORMED PAYMENT-SIGNATURE reads as no payment, never as a pass",
     paymentFrom(req({ "payment-signature": "!!!not base64!!!" })) === null);
  const payload = { x402Version: 2, payload: { signature: "0xabc" } };
  ok("a well-formed header round-trips",
     JSON.stringify(paymentFrom(req({ "payment-signature": _internals.b64(payload) })))
     === JSON.stringify(payload));
  ok("the MCP transport reads the same payload from _meta['x402/payment']",
     paymentFromMeta({ _meta: { "x402/payment": payload } }) === payload);
  ok("MCP: absent _meta is no payment", paymentFromMeta({}) === null);
}

// ---- charge(): verify -> work -> settle, failing closed at every step -----------------------------
const withFetch = async (impl, fn) => {
  const real = globalThis.fetch;
  globalThis.fetch = impl;
  try { return await fn(); } finally { globalThis.fetch = real; }
};
const res = (obj, okStatus = true) =>
  Promise.resolve({ ok: okStatus, status: okStatus ? 200 : 500, json: async () => obj });
const PR = paymentRequired(LIVE, "capability-history", "https://tashan.sh/api/history");

{
  let ran = 0;
  const out = await withFetch(
    (u) => res(String(u).endsWith("/verify") ? { isValid: true }
                                             : { success: true, transaction: "0xdead" }),
    () => charge(LIVE, PR, {}, async () => { ran++; return { series: [1, 2, 3] }; }));
  ok("happy path: work ran once and the result comes back",
     out.ok && ran === 1 && out.result.series.length === 3);
  ok("settlement is returned for the PAYMENT-RESPONSE header", out.settlement.transaction === "0xdead");
  ok("PAYMENT-RESPONSE is base64 of the settlement",
     _internals.unb64(responseHeader(out.settlement)["payment-response"]).transaction === "0xdead");
}
{
  let ran = 0;
  const out = await withFetch(
    (u) => res(String(u).endsWith("/verify") ? { isValid: false, invalidReason: "insufficient_funds" }
                                             : { success: true }),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("an INVALID payment never runs the work", !out.ok && ran === 0, JSON.stringify(out));
  ok("...and reports the facilitator's reason", out.reason === "insufficient_funds");
}
{
  let ran = 0;
  const out = await withFetch(
    () => Promise.reject(new Error("facilitator down")),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("a facilitator OUTAGE denies rather than becoming a free tier", !out.ok && ran === 0);
  ok("...and says which step failed", out.reason === "verification_unavailable");
}
{
  let ran = 0;
  const out = await withFetch(
    (u) => String(u).endsWith("/verify") ? res({ isValid: true })
                                         : res({ success: false, errorReason: "insufficient_funds" }),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("settlement failure AFTER the work still withholds the content",
     !out.ok && ran === 1 && out.result === undefined,
     "the spec is explicit: do not return the tool's content when settlement failed");
  ok("...and names the reason", out.reason === "insufficient_funds");
}
{
  const out = await withFetch(
    (u) => String(u).endsWith("/verify") ? res({}, false) : res({ success: true }),
    () => charge(LIVE, PR, {}, async () => "PAID DATA"));
  ok("a non-200 from the facilitator denies", !out.ok && out.reason === "verification_unavailable");
}

// ---- the shared refusal carries it, and only when a wallet exists --------------------------------
// deny() is where every paid endpoint refuses. If x402 only reached the audit route, an agent
// hitting /api/history would still see a subscription it cannot buy and nothing it can.
{
  const { deny } = await import("./_license.js");
  const plain = deny({ status: 402, why: "payment required" });
  const pb = await plain.json();
  ok("unconfigured: the refusal is unchanged, with no accepts and no header",
     pb.accepts === undefined && !plain.headers.get("payment-required") && pb.plans.length === 2);

  const pr = paymentRequired(LIVE, "capability-history", "https://tashan.sh/api/history");
  const paid = deny({ status: 402, why: "payment required" }, pr);
  const bb = await paid.json();
  ok("configured: the same refusal gains a spec-shaped accepts",
     bb.x402Version === 2 && bb.accepts[0].payTo === LIVE.X402_PAY_TO);
  ok("...and the PAYMENT-REQUIRED header", Boolean(paid.headers.get("payment-required")));
  ok("...without dropping the subscription option — two ways to pay, not a replacement",
     bb.plans.length === 2 && bb.free && bb.credential.header.startsWith("Authorization"));

  const forbidden = deny({ status: 403, why: "licence expired" }, pr);
  const fb = await forbidden.json();
  ok("a 403 is NOT turned into a payment quote (that caller already paid)",
     forbidden.status === 403 && fb.accepts === undefined && fb.error === "licence expired");
}

console.log(`\nx402: ${n}/${n} passed · all green`);
