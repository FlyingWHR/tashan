// Cloudflare Pages Function — GET /capability/<slug>.md : the plain-markdown dossier.
//
// WHY THIS IS NOT 9,013 FILES ANY MORE. Cloudflare Pages refuses ANY deployment over 20,000 files —
// refuses, not degrades. Writing one .md beside each .html made every capability cost two files, and
// the corpus grew 7,365 -> 9,013 in one run. At 18,759 files there were 620 capabilities of runway
// left, so the next full pipeline run would have produced a site that could not be published. The
// same wall was hit once before at 21,782 files, when one .svg per capability forced badges behind
// a Function; this is that move, for the same reason.
//
// THE DOSSIER IS NOT RE-RENDERED HERE. pipeline/prerender.py::markdown() still writes every byte, at
// build time, in Python — it is stored in web/data/md/NN.json and this Function looks it up. A JS
// reimplementation would be a second definition of the dossier, which is the defect this codebase
// has paid for six times (slugify, the install command, prerender vs capability.js). Lookup only.
//
// The .html twins remain real files: they carry inlined data islands and are the canonical URLs.

const SHARDS = 64;

// MUST match md_shard() in pipeline/prerender.py byte for byte. If they diverge, every dossier 404s
// at once. Slugs are [a-z0-9-] by construction, so charCodeAt is ASCII-safe here.
// Math.imul, not `*`: plain multiplication loses precision past 2^53 and would silently disagree
// with Python's exact integer arithmetic for longer slugs.
export function shard(slug, n = SHARDS) {
  let h = 0;
  for (let i = 0; i < slug.length; i++) h = (Math.imul(h, 31) + slug.charCodeAt(i)) >>> 0;
  return h % n;
}

const CACHE = new Map();          // module scope: a warm isolate skips the refetch
const TTL_MS = 5 * 60 * 1000;

async function loadShard(origin, i) {
  const hit = CACHE.get(i);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.d;
  const name = String(i).padStart(2, "0");
  const r = await fetch(`${origin}/data/md/${name}.json`, {
    cf: { cacheTtl: 300, cacheEverything: true },
  });
  if (!r.ok) throw new Error(`shard ${name} ${r.status}`);
  const d = await r.json();
  CACHE.set(i, { d, at: Date.now() });
  return d;
}

export async function onRequestGet({ request, params, next }) {
  const seg = Array.isArray(params.path) ? params.path.join("/") : String(params.path || "");
  // Everything that is not a .md — the .html dossiers above all — is a real file. Fall through to
  // the asset server rather than handling it here; `next()` is the runtime's fall-through and
  // `fetch(request)` is NOT a substitute, it re-enters this Function and loops.
  if (!seg.endsWith(".md")) return next();

  const slug = seg.slice(0, -3);
  if (!slug || !/^[a-z0-9-]+$/.test(slug)) return next();

  const origin = new URL(request.url).origin;
  let map;
  try {
    map = await loadShard(origin, shard(slug));
  } catch (e) {
    // Say the data is unavailable; never serve an empty dossier, which reads to a summariser as a
    // capability with nothing on it rather than as an outage.
    return new Response("dossier data unavailable\n", {
      status: 502,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }

  const body = map[slug];
  if (body === undefined) return next();      // let the asset server 404 it in the site's own voice

  return new Response(body, {
    headers: {
      // Without this a .md downloads instead of rendering, and several crawlers skip an attachment
      // outright — the reason web/_headers carried a /capability/*.md rule when these were files.
      // _headers does not apply to Function responses, so it is set here.
      "content-type": "text/markdown; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=900, stale-while-revalidate=86400",
    },
  });
}
