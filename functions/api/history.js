// Cloudflare Pages Function — GET /api/history?id=<capability id>  : THE first paid endpoint.
//
// Why history is what gets sold, and not a score: every score stays free forever, because a number
// behind a paywall is worth less to everyone including us, and the free endpoints are the
// distribution. What is genuinely not obtainable free is the SERIES — signal_history cannot be
// backfilled by anyone, including us. Miss a day and that day is gone permanently. It is the one
// asset that compounds without further work, and the only thing here a competitor starting today
// cannot have.
//
// It is also honest to charge for on day one: the data already exists (25,925 points and growing),
// unlike watch/alerts, which are still unbuilt and therefore still unsold.

import { keyFrom, validate, activationFrom, deny } from "./_license.js";
import { headOf } from "./_head.js";
import { paymentRequired } from "./_x402.js";
import { demand } from "./_demand.js";

// Bucketing must match bucket_of() in pipeline/push_history.py exactly, or every lookup misses
// silently and a paying customer sees 404. One KV value per capability is ~6,500 writes a night; one
// value for all of it is a 14 MB read by day 90 to answer a question about a single capability.
//
// NOT the first character: every id is `<kind>:<name>`, so `pkg:` and `plugin:` both bucket to "p"
// and 5,150 of 6,530 capabilities land in one shard — 737 KB today, ~11 MB by day 90, which is both
// a slow read and close to KV's 25 MB ceiling. A cheap character sum spreads them evenly instead.
// Deliberately arithmetic a human can verify by hand and that cannot differ between Python and JS:
// no overflow, no hash library, no endianness. It is a shard label, not a security primitive.
// ponytail: 64 shards holds for years; raise the modulus and re-push if a shard ever gets slow.
const SHARDS = 64;
export function bucketOf(id) {
  const s = String(id || "");
  let sum = 0;
  for (let i = 0; i < s.length; i++) sum += s.charCodeAt(i);
  return String(sum % SHARDS);
}

export async function onRequestGet({ request, env }) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) {
    return new Response(JSON.stringify({ error: "pass ?id=<capability id>, e.g. pkg:tavily-mcp" }), {
      status: 400, headers: { "content-type": "application/json" },
    });
  }

  const v = await validate(env, keyFrom(request), activationFrom(request));
  if (!v.ok) {
    demand(env, request, "quoted", "capability-history", v.reason || "");
    return deny(v, paymentRequired(env, "capability-history",
                new URL(request.url).origin + "/api/history"));
  }

  if (!env.TASHAN_KV) {
    return new Response(JSON.stringify({ error: "history store not configured" }), {
      status: 503, headers: { "content-type": "application/json" },
    });
  }
  const shard = await env.TASHAN_KV.get("hist:" + bucketOf(id), "json");
  const series = (shard && shard[id]) || null;
  // date -> scorer version. A consumer that trends across two versions is measuring OUR recalibration,
  // so the map ships with every response and cli/doctor.mjs refuses to compare across it.
  const scorers = (shard && shard._scorers) || {};
  if (!series) {
    return new Response(JSON.stringify({ id, series: null, note: "no history recorded for this id yet" }), {
      status: 404, headers: { "content-type": "application/json" },
    });
  }
  return new Response(JSON.stringify({ id, series, scorers, source: "tashan signal_history", licence: "paid" }), {
    // Private: this is per-customer paid data, so no shared cache may ever hold it.
    headers: { "content-type": "application/json", "cache-control": "private, max-age=60" },
  });
}

// A probe that cannot HEAD this endpoint reports us down. See _head.js.
export const onRequestHead = headOf(onRequestGet);
