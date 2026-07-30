// node cli/tashan.test.mjs  — pure-logic tests for the CLI (no network, no deps).
import { search, top, find, installSnippets, slugify } from "./tashan.mjs";
import assert from "node:assert";

const rows = [
  { id: "pkg:context7", slug: "context7", name: "context7", kind: "mcp", category: "docs",
    npm_pkg: "@upstash/context7-mcp", source_repo: "upstash/context7", tashan_score: 88, upkeep: 90,
    vitality: "active", expertise: 82, expertise_verdict: "deep", npm_downloads: 137460 },
  { id: "pkg:firecrawl-mcp", slug: "firecrawl-mcp", name: "firecrawl-mcp", kind: "mcp", category: "web",
    npm_pkg: "firecrawl-mcp", source_repo: "mendableai/firecrawl", tashan_score: 75, npm_downloads: 79087, expertise_verdict: "solid" },
  { id: "skill:anthropics/pdf", slug: "skill-anthropics-pdf", name: "pdf", kind: "skill", category: "docs",
    tashan_score: 60, npm_pkg: null, source_repo: "anthropics/skills" },
  { id: "pkg:remote-thing", slug: "remote-thing", name: "remote-thing", kind: "remote",
    tashan_score: 40, npm_pkg: null, source_repo: "acme/remote" },
  { id: "pkg:untrusted", slug: "untrusted", name: "untrusted", kind: "mcp", tashan_score: null },
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
assert.ok(!t.some((x) => x.tashan_score == null), "unscored rows excluded from the leaderboard");
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
  { name: "tavily", npm_pkg: "tavily-mcp", tashan_score: 82, vitality: "active" },
  { name: "deadthing", npm_pkg: "dead-mcp", tashan_score: 20, vitality: "abandoned", gh_archived: 1 },
  { name: "caveman", kind: "skill", tashan_score: null, rated: false },
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

// ---- resolve(): the lookup table, not the board -------------------------------------------------
{
  const { resolve, match, identify } = await import("./doctor.mjs");
  // Shape of web/data/lookup.json: records + a key->index map covering every identity a config yields.
  const lookup = {
    records: [
      { id: "pkg:tavily-mcp", name: "tavily", npm_pkg: "tavily-mcp", tashan_score: 86 },
      { id: "docker:mcp/thinking", name: "thinking", kind: "docker", tashan_score: 40 },
      { id: "py:some-tool", name: "some-tool", kind: "python", tashan_score: 33 },
      { id: "pkg:@scope/thing", name: "thing", npm_pkg: "@scope/thing", tashan_score: 55 },
    ],
    keys: { "tavily-mcp": 0, "tavily": 0, "pkg:tavily-mcp": 0,
            "docker:mcp/thinking": 1, "mcp/thinking": 1, "thinking": 1,
            "py:some-tool": 2, "some-tool": 2,
            "@scope/thing": 3, "thing": 3, "pkg:@scope/thing": 3 },
  };
  const board = [{ id: "pkg:tavily-mcp", name: "tavily", npm_pkg: "tavily-mcp", tashan_score: 86 }];

  assert.strictEqual(resolve({ kind: "npm", id: "tavily-mcp" }, lookup).name, "tavily");
  // THE POINT OF THIS WHOLE CHANGE: kinds the ranked board never carries.
  assert.strictEqual(resolve(identify({ command: "docker", args: ["run", "mcp/thinking"] }), lookup).name,
    "thinking", "a docker image resolves — the board holds no docker rows at all");
  assert.strictEqual(resolve(identify({ command: "uvx", args: ["some-tool"] }), lookup).name,
    "some-tool", "a python package resolves — the board holds no python rows either");
  assert.strictEqual(match(identify({ command: "docker", args: ["run", "mcp/thinking"] }), board), null,
    "...and the board genuinely could not, which is why doctor said 'unmeasured' for measured things");
  // scoped configured bare, and bare configured scoped
  assert.strictEqual(resolve({ kind: "npm", id: "thing" }, lookup).npm_pkg, "@scope/thing");
  assert.strictEqual(resolve({ kind: "npm", id: "@scope/thing" }, lookup).name, "thing");
  assert.strictEqual(resolve({ kind: "npm", id: "not-a-thing" }, lookup), null, "a real miss is still a miss");
  assert.strictEqual(resolve(null, lookup), null, "no item -> null, never a throw");
  assert.strictEqual(resolve({ kind: "npm", id: "x" }, null), null, "no lookup -> null, never a throw");
}
console.log("ok — resolve against the lookup table");

// ---- delisted by the registry: the most serious thing we can tell a user -----------------------
{
  const { assess } = await import("./doctor.mjs");
  const { risks } = await import("./mcp.mjs");
  const gone = { id: "registry:io.bad/thing", name: "thing", registry_status: "deleted" };
  const a = assess({ kind: "npm", id: "thing" }, gone);
  assert.strictEqual(a.level, "alert", "a registry removal is an alert, never a note");
  assert.ok(/REMOVED from the MCP registry/.test(a.notes.map((n) => n.text).join(" ")),
    "and it says so in words a non-expert understands");
  assert.ok(/malware/.test(a.notes.map((n) => n.text).join(" ")),
    "naming the policy's stated reasons is the point — 'delisted' alone means nothing to a user");
  assert.ok(risks(gone).some((r) => /REMOVED from the MCP registry/.test(r)),
    "the agent gets the same warning, so the CLI and the MCP server cannot disagree");
  // A delisted row carries no score by construction. It must still produce the alert, i.e. the verdict
  // must not depend on the row being scored — that was the bug: no score meant no row meant no warning.
  assert.strictEqual(gone.tashan_score, undefined);
  assert.strictEqual(assess({ kind: "npm", id: "thing" }, gone).level, "alert",
    "an unscored delisted row still alerts");
}
console.log("ok — registry removal surfaces as an alert");

// ---- suggest(): what to switch to -------------------------------------------------------------
{
  const { suggest, tokenFrequency, tokensOf, isDying } = await import("./doctor.mjs");
  const pool = [
    { id: "a", name: "mcp-server-sqlite-npx", tashan_score: 38, npm_deprecated: 1 },
    { id: "b", name: "mcp-sqlite", tashan_score: 61 },
    { id: "c", name: "@mokei/mcp-sqlite", npm_pkg: "@mokei/mcp-sqlite", tashan_score: 65 },
    { id: "d", name: "sqlite-but-dead", tashan_score: 90, gh_archived: 1 },
    { id: "e", name: "sqlite-but-worse", tashan_score: 12 },
    { id: "f", name: "totally-unrelated-thing", tashan_score: 99 },
    { id: "g", name: "unscored-sqlite", tashan_score: null },
  ];
  const df = tokenFrequency(pool);
  const dead = pool[0];
  const got = suggest(dead, pool, df);
  assert.deepStrictEqual(got.map((x) => x.cap.id), ["c", "b"],
    "best-measured comparable first");

  // Each of these was a way to produce a recommendation that is worse than saying nothing.
  assert.ok(!got.some((x) => x.cap.id === "d"),
    "never replace a dead thing with another dead thing, however well it scores");
  assert.ok(!got.some((x) => x.cap.id === "e"),
    "never suggest something measured WORSE than what they already have");
  assert.ok(!got.some((x) => x.cap.id === "f"),
    "a high score is not a reason — an unrelated tool is not an alternative");
  assert.ok(!got.some((x) => x.cap.id === "g"),
    "never suggest something we have not measured");
  assert.ok(!got.some((x) => x.cap.id === dead.id), "never suggest itself");

  // Generic words must not create false matches. `mcp`/`server` are in every other name.
  assert.ok(!tokensOf({ name: "mcp-server-thing" }).has("mcp"), "stopwords are dropped");
  assert.ok(!tokensOf({ name: "mcp-server-thing" }).has("server"));
  const generic = [
    { id: "x", name: "alpha-tool", tashan_score: 10, npm_deprecated: 1 },
    ...Array.from({ length: 80 }, (_, i) => ({ id: "g" + i, name: `beta-shared${i}`, tashan_score: 50 })),
  ];
  // "shared" appears in 80 rows; with maxDf 60 it is a category word and must not link anything.
  assert.deepStrictEqual(
    suggest({ id: "y", name: "shared-dead", tashan_score: 5 }, generic, null, { maxDf: 60 }), [],
    "a token common across the corpus is not evidence of the same integration");

  assert.deepStrictEqual(suggest(null, pool), [], "no capability -> no suggestion, never a throw");
  assert.deepStrictEqual(suggest({ id: "z", name: "zzz", tashan_score: 1 }, pool, df), [],
    "nothing comparable returns nothing — 'no confident alternative' is a real answer");

  assert.ok(isDying({ registry_status: "deleted" }), "a registry removal counts as dying");
  assert.ok(isDying({ vitality: "abandoned" }) && isDying({ gh_archived: 1 }));
  assert.ok(!isDying({ vitality: "active" }));
}
console.log("ok — suggest (relevance, never a worse or deader replacement)");

// ---- versionOf(): the pin the user actually wrote -----------------------------------------------
{
  const { versionOf, stripVersion, identify, assess } = await import("./doctor.mjs");
  // stripVersion still discards the version FOR MATCHING; versionOf keeps it for comparison.
  // Only the first existed, which is why nothing could answer "am I running an old release".
  assert.strictEqual(versionOf("tavily-mcp@1.2.3"), "1.2.3");
  assert.strictEqual(versionOf("@playwright/mcp@1.0.0"), "1.0.0", "a scoped package still yields its pin");
  assert.strictEqual(versionOf("@upstash/context7-mcp"), null, "an unpinned scoped package has no pin");
  assert.strictEqual(versionOf("@playwright/mcp@latest"), null, "'latest' is a tag, not a pin — nothing to compare");
  assert.strictEqual(versionOf("plain-package"), null);
  assert.strictEqual(versionOf(""), null);
  assert.strictEqual(versionOf(null), null, "never throws on junk");
  // matching must be unaffected
  assert.strictEqual(stripVersion("tavily-mcp@1.2.3"), "tavily-mcp");
  assert.strictEqual(identify({ command: "npx", args: ["-y", "tavily-mcp@1.2.3"] }).id, "tavily-mcp");
  assert.strictEqual(identify({ command: "npx", args: ["-y", "tavily-mcp@1.2.3"] }).version, "1.2.3");

  const behind = assess({ kind: "npm", id: "x", version: "1.0.0" }, { rated: true, npm_latest_version: "2.1.0" });
  assert.ok(/pinned at 1\.0\.0; 2\.1\.0 is published/.test(behind.notes.map((n) => n.text).join(" ")));
  // A NOTE, not a warning. Pinning is often deliberate, and crying wolf over every minor release is
  // how an audit tool gets uninstalled.
  assert.strictEqual(behind.level, "ok", "being behind is a fact, not an alert");
  const current = assess({ kind: "npm", id: "x", version: "2.1.0" }, { rated: true, npm_latest_version: "2.1.0" });
  assert.ok(!/pinned at/.test(current.notes.map((n) => n.text).join(" ")), "on the latest version, says nothing");
  const unpinned = assess({ kind: "npm", id: "x" }, { rated: true, npm_latest_version: "2.1.0" });
  assert.ok(!/pinned at/.test(unpinned.notes.map((n) => n.text).join(" ")), "no pin means nothing to compare");
  const unknownLatest = assess({ kind: "npm", id: "x", version: "1.0.0" }, { rated: true });
  assert.ok(!/pinned at/.test(unknownLatest.notes.map((n) => n.text).join(" ")),
    "if we do not know the latest version we say nothing, rather than guessing");
}
console.log("ok — version pin vs published latest");

// ---- remote servers resolve by host ------------------------------------------------------------
{
  const { identify, resolve } = await import("./doctor.mjs");
  // The registry keeps a hosted server's endpoint in remotes[].url; ingest read packages[] and threw
  // remotes away, so 0 of 4,215 remote rows carried a URL and identify()'s {kind:remote,id:host} could
  // never match anything. Remote is the second-largest kind we track.
  const lookup = {
    records: [{ id: "registry:ai.exa/mcp", name: "exa", kind: "remote",
                remote_host: "mcp.exa.ai", tashan_score: 71 }],
    keys: { "registry:ai.exa/mcp": 0, "exa": 0, "mcp.exa.ai": 0, "ai.exa/mcp": 0 },
  };
  const item = identify({ url: "https://mcp.exa.ai/mcp" });
  assert.strictEqual(item.kind, "remote");
  assert.strictEqual(item.id, "mcp.exa.ai", "a URL is reduced to its host");
  assert.strictEqual(resolve(item, lookup).name, "exa", "and the host is a lookup key");
  // port and path must not defeat it
  assert.strictEqual(resolve(identify({ url: "https://mcp.exa.ai/v1/sse?k=1" }), lookup).name, "exa");
  assert.strictEqual(resolve(identify({ url: "https://other.example.com/mcp" }), lookup), null,
    "an unknown host is still a clean miss");
}
console.log("ok — remote servers resolve by host");

// ---- licence storage: precedence and the --forget trap -----------------------------------------
// A key that only lives in an env var is re-typed every shell and gone on a new machine, which is
// the single most likely reason a paying customer concludes the product is broken.
import { keyPath, storedKey, resolveKey, parseArgs } from "./tashan.mjs";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
{
  const sandbox = mkdtempSync(join(tmpdir(), "tashan-key-"));
  process.env.XDG_CONFIG_HOME = sandbox;
  assert.ok(keyPath().startsWith(sandbox), "XDG_CONFIG_HOME is honoured");
  assert.strictEqual(storedKey(), null, "no key stored yet reads as null, never a throw");
  assert.strictEqual(resolveKey({}), null, "and resolves to nothing");

  mkdirSync(join(sandbox, "tashan"), { recursive: true });
  writeFileSync(keyPath(), "from_disk\n");
  assert.strictEqual(storedKey(), "from_disk", "trailing newline is trimmed");
  assert.strictEqual(resolveKey({}), "from_disk", "the stored key is used with no env var");

  process.env.TASHAN_KEY = "from_env";
  assert.strictEqual(resolveKey({}), "from_env", "env beats the file — CI and one-off checks");
  assert.strictEqual(resolveKey({ key: "from_flag" }), "from_flag", "--key beats everything");
  delete process.env.TASHAN_KEY;

  // --forget must be a parsed flag. Unparsed it lands in _ and `activate --forget` would happily
  // try to store the literal string "--forget" as the licence.
  const a = parseArgs(["activate", "--forget"]);
  assert.strictEqual(a.forget, true, "--forget parses as a flag");
  assert.deepStrictEqual(a._, ["activate"], "...and never as the key itself");
  console.log("ok — licence storage (precedence, trimming, --forget)");
}
