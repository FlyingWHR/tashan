// node cli/tashan.test.mjs  — pure-logic tests for the CLI (no network, no deps).
import { search, top, find, installSnippets, slugify } from "./tashan.mjs";
import assert from "node:assert";

const rows = [
  { id: "pkg:context7", slug: "context7", name: "context7", kind: "mcp", category: "docs",
    npm_pkg: "@upstash/context7-mcp", source_repo: "upstash/context7", trust: 88, maintenance: 90,
    vitality: "active", expertise: 82, expertise_verdict: "deep", npm_downloads: 137460 },
  { id: "pkg:firecrawl-mcp", slug: "firecrawl-mcp", name: "firecrawl-mcp", kind: "mcp", category: "web",
    npm_pkg: "firecrawl-mcp", source_repo: "mendableai/firecrawl", trust: 75, npm_downloads: 79087, expertise_verdict: "solid" },
  { id: "skill:anthropics/pdf", slug: "skill-anthropics-pdf", name: "pdf", kind: "skill", category: "docs",
    trust: 60, npm_pkg: null, source_repo: "anthropics/skills" },
  { id: "pkg:remote-thing", slug: "remote-thing", name: "remote-thing", kind: "remote",
    trust: 40, npm_pkg: null, source_repo: "acme/remote" },
  { id: "pkg:untrusted", slug: "untrusted", name: "untrusted", kind: "mcp", trust: null },
];

// search: exact > prefix > substring; ranked
let r = search(rows, "context7");
assert.strictEqual(r[0].slug, "context7", "exact name wins");
r = search(rows, "fire");
assert.strictEqual(r[0].slug, "firecrawl-mcp", "prefix match");
r = search(rows, "docs");
assert.ok(r.some((x) => x.slug === "context7"), "category match included");
assert.strictEqual(search(rows, "zzzznope").length, 0, "no false matches");

// top: trust-ranked, drops null-trust, category filter
let t = top(rows);
assert.strictEqual(t[0].slug, "context7", "highest trust first");
assert.ok(!t.some((x) => x.trust == null), "null-trust excluded");
assert.deepStrictEqual(top(rows, "web").map((x) => x.slug), ["firecrawl-mcp"], "category filter");

// find: by slug, name, pkg, fuzzy
assert.strictEqual(find(rows, "context7").slug, "context7");
assert.strictEqual(find(rows, "@upstash/context7-mcp").slug, "context7", "by npm pkg");
assert.strictEqual(find(rows, "firecrawl").slug, "firecrawl-mcp", "fuzzy substring");

// install snippets — must match the site's installBlock() shapes
let s = installSnippets(rows[0], null);
assert.strictEqual(s[0].client, "claude");
assert.strictEqual(s[0].cmd, "claude mcp add context7 -- npx -y @upstash/context7-mcp", "claude one-liner matches site");
assert.ok(s.find((x) => x.client === "cursor").cmd.includes('"@upstash/context7-mcp"'), "cursor json snippet");
assert.strictEqual(installSnippets(rows[0], "npx")[0].cmd, "npx -y @upstash/context7-mcp", "client filter");

// skill install
let sk = installSnippets(rows[2], null);
assert.ok(sk[0].cmd.startsWith("cp -r pdf ~/.claude/skills/"), "skill copies into skills dir");

// remote (no npm) → guidance, never a bogus npx
let rm = installSnippets(rows[3], null);
assert.strictEqual(rm[0].client, "remote");
assert.ok(!rm[0].cmd.includes("npx"), "remote has no fake npx command");

assert.strictEqual(slugify("Pkg: Foo/Bar!"), "pkg-foo-bar");

console.log("ok — CLI pure logic (search / top / find / install / slugify)");

// ---- doctor ----------------------------------------------------------------
import { stripVersion, identify, match, assess, collect } from "./doctor.mjs";
const assertEq = (a, b, msg) => assert.deepStrictEqual(a, b, msg);

// stripVersion: the bug that made every pinned server unmatchable. A numeric-only regex missed
// "@latest", so chrome-devtools-mcp@latest never matched chrome-devtools-mcp.
assertEq(stripVersion("chrome-devtools-mcp@latest"), "chrome-devtools-mcp", "strip @latest");
assertEq(stripVersion("@playwright/mcp@latest"), "@playwright/mcp", "strip tag, keep scope");
assertEq(stripVersion("@upstash/context7-mcp"), "@upstash/context7-mcp", "scoped, unversioned, untouched");
assertEq(stripVersion("tavily-mcp@1.2.3"), "tavily-mcp", "strip semver");

assertEq(identify({ command: "npx", args: ["-y", "tavily-mcp@1.0.0"] }).id, "tavily-mcp", "npx identity");
assertEq(identify({ command: "docker", args: ["run", "ghcr.io/x/y"] }).id, "ghcr.io/x/y", "docker identity");
assertEq(identify({ url: "https://mcp.example.com/sse" }).id, "mcp.example.com", "remote identity");
assertEq(identify({}), null, "empty entry -> null");

const ROWS = [
  { name: "tavily", npm_pkg: "tavily-mcp", trust: 82, vitality: "active" },
  { name: "deadthing", npm_pkg: "dead-mcp", trust: 20, vitality: "abandoned", gh_archived: 1 },
  { name: "caveman", kind: "skill", trust: null, rated: false },
];
assertEq(match({ kind: "npm", id: "tavily-mcp" }, ROWS).name, "tavily", "npm match");
assertEq(match({ kind: "skill", id: "caveman" }, ROWS).name, "caveman", "skill match");
assertEq(match({ kind: "npm", id: "nope" }, ROWS), null, "no match -> null");

assertEq(assess({}, null).level, "unknown", "unindexed -> unknown");
assertEq(assess({}, ROWS[0]).level, "ok", "healthy -> ok");
assertEq(assess({}, ROWS[1]).level, "alert", "archived -> alert");
// an unrated row must NOT render as a green tick: we know it exists and nothing about its quality
assertEq(assess({}, ROWS[2]).level, "unrated", "rated:false -> unrated, not ok");

// a malformed config must be reported, never thrown — the tool is needed most when config is broken
const bad = collect([{ client: "X", path: "/fake", key: "mcpServers" }], [],
  () => "{ not json", () => true, () => []);
assertEq(bad.problems.length, 1, "malformed config reported not thrown");
assertEq(bad.found.length, 0, "nothing collected from a broken file");

process.stdout.write("ok — doctor (identity / match / assess / malformed-config safety)\n");

// ---- trend: the paid half of doctor -----------------------------------------------------------
{
  const { trend, withTrend } = await import("./doctor.mjs");
  const S = (o) => ({ tashan_score: o });
  const t = (o, sc = null) => trend(S(o), sc);
  assert.strictEqual(t({ "2026-07-20": 58, "2026-07-21": 55, "2026-07-22": 50, "2026-07-23": 41 }).level, "alert", "a 17-point fall is an alert");
  assert.strictEqual(t({ "2026-07-20": 58, "2026-07-21": 55, "2026-07-22": 50, "2026-07-23": 41 }).direction, "falling", "...and names the drop");
  assert.strictEqual(t({ "2026-07-20": 50, "2026-07-21": 48, "2026-07-22": 45 }).level, "warn", "a 5-point slip is a warn");
  assert.strictEqual(t({ "2026-07-20": 50, "2026-07-21": 50, "2026-07-22": 51 }).level, "ok", "flat is ok");
  assert.strictEqual(t({ "2026-07-20": 40, "2026-07-21": 44, "2026-07-22": 48 }).direction, "recovering", "a rise off a low is 'recovering'");
  // A LOW SCORE IS NOT NEWS; A DROP IS. Something parked at 30 all week is already on the free board.
  assert.strictEqual(t({ "2026-07-20": 30, "2026-07-21": 30, "2026-07-22": 30 }).level, "ok",
    "a steadily LOW score is still just ok — the free board already shows it");
  assert.strictEqual(t({ "2026-07-22": 50 }).direction, "new", "too little history refuses to call a trend");
  assert.strictEqual(trend(null).direction, "new", "no series at all does not throw");
  assert.strictEqual(trend({}).direction, "new", "empty series does not throw");

  const falling = t({ "2026-07-20": 58, "2026-07-21": 50, "2026-07-22": 41 });
  const rising  = t({ "2026-07-20": 40, "2026-07-21": 44, "2026-07-22": 48 });
  assert.strictEqual(withTrend({ level: "ok", notes: [] }, falling).level, "alert", "a fall escalates a clean row");
  // A recovering score must never quiet an archived repository.
  assert.strictEqual(withTrend({ level: "alert", notes: [] }, rising).level, "alert", "a rise never de-escalates an alert");
  assert.strictEqual(withTrend({ level: "warn", notes: [] }, null).level, "warn", "no trend leaves the assessment untouched");

  // ---- scorer versions: never trend across a change of ruler ----
  // The real contamination: pkg:3dstreet-mcp read 43,43,43,43,42,40 and every step down was caused by
  // us rewriting the scorer, not by the capability getting worse.
  const contaminated = { "2026-07-27": 43, "2026-07-28": 42, "2026-07-29": 40, "2026-07-30": 40 };
  const mixed = { "2026-07-27": "s1", "2026-07-28": "s1", "2026-07-29": "s1", "2026-07-30": "s2" };
  assert.strictEqual(t(contaminated, mixed).direction, "new",
    "one point under the current scorer is not a trend — it must refuse, not reach back across the boundary");
  assert.ok(/comparable history/.test(t(contaminated, mixed).text),
    "and it says the history is not comparable, rather than implying none exists");

  // A clean run entirely inside one version trends normally.
  const clean = { "2026-08-01": 58, "2026-08-02": 50, "2026-08-03": 41 };
  const same = { "2026-08-01": "s2", "2026-08-02": "s2", "2026-08-03": "s2" };
  assert.strictEqual(t(clean, same).level, "alert", "within one scorer version a real fall still alerts");

  // Old points are dropped, not blended: the s1 tail must not soften an s2 fall.
  const spanning = { "2026-07-29": 90, "2026-08-01": 58, "2026-08-02": 50, "2026-08-03": 41 };
  const span = { "2026-07-29": "s1", "2026-08-01": "s2", "2026-08-02": "s2", "2026-08-03": "s2" };
  assert.strictEqual(t(spanning, span).days, 3, "only the current version's points are counted");
  assert.strictEqual(t(spanning, span).delta, -17, "the s1 point does not enter the delta");

  // No map (an older endpoint, or a cache miss) must not silently trend a mixed series.
  assert.strictEqual(t(clean, {}).level, "alert", "an empty map falls back to trending what it was given");
}
console.log("ok — trend is scorer-aware");
