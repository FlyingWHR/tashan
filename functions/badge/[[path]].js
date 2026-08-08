// Cloudflare Pages Function — GET /badge/<slug>.svg : the embeddable badge, rendered on demand.
//
// WHY THIS IS NOT A FILE ANY MORE. gen_badges.py wrote one .svg per scored capability. That is a file
// count that grows with the corpus, and Cloudflare Pages refuses ANY deployment over 20,000 files —
// at 6,453 badges the site reached 21,782 and could not be published at all. Not degraded: refused.
// Capping badges by score bought exactly one release; 4,684 discovered npm packages are still
// unenriched and each one scores as it is enriched.
//
// A badge is a pure function of (score, verdict), so it does not need to be a file. This renders from
// /data/badges.json — one artifact instead of thousands — and /badge/* already carries a 1h edge
// cache, so origin hits are rare even though READMEs are the highest-traffic surface we have.
//
// THE OUTPUT MUST STAY BYTE-IDENTICAL to pipeline/gen_badges.py::badge(). These are two
// implementations of one concept, which is the failure this codebase has hit six times; here it would
// silently change the artwork inside other people's READMEs. tests/test_badge_parity.mjs renders both
// and diffs them, and fails on any difference.

// Must match VCOLOR in pipeline/gen_badges.py exactly — two renderers, one artifact, and the
// blast radius is other people's READMEs. `wrapper` and `slop` were retired: a shim is a KIND
// of artifact and not a documentation grade, and "slop" was an accusation a README read
// cannot support.
const VCOLOR = { deep: "#5cf0c0", solid: "#34e0a0", thin: "#8a8a93" };
const MARK = '<g transform="translate(7,4.2) scale(0.38)">' +
  '<path d="M17 4 L23 10 L29 22 L18 28 L5 24 L4 13 Z" fill="#34e0a0"/>' +
  '<path d="M17 4 L4 13 L14 15 Z" fill="#5cf0c0"/>' +
  '<path d="M17 4 L23 10 L29 22 L18 28 L14 15 Z" fill="#1f9e78"/></g>';
const CW = 6.6;
const MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace";

function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

// Mirror of gen_badges.py::badge(). Python's round() is banker's rounding and JS's is half-up, but
// len*6.6+16 can only ever land on .0/.2/.4/.6/.8 — never the .5 where they disagree — so Math.round
// is exact here. test_badge_parity sweeps every width the corpus actually produces.
export function badge(trust, verdict) {
  const left = "  tashan";
  const rightScore = String(Math.trunc(trust));
  const right = rightScore + (verdict ? "  " + verdict : "");
  const lw = Math.round(left.length * CW + 16);
  const rw = Math.round(right.length * CW + 16);
  const W = lw + rw, H = 20;
  const vcol = VCOLOR[verdict] || "#34e0a0";
  const rtext = verdict
    ? `<tspan fill="#34e0a0">${rightScore}</tspan><tspan fill="#5b5b63">  ·  </tspan><tspan fill="${vcol}">${esc(verdict)}</tspan>`
    : `<tspan fill="#34e0a0">${rightScore}</tspan>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" role="img" aria-label="tashan: ${rightScore} ${esc(verdict || "")}">
<rect width="${W}" height="${H}" rx="4" fill="#09090b"/>
<rect width="${lw}" height="${H}" rx="4" fill="#18181b"/>
<rect x="${lw - 4}" width="4" height="${H}" fill="#18181b"/>
<rect x="${lw}" width="${rw}" height="${H}" rx="4" fill="#0d0d10"/>
<rect x="${lw}" width="4" height="${H}" fill="#0d0d10"/>
<line x1="${lw}" y1="3" x2="${lw}" y2="17" stroke="rgba(233,162,59,.35)"/>
${MARK}<text x="21" y="14" font-family="${MONO}" font-size="11" font-weight="600"><tspan fill="#ededf0">tashan</tspan></text>
<text x="${lw + 8}" y="14" font-family="${MONO}" font-size="11" font-weight="600">${rtext}</text>
</svg>`;
}

// Cached per isolate. Workers reuse an isolate across many requests, so the map is fetched on cold
// start and then held — the 250 KB is a cold-start cost, never a per-request one.
let MAP = null;

async function loadMap(origin) {
  if (MAP) return MAP;
  const r = await fetch(new URL("/data/badges.json", origin), { cf: { cacheTtl: 3600 } });
  if (!r.ok) throw new Error("badges.json " + r.status);
  MAP = await r.json();
  return MAP;
}

const SVG_HEADERS = {
  "content-type": "image/svg+xml; charset=utf-8",
  // Matches the static era's _headers rule so embeds keep the same caching behaviour.
  "cache-control": "public, max-age=3600",
  "access-control-allow-origin": "*",
};

export async function onRequestGet({ request, params }) {
  const seg = Array.isArray(params.path) ? params.path.join("/") : String(params.path || "");
  const slug = seg.replace(/\.svg$/, "");
  if (!slug) return new Response("not found", { status: 404 });
  let map;
  try {
    map = await loadMap(new URL(request.url).origin);
  } catch (e) {
    // A badge lives in someone else's README. If our data is unreachable, a 502 renders as a broken
    // image on their page — better to say nothing loudly than to invent a score.
    return new Response("badge data unavailable", { status: 502, headers: { "cache-control": "no-store" } });
  }
  const row = map[slug];
  if (!row) {
    // UNKNOWN, not zero. A capability we do not rank must never be handed a badge reading 0 — that is
    // a measurement we never made, embedded in a stranger's README.
    return new Response("no badge for this capability", { status: 404, headers: { "cache-control": "public, max-age=300" } });
  }
  return new Response(badge(row[0], row[1] || null), { headers: SVG_HEADERS });
}
