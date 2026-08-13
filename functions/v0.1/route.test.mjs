// Tests for GET /v0.1/lookup and /v0.1/search.
//
// The one that matters most is the fall-through. This Function mounts on /v0.1/*, and a Pages
// Function WINS the route over a static asset — so a mistake here does not degrade the new endpoints,
// it takes /v0.1/scores and /v0.1/servers, both published and linked from llms.txt and robots.txt,
// off the air. The first draft called fetch(request) as its fall-through, which re-enters this same
// Function and loops.
//
// Run: node functions/v0.1/route.test.mjs
import assert from "node:assert";
import { onRequestGet } from "./[[route]].js";

// lookup.json's shape: a key map (bare name AND prefixed id) into a records array.
const LOOKUP = {
  generated_at: "2026-08-06T00:00:00Z",
  scorer: "s5",
  keys: { "tavily-mcp": 0, "pkg:tavily-mcp": 0, "mcp-server-fetch": 1, "pkg:mcp-server-fetch": 1,
          "old-thing": 2, "pkg:old-thing": 2, "corrupt-thing": 3, "pkg:corrupt-thing": 3 },
  records: [
    { id: "pkg:tavily-mcp", name: "tavily-mcp", kind: "npm", slug: "pkg-tavily-mcp",
      tashan_score: 86, rated: true, vitality: "active", sec_advisory_count: 0,
      sec_scanned_at: "2026-08-06T00:00:00+00:00", sec_provenance: 0,
      sec_permissions: JSON.stringify(["network", "credentials"]), expertise_verdict: "solid" },
    // Confirmed malware. junk() removes it from every ranking, so it is NOT in /v0.1/scores — and
    // answering "unmeasured" here would be the worst answer this service can give.
    { id: "pkg:mcp-server-fetch", name: "mcp-server-fetch", kind: "pkg",
      sec_advisory_count: 1, sec_max_severity: "MALICIOUS", sec_install_script: "node index.js",
      sec_advisories: JSON.stringify([{ id: "MAL-2026-5476", severity: "MALICIOUS",
                                        summary: "Malicious code in mcp-server-fetch (npm)", fixed: null }]) },
    { id: "pkg:old-thing", name: "old-thing", kind: "npm", slug: "pkg-old-thing",
      tashan_score: 20, rated: true, npm_deprecated: 1, sec_advisory_count: 0 },
    { id: "pkg:corrupt-thing", name: "corrupt-thing", kind: "npm", slug: "pkg-corrupt-thing",
      tashan_score: 55, rated: true, sec_advisory_count: 0, sec_scanned_at: "2026-08-06T00:00:00+00:00",
      sec_permissions: "{not json", sec_advisories: "also not json" },
  ],
};

const SCORES = {
  scores: {
    "@upstash/context7-mcp": [97, "active", "1,112,039 npm downloads/week", "pkg-upstash-context7-mcp"],
    "postgres-mcp": [71, "active", "4,201 npm downloads/week", "pkg-postgres-mcp"],
    "@modelcontextprotocol/server-postgres": [43, "abandoned", "126,507 npm downloads/week",
                                              "pkg-at-modelcontextprotocol-server-postgres"],
    "tavily-mcp": [86, "active", "32,517 npm downloads/week", "pkg-tavily-mcp"],
    // SHIPPED AND WRONG: an exact name match at score 11 led ?q=postgres ahead of a 74, because the
    // first ranking sorted by match tier alone. search answers "what should I use", so the
    // measurement has to be part of the rank, not a tiebreak.
    "postgres": [11, "abandoned", "88 npm downloads/week", "pkg-postgres"],
  },
  metadata: { generated_at: "2026-08-06T00:00:00Z", license: "CC BY 4.0 — attribute tashan" },
};

let fetched = [];
globalThis.fetch = async (u) => {
  const s = String(u);
  fetched.push(s);
  return new Response(JSON.stringify(s.includes("/data/lookup.json") ? LOOKUP : SCORES), { status: 200 });
};

const ctx = (path, { nextImpl } = {}) => ({
  request: new Request("https://tashan.sh" + path),
  params: { route: path.split("?")[0].replace(/^\/v0\.1\//, "").split("/") },
  next: nextImpl || (async () => new Response("STATIC ASSET", { status: 200 })),
});

const body = async (r) => JSON.parse(await r.text());
let n = 0;
const ok = (name, cond, extra = "") => {
  n++;
  assert.ok(cond, name + (extra ? " — " + extra : ""));
  console.log("  ok   " + name);
};

// ---- fall-through -------------------------------------------------------------------------
{
  // If this ever calls fetch() instead of next(), the published feeds die. Assert the mechanism,
  // not just the output: a fetch-based fall-through would also return 200 here.
  let called = 0;
  const r = await onRequestGet(ctx("/v0.1/scores", {
    nextImpl: async () => { called++; return new Response("STATIC ASSET", { status: 200 }); },
  }));
  ok("/v0.1/scores falls through to the static asset", (await r.text()) === "STATIC ASSET");
  ok("fall-through uses next(), not a re-fetch of the same URL", called === 1);
}
{
  const r = await onRequestGet(ctx("/v0.1/servers"));
  ok("/v0.1/servers falls through too", (await r.text()) === "STATIC ASSET");
}
{
  // Both feeds are EXTENSIONLESS files. Without a content-type an agent gets an octet-stream
  // download instead of a parseable body — the reason web/_headers has a /v0.1/* rule at all, and
  // _headers is documented as not applying to Function responses.
  const r = await onRequestGet(ctx("/v0.1/scores", {
    nextImpl: async () => new Response("{}", { status: 200 }),   // asset server sent no content-type
  }));
  ok("a fallen-through feed still declares JSON",
     r.headers.get("content-type") === "application/json; charset=utf-8");
  ok("and stays CORS-open", r.headers.get("access-control-allow-origin") === "*");
}
{
  // Never override what the platform already decided correctly.
  const r = await onRequestGet(ctx("/v0.1/scores", {
    nextImpl: async () => new Response("{}", {
      status: 200, headers: { "cache-control": "public, max-age=42" },
    }),
  }));
  ok("an existing cache-control is left alone", r.headers.get("cache-control") === "public, max-age=42");
}
{
  const r = await onRequestGet(ctx("/v0.1/nope", {
    nextImpl: async () => new Response("not found", { status: 404 }),
  }));
  ok("an unknown /v0.1 path is left entirely to the asset server", r.status === 404);
}

// ---- lookup -------------------------------------------------------------------------------
{
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=tavily-mcp")));
  ok("lookup returns the measurement", d.measured === true && d.tashan_score === 86);
  ok("lookup links the page and the markdown twin",
     d.url === "https://tashan.sh/capability/pkg-tavily-mcp.html" &&
     d.markdown === "https://tashan.sh/capability/pkg-tavily-mcp.md");
  ok("lookup carries the caveat with the number", /NOT a security verdict/.test(d.note));
  ok("lookup carries attribution terms", /CC BY 4.0/.test(d.license));
}
{
  const r = await onRequestGet(ctx("/v0.1/lookup?name=definitely-not-real-xyz"));
  const d = await body(r);
  // 200, deliberately: "unmeasured" is an answer. A 404 reads as a broken endpoint, and a caller
  // that concludes the endpoint is broken stops calling it at all.
  ok("an unmeasured package answers 200 with measured:false", r.status === 200 && d.measured === false);
  ok("and says plainly that this is not a finding about the package",
     /not a finding about the package/.test(d.hint));
}
{
  const r = await onRequestGet(ctx("/v0.1/lookup"));
  ok("lookup without a name is a 400 that says what to pass",
     r.status === 400 && /name=/.test(await r.text()));
}

// ---- the malware case, which is the whole reason lookup reads a different file ---------------
{
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=mcp-server-fetch")));
  // THE BUG THIS EXISTS FOR: reading /v0.1/scores to answer a safety question returned
  // measured:false for a package in OSV's malicious-packages database — "we have no evidence" about
  // confirmed malware, because junk() correctly removes it from the RECOMMENDATION list.
  ok("confirmed malware is answerable, not 'unmeasured'", d.measured === true,
     JSON.stringify(d).slice(0, 120));
  ok("the malware verdict leads, not buried under security.max_severity",
     d.verdict === "DO NOT INSTALL");
  ok("the advisory id is given so the claim is checkable",
     d.security.advisories[0].id === "MAL-2026-5476");
  ok("the install-time command is named", d.security.install_script === "node index.js");
  ok("and it explains why it is absent from every ranking",
     /absent from every tashan ranking/.test(d.verdict_reason));
}
{
  // …and the other half of the policy: we ANSWER about malware, we never RECOMMEND it. Search reads
  // the ranked corpus precisely so a "find me something for X" can never surface it.
  const d = await body(await onRequestGet(ctx("/v0.1/search?q=fetch")));
  ok("search never surfaces malware",
     !d.results.some((r) => r.name === "mcp-server-fetch"),
     JSON.stringify(d.results.map((r) => r.name)));
}
{
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=old-thing")));
  ok("a stopped maintainer is stated as a verdict too", d.verdict === "MAINTAINER HAS STOPPED");
  ok("a low score is still reported rather than suppressed", d.tashan_score === 20);
}
{
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=pkg:tavily-mcp")));
  ok("a prefixed id resolves as well as a bare name", d.measured === true && d.name === "tavily-mcp");
}
{
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=tavily-mcp")));
  // A caller reading a missing score as 0 would have invented a bad measurement out of our silence.
  ok("a clean package carries no invented verdict", d.verdict === undefined);
  ok("security.scanned is stated explicitly", d.security.scanned === true);
  ok("the declared permission surface is returned", Array.isArray(d.security.declared_permissions));
  // The value is systematically an UNDER-count and a caller cannot know that from the array alone.
  ok("…with the caveat that makes it readable",
     /never 'nothing possible'/.test(d.security.permissions_note));
  ok("provenance is reported", d.security.build_provenance === false);
  ok("instruction depth is stated, null included", "expertise" in d);
}
{
  // Unscanned rows must not claim an absence we never checked for.
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=mcp-server-fetch")));
  ok("provenance is null, not false, where nothing was scanned",
     d.security.build_provenance === null);
}
{
  // A malformed JSON column must degrade to "nothing recorded", never take the answer down. The
  // fixture is corrupt from the start rather than mutated mid-run: the Function caches the PARSED
  // object, so editing the fixture afterwards is invisible and the test would pass on a stale copy.
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=corrupt-thing")));
  ok("a corrupt permissions column degrades instead of failing",
     Array.isArray(d.security.declared_permissions) && d.security.declared_permissions.length === 0);
  ok("and the rest of the record still answers", d.tashan_score === 55);
}

// ---- search -------------------------------------------------------------------------------
{
  const d = await body(await onRequestGet(ctx("/v0.1/search?q=postgres")));
  ok("search finds every match", d.count === 3);
  // The exact-name row scores 11 and must NOT lead: a recommendation endpoint whose first answer is
  // the worst option is the same defect as a role stack recommending a 55 over a 93.
  ok("a badly-scoring exact match does not lead a recommendation",
     d.results[0].name === "postgres-mcp",
     JSON.stringify(d.results.map((r) => [r.name, r.tashan_score])));
  // …but relevance still leads: postgres-mcp (71, exact-ish) beats the 43 substring match.
  ok("relevance still outranks raw score",
     d.results[1].name === "@modelcontextprotocol/server-postgres" || d.results[1].name === "postgres",
     JSON.stringify(d.results.map((r) => r.name)));
  ok("the weak match is still returned, not hidden",
     d.results.some((r) => r.name === "postgres"));
  ok("search results carry urls", d.results.every((r) => r.url && r.markdown));
}
{
  const d = await body(await onRequestGet(ctx("/v0.1/search?q=context7")));
  ok("a scoped package is findable by its bare name",
     d.results[0].name === "@upstash/context7-mcp");
}
{
  const d = await body(await onRequestGet(ctx("/v0.1/search?q=mcp&limit=2")));
  ok("limit is honoured and truncation is stated", d.results.length === 2 && !!d.truncated);
}
{
  const d = await body(await onRequestGet(ctx("/v0.1/search?q=mcp&limit=9999")));
  ok("limit is capped rather than obeyed", d.results.length <= 50);
}
{
  const r = await onRequestGet(ctx("/v0.1/search"));
  ok("search without a query is a 400", r.status === 400);
}

// ---- upstream failure ---------------------------------------------------------------------
{
  globalThis.fetch = async () => new Response("nope", { status: 500 });
  // Bust the module-level cache the same way five minutes would.
  const r = await onRequestGet(ctx("/v0.1/lookup?name=whatever-uncached-" + Date.now()));
  // A cached copy is legitimate; what must never happen is inventing an answer about safety.
  const d = await body(r);
  ok("an upstream failure never fabricates a measurement",
     r.status === 502 || d.measured !== undefined,
     "status " + r.status);
}

// ---- the agent API sells, and restates the firewall while doing it ---------------------------
// This endpoint is the product's best distribution: every assistant wired to it is a channel, and
// the response is the only place that channel ever reads. It carried an honest, complete answer and
// no indication that anything else existed, so an assistant could never tell its human that tashan
// tracks whether this changes. The price must be the one the 402 quotes — two copies of a price is
// how a score once differed between two of our own surfaces.
{
  const d = await body(await onRequestGet(ctx("/v0.1/lookup?name=tavily-mcp")));
  ok("lookup tells an agent what a licence adds", d.pro && /history/i.test(d.pro.buys || ""),
     JSON.stringify(d.pro || null));
  ok("...quoting the same monthly and annual price as the 402",
     /\$6\/month/.test(d.pro?.price || "") && /\$50\/year/.test(d.pro?.price || ""),
     d.pro?.price);
  ok("...and restating the firewall where a machine reads it",
     /stays free/i.test(d.pro?.free || "") && /nothing purchasable moves a score/i.test(d.pro?.free || ""),
     d.pro?.free);
  ok("...without displacing the measurement, which is the point of the response",
     d.tashan_score !== undefined && d.security !== undefined);
}

console.log(`\nv0.1 route: ${n}/${n} passed · all green`);
