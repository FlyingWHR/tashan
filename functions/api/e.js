// Cloudflare Pages Function — POST /api/e : tashan's first-party analytics collector.
//
// Writes one row per event to the Analytics Engine dataset bound as TASHAN_AE (free, serverless,
// SQL-queryable via the CF API). No cookies set, no IP stored, no PII. If the binding is absent
// (e.g. not yet configured), it still 204s so the client beacon never errors. See docs/ANALYTICS.md
// for the one-step activation and the example queries.

// Pure event → Analytics-Engine data point. Exported for the test; clamps every field so a hostile
// or oversized beacon can't bloat a row (AE caps blobs at 5 KB total / 20 blobs).
export function toDataPoint(ev, cf) {
  ev = ev || {}; cf = cf || {};
  var s = function (v, n) { return String(v == null ? "" : v).slice(0, n); };
  return {
    indexes: [s(ev.e, 32)],            // event name = sampling index
    blobs: [
      s(ev.e, 32),                     // 1 event  (pageview | copy | outbound | conav | search | …)
      s(ev.p, 128),                    // 2 path
      s(ev.r, 64),                     // 3 referrer host (no full URL)
      s(ev.k, 128),                    // 4 context key (slug / outbound host / copy target)
      s(ev.v, 128),                    // 5 value (data-src label, query, …)
      s(ev.w, 4),                      // 6 viewport bucket (sm|md|lg)
      s(cf.country, 2),                // 7 country (coarse, from CF edge — no IP)
      s(ev.s, 16)                      // 8 session id (in-memory, per-visit only)
    ],
    doubles: [1]                       // count
  };
}

export async function onRequestPost({ request, env }) {
  var ev;
  try { ev = await request.json(); } catch (_) { return new Response(null, { status: 204 }); }
  if (!ev || typeof ev.e !== "string") return new Response(null, { status: 204 });
  try {
    if (env.TASHAN_AE) env.TASHAN_AE.writeDataPoint(toDataPoint(ev, request.cf || {}));
  } catch (_) { /* a beacon must never fail loudly */ }
  return new Response(null, { status: 204, headers: { "cache-control": "no-store" } });
}
