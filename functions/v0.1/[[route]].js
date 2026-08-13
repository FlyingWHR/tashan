// Cloudflare Pages Function — GET /v0.1/lookup?name=… and GET /v0.1/search?q=…
//
// WHY THIS EXISTS. The two static feeds answer the wrong shape of question for the common case.
// /v0.1/servers is 5.6 MB and /v0.1/scores is 420 KB, and an agent deciding whether to install ONE
// package had to pull all of it. Inside a tool call that is not merely wasteful — it is the latency
// budget and the context window, and an agent that learns a source is expensive stops reaching for
// it. This answers in a few hundred bytes.
//
// The static files stay exactly as they are: a host mirroring the corpus wants the whole thing, and
// a URL we have published must keep working. This is an addition, not a replacement — /v0.1/servers
// now says in its own `limits` note which one to use.
//
// Reads /v0.1/scores from its own origin (the pattern functions/badge/ already uses) rather than
// binding a store, so there is one source of truth and no build step to keep in step.


// The price, from the one module that owns it — see functions/api/_license.js. Two copies of a
// price is how a score once differed between two of our own surfaces.
import { OFFER } from "../api/_license.js";

// WHAT AN AGENT CANNOT GET HERE, said in the response rather than left to be discovered.
//
// This endpoint is the product's best distribution: every assistant wired to it is a channel,
// and the response is the only place that channel ever reads. It carried the score, the full
// security audit, the methodology, the licence and the caveat — an honest, complete answer — and
// no indication that anything else exists, so an assistant could never tell its human "tashan
// also tracks whether this changes".
//
// The last field is not marketing. Restating the firewall where a MACHINE reads it is the whole
// reason the number is worth citing back to a human.
const PRO = {
  buys: "The score history behind this capability, and `tashan doctor` over your own config — " +
        "which of the servers YOU run gained an advisory, started running an install script, " +
        "or lost its last maintainer.",
  price: OFFER.plans.map(p => `$${p.amount}/${p.period}`).join(" or ") + ", 7 days free",
  start: "https://tashan.sh/pricing.html",
  // The endpoint an agent should actually reach for. A per-capability lookup answers "is this one
  // safe"; an agent maintaining a stack has a LIST, and that question is what we sell.
  kit: {
    endpoint: "POST https://tashan.sh/v0.1/kit",
    body: { task: "<task slug>", client: "claude-code", kit: false },
    free: "The ranked shortlist for a job, and everything excluded, with reasons.",
    paid: "`kit: true` assembles it: versions pinned to the release the advisory scan cleared, and " +
          "a config for your host. We do not sell anyone's content — each pick links to its source.",
  },
  audit: {
    endpoint: "POST https://tashan.sh/v0.1/audit",
    body: { servers: ["<name or id>", "…"], history: false },
    free: "Every risk we hold about every capability you name. No account, no payment.",
    paid: "`history: true` adds the score series and direction of travel. Licence, or per call " +
          "with x402 (github.com/coinbase/x402).",
  },
  free: "Everything in this response is free, needs no account, and stays free. Nothing " +
        "purchasable moves a score, a rank or a listing.",
};
const MAX_LIMIT = 50;
const DEFAULT_LIMIT = 10;
const BASE_HINT = "https://tashan.sh/methodology.html";
// lookup.json carries no licence line of its own; the terms are the same ones /v0.1/* publishes.
const LICENSE = "CC BY 4.0 — attribute tashan (https://tashan.sh).";

// A measurement's caveats have to travel WITH it: a machine consumer cannot ask a follow-up, and a
// bare number invites exactly the reading this project exists to argue against.
const NOTE =
  "tashan score = upkeep and freshness, gated by real adoption. It is NOT a security verdict and " +
  "NOT a measure of whether the capability works. Absence means unmeasured, never bad or unsafe. " +
  "Nothing purchasable moves a score.";

// TWO SOURCES, AND THE SPLIT IS A SAFETY DECISION, not an optimisation.
//
// /v0.1/scores is the ranked, publishable corpus — junk() has already removed from it everything we
// refuse to recommend, including packages OSV's malicious-packages database confirms as malware.
// That is right for SEARCH: "find me something for X" must never surface malware.
//
// It is exactly wrong for LOOKUP. Asking "is mcp-server-fetch safe?" about a package carrying
// MAL-2026-5476 would have answered `measured:false` — "we have no public evidence for it yet" —
// because the row is deliberately absent from the board. The single worst answer this service can
// give, produced by reading the recommendation list to answer a safety question. /data/lookup.json
// is the file that keeps those rows precisely so `doctor` can warn someone already running one, and
// it carries the advisory ids and install-script text besides.
//
// So: we do not RECOMMEND malware, and we do ANSWER about it. Same policy the CLI has always had.
const SRC = {
  scores: { path: "/v0.1/scores", cache: null, at: 0 },
  lookup: { path: "/data/lookup.json", cache: null, at: 0 },
};
const TTL_MS = 5 * 60 * 1000;

async function load(origin, which) {
  const s = SRC[which];
  if (s.cache && Date.now() - s.at < TTL_MS) return s.cache;
  const r = await fetch(origin + s.path, { cf: { cacheTtl: 300, cacheEverything: true } });
  if (!r.ok) throw new Error(which + " " + r.status);
  s.cache = await r.json();
  s.at = Date.now();
  return s.cache;
}

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      // Keyless and cross-origin on purpose — an endpoint an agent has to negotiate for is not one
      // it will call at decision time.
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=300, stale-while-revalidate=86400",
      ...extra,
    },
  });
}

function row(name, v, origin) {
  const [score, vitality, evidence, slug] = v;
  return {
    name,
    tashan_score: score,
    vitality,
    evidence,
    url: slug ? origin + "/capability/" + slug + ".html" : null,
    // The plain-markdown twin, named explicitly. It is the cheapest complete answer we publish and
    // an agent has no way to guess the convention from a JSON body.
    markdown: slug ? origin + "/capability/" + slug + ".md" : null,
  };
}

function detail(r, origin) {
  const slug = r.slug || r.id.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  // Both arrive as JSON STRINGS in lookup.json (build.py stores them as TEXT columns). A parse that
  // throws must degrade to "nothing recorded", never take the whole answer down with it.
  const arr = (s) => { try { return s ? JSON.parse(s) : []; } catch (e) { return []; } };
  const advisories = arr(r.sec_advisories);
  const perms = arr(r.sec_permissions);
  const out = {
    name: r.name, id: r.id, kind: r.kind,
    tashan_score: r.tashan_score ?? null,
    // null vs 0 matters more here than anywhere: a caller that reads a missing score as zero has
    // invented a bad measurement out of our silence.
    rated: r.rated ?? (r.tashan_score != null),
    vitality: r.vitality ?? null,
    deprecated: r.npm_deprecated ? true : undefined,
    archived: r.gh_archived ? true : undefined,
    single_maintainer: r.single_maintainer ? true : undefined,
    // Instruction depth — how well the thing documents itself. null on most rows, and that is stated
    // rather than omitted: an absent field reads to a summariser as "fine".
    expertise: r.expertise_verdict ?? null,
    security: {
      scanned: r.sec_advisory_count !== undefined || !!r.sec_scanned_at,
      scanned_at: r.sec_scanned_at ?? null,
      advisory_count: r.sec_advisory_count ?? 0,
      max_severity: r.sec_max_severity ?? null,
      advisories,
      install_script: r.sec_install_script ?? null,
      // The headline finding of the whole corpus: ~77% of scanned packages carry no attestation
      // tying the tarball to the repo it points at. `null` where we have not scanned — never false,
      // which would assert an absence we never checked for.
      build_provenance: r.sec_scanned_at ? !!r.sec_provenance : null,
      // Read from DECLARED dependencies only. The wording travels with the value because the value
      // is systematically an UNDER-count and a caller cannot know that from the array alone.
      declared_permissions: perms,
      permissions_note:
        "Derived from declared dependencies; nothing is executed. An empty list means 'nothing " +
        "declared', never 'nothing possible' — a server can shell out with built-ins and declare none.",
      can_carry_remote_content: r.sec_scanned_at ? !!r.sec_remote_content : null,
    },
    url: origin + "/capability/" + slug + ".html",
    markdown: origin + "/capability/" + slug + ".md",
  };
  // THE HEADLINE, WHEN THERE IS ONE. An agent skimming a JSON body should not have to notice that
  // max_severity reads "MALICIOUS" three levels down. These rows exist in the lookup precisely
  // because someone may already be running one.
  if (r.sec_max_severity === "MALICIOUS") {
    out.verdict = "DO NOT INSTALL";
    out.verdict_reason =
      "Listed in OSV's malicious-packages database. It is deliberately absent from every tashan " +
      "ranking and recommendation, and kept here only so a tool can warn someone already running it.";
  } else if (r.npm_deprecated || r.gh_archived) {
    out.verdict = "MAINTAINER HAS STOPPED";
    out.verdict_reason = r.npm_deprecated ? "Marked deprecated on npm." : "Its repository is archived.";
  }
  for (const k of Object.keys(out)) if (out[k] === undefined) delete out[k];
  return out;
}

// Ranked, not merely filtered — and the SCORE has to be part of the ranking, not just a tiebreak.
//
// The first version sorted by match tier alone (exact > prefix > substring) and broke ties on the
// score. Shipped, it answered `?q=postgres` by leading with a capability literally named "postgres"
// scoring 11, ahead of @henkey/postgres-mcp-server at 74. An agent asking search for a
// recommendation got the worst option first, which is the same defect as a role stack recommending
// a 55 over a 93.
//
// `lookup` is the endpoint for "I know the exact name, tell me about it". `search` answers "what
// should I use for this", so it must rank on fitness to recommend. Weighting is the pattern already
// swept in cli/mcp.mjs against ten judged phrases — relevance stays in charge (a strictly better
// match still wins) while the measurement decides between comparable matches, and an exponent of
// 1.5 was the sweep's answer there.
const TIER = { exact: 4, bareExact: 3, prefix: 2, substring: 1 };

function tier(q, name) {
  const n = name.toLowerCase();
  if (n === q) return TIER.exact;
  const bare = n.replace(/^@[^/]+\//, "");            // @scope/name — people search the bare name
  if (bare === q) return TIER.bareExact;
  if (n.startsWith(q) || bare.startsWith(q)) return TIER.prefix;
  if (n.includes(q)) return TIER.substring;
  return 0;
}

function relevance(q, name, score) {
  const t = tier(q, name);
  if (!t) return 0;
  // An unrated capability is not scored 0 — that would bury it below everything. It sits where a
  // middling measured one would, because "we have not measured this" is not "this is bad".
  const s = (score == null ? 45 : score) / 100;
  return t * Math.pow(s, 1.5);
}

export async function onRequestGet({ request, params, next }) {
  const url = new URL(request.url);
  const origin = url.origin;
  const route = (Array.isArray(params.route) ? params.route.join("/") : String(params.route || ""))
    .replace(/\/+$/, "");

  // `servers` and `scores` are STATIC FILES under the same prefix, and a Pages Function wins the
  // route over an asset — so without this, mounting here would have taken both published endpoints
  // off the air. `next()` is the runtime's fall-through to the asset; `fetch(request)` is NOT a
  // substitute, it re-enters this same Function and loops until the request dies.
  if (route !== "lookup" && route !== "search") {
    const r = await next();
    // AND RE-ASSERT THE HEADERS. web/_headers gives /v0.1/* its JSON content-type and CORS, and
    // those files are EXTENSIONLESS — without the header they are served as octet-stream and an
    // agent gets a download instead of a body it can parse. _headers is documented as not applying
    // to Function responses (see functions/badge/), and a response that arrives through next() is
    // ambiguous enough that it is not worth finding out in production: setting them here is a no-op
    // if the platform already did it, and saves both published feeds if it did not.
    if (r.ok && (route === "scores" || route === "servers")) {
      const h = new Headers(r.headers);
      h.set("content-type", "application/json; charset=utf-8");
      h.set("access-control-allow-origin", "*");
      if (!h.has("cache-control")) h.set("cache-control", "public, max-age=900, stale-while-revalidate=86400");
      return new Response(r.body, { status: r.status, headers: h });
    }
    return r;
  }

  let data;
  try {
    data = await load(origin, route === "lookup" ? "lookup" : "scores");
  } catch (e) {
    // Never invent an answer about whether software is safe. Say the measurement is unavailable.
    return json({ error: "measurement data unavailable", detail: String(e) }, 502,
                { "cache-control": "no-store" });
  }

  if (route === "lookup") {
    const name = (url.searchParams.get("name") || "").trim();
    if (!name) return json({ error: "pass ?name=<package or capability name>" }, 400);
    const meta = { generated_at: data.generated_at, scorer: data.scorer,
                   method: BASE_HINT, license: LICENSE, note: NOTE, pro: PRO };
    const keys = data.keys || {};
    // The key map is indexed by BOTH the bare name and the prefixed id, so `tavily-mcp` and
    // `pkg:tavily-mcp` both resolve — an agent holding either should not have to know which.
    const i = keys[name] ?? keys[name.replace(/^npm:/, "")] ?? keys["pkg:" + name];
    if (i === undefined) {
      // 200, not 404. "We have not measured this" is a real and useful answer, and a 404 reads to a
      // caller as a broken endpoint — which is how a source stops getting called.
      return json({ name, measured: false, ...meta,
                    hint: "Not in the tracked corpus. That is not a finding about the package — it " +
                          "means we have no public evidence for it yet. Request one: " +
                          origin + "/requests.html" });
    }
    return json({ ...detail(data.records[i], origin), measured: true, ...meta });
  }

  const map = data.scores || {};
  const meta = {
    generated_at: (data.metadata || {}).generated_at,
    method: BASE_HINT,
    license: (data.metadata || {}).license,
    note: NOTE,
    pro: PRO,
  };
  const q = (url.searchParams.get("q") || "").trim().toLowerCase();
  if (!q) return json({ error: "pass ?q=<query>" }, 400);
  let limit = parseInt(url.searchParams.get("limit") || DEFAULT_LIMIT, 10);
  if (!Number.isFinite(limit) || limit < 1) limit = DEFAULT_LIMIT;
  limit = Math.min(limit, MAX_LIMIT);

  const hits = [];
  for (const name in map) {
    const rel = relevance(q, name, map[name][0]);
    if (rel > 0) hits.push([-rel, -(map[name][0] || 0), name]);
  }
  // Descending relevance, then descending score, then name — so the order is total and identical
  // between runs. An unstable ordering on a recommendation endpoint means two agents asking the
  // same question get different first answers.
  hits.sort((a, b) => a[0] - b[0] || a[1] - b[1] || (a[2] < b[2] ? -1 : 1));
  const shown = hits.slice(0, limit);
  return json({
    query: q,
    count: hits.length,
    results: shown.map(([, , name]) => row(name, map[name], origin)),
    ...meta,
    ...(hits.length > shown.length
      ? { truncated: `showing ${shown.length} of ${hits.length}; pass &limit= up to ${MAX_LIMIT}` }
      : {}),
  });
}
