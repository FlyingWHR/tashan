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
     a.amount === "10000" && typeof a.amount === "string",
     "0.01 USDC at 6 decimals; a float here loses money to rounding");
  // THE TWO HALVES OF A PRICE MUST NEVER DRIFT. `usd` is what every human-readable surface quotes
  // and `atomic` is what the caller actually signs for — nothing recomputes one from the other, so
  // a repricing that edits one and forgets the other silently charges a different amount than the
  // page advertises. That is exactly the mistake the 18 Aug repricing nearly made.
  for (const [key, p] of Object.entries(PRICED)) {
    ok(`${key}: usd and atomic agree`,
       String(Math.round(p.usd * 1e6)) === p.atomic,
       `usd ${p.usd} implies ${Math.round(p.usd * 1e6)}, atomic says ${p.atomic}`);
  }
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
  // VERIFICATION MUST REQUIRE AN EXPLICIT YES. The old code denied only on `isValid: false` or
  // `valid: false`, so ANY other shape was read as approval — the work would run and the paid
  // content would be served for free. Every stub in this file happened to return the exact field
  // the code looked for, which is why 39 tests passed over a paywall that failed OPEN.
  for (const [label, reply] of [
    ["an empty object", {}],
    ["an error shape we do not recognise", { error: "facilitator exploded" }],
    ["a status string instead of a boolean", { status: "invalid" }],
    ["a null body", null],
    ["valid spelled as a string", { isValid: "true" }],
  ]) {
    let ran = 0;
    const out = await withFetch(
      (u) => res(String(u).endsWith("/verify") ? reply : { success: true }),
      () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
    ok(`${label} is a refusal, never a pass`, !out.ok && ran === 0, JSON.stringify(out));
  }
  // …and the positive case still works, so this is a tightening and not a wall.
  let ran = 0;
  const yes = await withFetch(
    (u) => res(String(u).endsWith("/verify") ? { valid: true } : { success: true }),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("an explicit `valid: true` still passes", yes.ok && ran === 1, JSON.stringify(yes));
}
{
  // THE SHAPE THE LIVE FACILITATOR ACTUALLY RETURNS, captured 16 Aug 2026 from openx402 when the
  // receiving address was not registered with it. Everything about our config was correct and every
  // payment would have been refused — so the reason has to survive to the caller, not be flattened
  // into "payment_invalid".
  let ran = 0;
  const out = await withFetch(
    (u) => res(String(u).endsWith("/verify")
      ? { isValid: false, invalidReason: "address_not_registered",
          invalidMessage: "Address 0x813e… is not registered. Register at https://openx402.ai/register" }
      : { success: true }),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("a seller-side refusal never runs the work", !out.ok && ran === 0);
  ok("...and names the reason", out.reason === "address_not_registered");
  ok("...and keeps the message that says how to fix it",
     String(out.detail || "").includes("openx402.ai/register"));
}
{
  let ran = 0;
  const out = await withFetch(
    () => Promise.reject(new Error("facilitator down")),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("a facilitator OUTAGE denies rather than becoming a free tier", !out.ok && ran === 0);
  // Renamed from the catch-all "verification_unavailable": a facilitator we cannot REACH is a
  // different fault from one that refuses our credential or answers 5xx, and on an authenticated
  // facilitator telling them apart is the difference between fixing a URL and rotating a key.
  ok("...and says which step failed", out.reason === "verification_unreachable", out.reason);
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
  // res({}, false) is a 500 here, so the reason now carries the status rather than a catch-all.
  ok("a non-200 from the facilitator denies",
     !out.ok && String(out.reason).startsWith("verification_http_"), out.reason);
}

{
  // AN OUTAGE AND A REJECTED CREDENTIAL NEED OPPOSITE FIXES, so they must not share a word. With an
  // authenticated facilitator (CDP) a 401 is the likeliest failure and the least self-evident: the
  // quote looks perfect, every secret is set, and every payment is refused. Collapsing it into
  // "verification_unavailable" is what made that invisible for a deploy.
  let ran = 0;
  const rejected = await withFetch(
    () => new Response("Unauthorized", { status: 401 }),
    () => charge(LIVE, PR, {}, async () => { ran++; return "PAID DATA"; }));
  ok("a 401 from the facilitator is reported as a REJECTED CREDENTIAL",
     rejected.reason === "verification_credential_rejected", JSON.stringify(rejected));
  ok("...and still never runs the work", ran === 0);
  ok("...and keeps the status for a human", /401/.test(String(rejected.detail)));

  const down = await withFetch(
    () => new Response("boom", { status: 503 }),
    () => charge(LIVE, PR, {}, async () => "PAID DATA"));
  ok("a 503 is reported as an HTTP failure, with the status kept",
     down.reason === "verification_http_503", JSON.stringify(down));

  // AND NEVER REACHING IT AT ALL is its own thing: a bad facilitator URL, DNS, TLS. This is what a
  // live deploy actually returned, and calling it "unavailable" sent me looking at the credential.
  // A FACILITATOR MAY RETURN ITS VERDICT AS A 4xx. openx402 answers an invalid payment 200 with
  // {isValid:false}; CDP answers 400 with the identical body. Verified live 17 Aug 2026 — CDP
  // returned {"invalidReason":"invalid_exact_evm_payload_signature", …} with HTTP 400, and treating
  // that as an outage reported "verification_http_400" to a caller whose signature was simply bad.
  {
    let r2 = 0;
    const verdict = await withFetch(
      () => new Response(JSON.stringify({ isValid: false,
              invalidReason: "invalid_exact_evm_payload_signature",
              invalidMessage: "invalid signature: not for a valid curve point" }),
              { status: 400, headers: { "content-type": "application/json" } }),
      () => charge(LIVE, PR, {}, async () => { r2++; return "PAID DATA"; }));
    ok("a 4xx carrying {isValid:false} is read as a PAYMENT refusal, not an outage",
       verdict.reason === "invalid_exact_evm_payload_signature", JSON.stringify(verdict));
    ok("...and still never runs the work", r2 === 0);
    // A 4xx that is NOT a verdict stays a transport failure.
    const junk = await withFetch(
      () => new Response("<html>gateway error</html>", { status: 400 }),
      () => charge(LIVE, PR, {}, async () => "PAID DATA"));
    ok("a 4xx with no verdict in it is still an HTTP failure",
       String(junk.reason).startsWith("verification_http_"), junk.reason);
  }

  const gone = await withFetch(
    () => { throw new TypeError("fetch failed"); },
    () => charge(LIVE, PR, {}, async () => "PAID DATA"));
  ok("an unreachable facilitator says so, rather than blaming the credential",
     gone.reason === "verification_unreachable", JSON.stringify(gone));
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


// ---------------------------------------------------------------------------------------------
// BAZAAR — being FINDABLE, which is the half that compounds.
//
// The Bazaar is the discovery layer agents search for paid endpoints. A seller is indexed within
// ~30 seconds of their first CONFIRMED SETTLE, and only if that settle carries a declaration and a
// resource to attach it to. We shipped `extensions: {}`, so the first real payment would have
// earned the money and bought no discovery at all.
{
  const pr = paymentRequired(LIVE, "capability-kit", "https://tashan.sh/v0.1/kit");
  ok("the 402 declares the endpoint to the Bazaar", Boolean(pr.extensions && pr.extensions.bazaar),
     JSON.stringify(pr.extensions));
  const b = pr.extensions.bazaar;
  ok("...with the method an agent must use", b.method === "POST", b.method);
  ok("...an input schema, so it can construct a call BEFORE paying", Boolean(b.bodySchema));
  ok("...and a worked output example, not an empty object",
     b.output && b.output.example && Object.keys(b.output.example).length > 0);
  ok("...carrying the same description the price quotes",
     b.description === PRICED["capability-kit"].description);

  const h = paymentRequired(LIVE, "capability-history", "https://tashan.sh/api/history");
  ok("a GET resource declares its query parameters", h.extensions.bazaar.method === "GET"
     && Boolean(h.extensions.bazaar.queryParamsSchema));

  // Unconfigured stays unconfigured: no wallet, no quote, nothing declared.
  ok("nothing is declared when the rail is off",
     paymentRequired({}, "capability-kit", "https://tashan.sh/v0.1/kit") === null);
}
{
  // THE SETTLE MUST NAME THE RESOURCE. Verified separately from verify, because we add it only
  // after verification has passed and only when the client left it out.
  const seen = [];
  const out = await withFetch(
    (u, init) => { seen.push({ u: String(u), body: JSON.parse(init.body) });
                   return res(String(u).endsWith("/verify") ? { isValid: true }
                                                            : { success: true, transaction: "0x1" }); },
    () => charge(LIVE, PR, { x402Version: 2 }, async () => "PAID"));
  ok("payment succeeded", out.ok, JSON.stringify(out));
  const settle = seen.find((c) => c.u.endsWith("/settle"));
  ok("the settle call carries paymentPayload.resource",
     Boolean(settle && settle.body.paymentPayload.resource), JSON.stringify(settle && settle.body));
  const verify = seen.find((c) => c.u.endsWith("/verify"));
  ok("...and verify is sent EXACTLY what the client signed, untouched",
     verify && verify.body.paymentPayload.resource === undefined,
     JSON.stringify(verify && verify.body.paymentPayload));
}
{
  // A client that supplied its own resource keeps it — we never overwrite the caller.
  const seen = [];
  await withFetch(
    (u, init) => { seen.push({ u: String(u), body: JSON.parse(init.body) });
                   return res(String(u).endsWith("/verify") ? { isValid: true } : { success: true }); },
    () => charge(LIVE, PR, { x402Version: 2, resource: { url: "https://client.example/r" } },
                 async () => "PAID"));
  const settle = seen.find((c) => c.u.endsWith("/settle"));
  ok("a resource the client supplied is not overwritten",
     settle.body.paymentPayload.resource.url === "https://client.example/r");
}

console.log(`\nx402: ${n}/${n} passed · all green`);
