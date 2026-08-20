// Demand signal for the paid endpoints — including, especially, the failures.
//
// WHY THIS EXISTS. Nothing recorded a 402 being served or a payment being refused. An agent could
// find a priced endpoint, decide it wanted the answer, attempt to pay, fail, and leave — and we
// would have learned nothing at all. The whole funnel showed "0 revenue", which is true and useless:
// it cannot tell "nobody came" from "eleven came and every one of them failed at the same step".
//
// A FAILED PAYMENT IS THE MOST VALUABLE EVENT THIS SERVICE CAN RECORD. Revenue tells you something
// worked. A refusal tells you somebody WANTED it and names the thing standing in the way, which is
// the only signal that says what to fix. At zero customers it is the only demand signal that exists.
//
// The reason is the payload. These are not interchangeable:
//
//   quoted                          somebody hit a priced endpoint and did not pay. Interest.
//   attempted                       a PAYMENT-SIGNATURE arrived. Real intent, wallet and all.
//   failed:invalid_*                their signature or funds. Their side — but still demand.
//   failed:verification_credential_rejected   OUR key is wrong. Every payment fails. Fix now.
//   failed:verification_unreachable OUR facilitator URL is wrong. Same.
//   settled                         money.
//
// Two of those five mean the rail is broken on our side and no caller can ever succeed, which is
// exactly the state we shipped in for a day without knowing.
//
// SERVER-SIDE, so no ad-blocker suppresses it and no beacon is lost — the same reasoning as
// /api/buy. And with the same exclusion: our own checker must never appear, because a metric your
// monitoring inflates manufactures the number you would most like to see. That already happened
// once here, producing 43 checkouts nobody made.

// OUR OWN TRAFFIC, BY DECLARED USER-AGENT. `tashan-payment-check` is what check_payments.py sends.
// `tashan-selfcheck` is the marker every OTHER diagnostic must carry — added after five of the six
// "agent quoted a price" events in the first week turned out to be my own curl probes
// (tashan-live-verify, tashan-bazaar-compliance). Having an exclusion and then not using it is the
// same as not having one: it manufactured the exact demand signal this file exists to measure.
//
// A REAL CLIENT MUST NEVER MATCH THESE. `tashan-cli` is our shipped CLI and its traffic is genuine
// demand, so the markers are deliberately not "tashan".
const SELF = ["tashan-payment-check", "tashan-selfcheck"];

/** One row per demand event. Never throws — telemetry must not cost a sale, or a refusal. */
export function demand(env, request, stage, resource, reason) {
  try {
    if (!env || !env.TASHAN_AE) return;
    const ua = (request && request.headers && request.headers.get("user-agent")) || "";
    if (SELF.some((m) => ua.includes(m))) return;
    env.TASHAN_AE.writeDataPoint({
      indexes: ["x402"],
      blobs: [
        "x402",                                        // 1 event family
        String(resource || "").slice(0, 128),          // 2 which priced resource
        "",                                            // 3 referrer host — meaningless for agents
        String(stage || "").slice(0, 32),              // 4 quoted | attempted | failed | settled
        String(reason || "").slice(0, 128),            // 5 WHY, which is the whole point
        "",                                            // 6 viewport — not a browser
        (request && request.cf && request.cf.country) || "",
        // The user-agent, TRUNCATED AND UNLINKED. An agent's UA is how we learn which client is
        // asking (a Claude Code host, a bespoke script, a crawler). It is not a person, carries no
        // identifier, and is capped so a hostile one cannot bloat a row.
        ua.slice(0, 64),
      ],
      doubles: [1],
    });
  } catch (_) { /* a metric must never break the thing it measures */ }
}

export const _SELF = SELF;
