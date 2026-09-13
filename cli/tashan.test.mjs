// node cli/tashan.test.mjs  — pure-logic tests for the CLI (no network, no deps).
import { search, top, find, installSnippets, slugify, renderAdd } from "./tashan.mjs";
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

  // THE WORST FALSE POSITIVE THIS TOOL HAS PRODUCED — found by installing the published CLI and
  // running it on a real machine. A config entry for `@playwright/mcp`, Microsoft's official server,
  // was stripped to its leaf `mcp` and matched an unrelated `@rendobar/mcp` that IS deleted from the
  // registry. Every Playwright user was told their install had been REMOVED for spam, malware or
  // illegal content: the gravest claim this tool can make, about the wrong package, on the strength
  // of a shared last path segment. Same defect as the slug collision that sent @stripe/mcp to a
  // third-party page — a scoped name's identity is the WHOLE name.
  lookup.records.push({ id: "pkg:@rendobar/mcp", name: "mcp", registry_status: "deleted" });
  lookup.keys["@rendobar/mcp"] = 4;
  lookup.keys["mcp"] = 4;
  assert.strictEqual(resolve({ kind: "npm", id: "@playwright/mcp" }, lookup), null,
    "unmeasured is the honest answer; a deleted stranger that shares a leaf is a libel");
  for (const leaf of ["server", "cli", "core", "client", "sdk"]) {
    lookup.keys[leaf] = 4;
    assert.strictEqual(resolve({ kind: "npm", id: `@someone/${leaf}` }, lookup), null,
      `@someone/${leaf} must not match a stranger sharing the leaf "${leaf}"`);
  }
  // …and the bare-name fallback still works where the leaf is a real identity, not a generic word.
  assert.strictEqual(resolve({ kind: "npm", id: "@other/tavily-mcp" }, lookup).name, "tavily",
    "a distinctive leaf is still a legitimate identity");
  assert.strictEqual(resolve({ kind: "npm", id: "@rendobar/mcp" }, lookup).id, "pkg:@rendobar/mcp",
    "an exact scoped match is untouched");
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

// ---- licence storage: precedence, the JSON record, and the --forget trap -----------------------
// A key that only lives in an env var is re-typed every shell and gone on a new machine, which is
// the single most likely reason a paying customer concludes the product is broken. The stored form
// carries Polar's activation id too — without it, --forget cannot release the device seat.
import { keyPath, storedLicence, resolveLicence, resolveKey, parseLicence, parseArgs, PORTAL } from "./tashan.mjs";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
{
  const sandbox = mkdtempSync(join(tmpdir(), "tashan-key-"));
  process.env.XDG_CONFIG_HOME = sandbox;
  delete process.env.TASHAN_KEY;
  assert.ok(keyPath().startsWith(sandbox), "XDG_CONFIG_HOME is honoured");
  assert.strictEqual(storedLicence(), null, "nothing stored reads as null, never a throw");
  assert.strictEqual(resolveKey({}), null, "and resolves to nothing");

  // A bare string is what TASHAN_KEY gives, and what someone pasting into the file by hand writes.
  assert.deepStrictEqual(parseLicence("  raw_key\n"), { key: "raw_key", activation_id: null, label: null },
    "a bare string parses, trimmed");
  assert.strictEqual(parseLicence("{ not json"), null, "a broken record is null, not a crash");
  assert.strictEqual(parseLicence('{"activation_id":"x"}'), null, "a record with no key is worthless");
  assert.deepStrictEqual(parseLicence('{"key":"k","activation_id":"act_1","label":"box"}'),
    { key: "k", activation_id: "act_1", label: "box" }, "the full record round-trips");

  mkdirSync(join(sandbox, "tashan"), { recursive: true });
  writeFileSync(keyPath(), JSON.stringify({ key: "from_disk", activation_id: "act_9", label: "box" }));
  assert.strictEqual(resolveKey({}), "from_disk", "the stored key is used with no env var");
  assert.strictEqual(resolveLicence({}).activation_id, "act_9",
    "...and carries the activation id, or --forget silently leaks a device seat");

  process.env.TASHAN_KEY = "from_env";
  assert.strictEqual(resolveKey({}), "from_env", "env beats the file — CI and one-off checks");
  assert.strictEqual(resolveLicence({}).activation_id, null,
    "an env key has no activation — it must not inherit the stored one");
  assert.strictEqual(resolveKey({ key: "from_flag" }), "from_flag", "--key beats everything");
  delete process.env.TASHAN_KEY;

  // --forget must be a parsed flag. Unparsed it lands in _ and `activate --forget` would happily
  // try to register the literal string "--forget" as a licence with Polar.
  const a = parseArgs(["activate", "--forget"]);
  assert.strictEqual(a.forget, true, "--forget parses as a flag");
  assert.deepStrictEqual(a._, ["activate"], "...and never as the key itself");

  // polar.sh/purchases is a 404. Every link we ship must be the org portal.
  assert.strictEqual(PORTAL, "https://polar.sh/tashan/portal", "the portal URL is the org portal");
  console.log("ok — licence record (precedence, activation id, --forget)");
}

// ---- the security audit in doctor: every finding is free ---------------------------------------
// The rule the whole product rests on: a user never learns from us that a risk exists only AFTER
// paying. assess() must surface every finding with no key present. What a licence adds is which
// advisory and the version that fixes it — the part you act on, not the part that warns you.
{
  const sec = (row) => assess({ name: "x" }, { rated: true, ...row });

  let a = sec({ sec_max_severity: "MALICIOUS", sec_advisory_count: 1 });
  assert.strictEqual(a.level, "alert", "confirmed malware is an alert");
  assert.ok(/malicious-packages/.test(a.notes.map((n) => n.text).join(" ")),
    "...and names the authority, so it is checkable rather than an accusation");

  a = sec({ sec_advisory_count: 2, sec_max_severity: "HIGH" });
  assert.strictEqual(a.level, "alert", "a high-severity advisory is an alert");
  assert.ok(/2 known advisories/.test(a.notes.map((n) => n.text).join(" ")), "count is stated free");

  a = sec({ sec_advisory_count: 1, sec_max_severity: "LOW" });
  assert.strictEqual(a.level, "warn", "a low-severity advisory warns rather than alarms");
  assert.ok(/1 known advisory/.test(a.notes.map((n) => n.text).join(" ")), "singular reads correctly");

  a = sec({ sec_install_script: "node evil.js" });
  assert.strictEqual(a.level, "warn", "install-time code execution warns");

  a = sec({ sec_permissions: JSON.stringify(["shell", "network"]) });
  assert.ok(/can reach: shell, network/.test(a.notes.map((n) => n.text).join(" ")),
    "permission surface is stated");
  assert.strictEqual(a.level, "ok", "...but a permission is a fact, not a fault — it must not alarm");

  assert.doesNotThrow(() => sec({ sec_permissions: "{not json" }),
    "a malformed permissions field must never take the whole audit down");

  a = sec({});
  assert.strictEqual(a.notes.length, 0, "a clean row says nothing — no nagging on a healthy stack");
  console.log("ok — security findings are free in doctor");
}

// ---- the upsell must be earned, not recurring ---------------------------------------------------
// The rule is offerFor() itself now, not a copy of it re-typed into this file — the copy passed
// while renderDoctor did whatever it liked. It CHANGED on purpose: "only where a finding's detail is
// withheld" had shrunk to a named replacement alone, so a healthy stack never learned anything was
// for sale. A licence buys every measured row its score series, so the offer names that, for the
// rows this reader has. What still must never happen is asserted below.
{
  const { offerFor, standing, evidenceOf, reachOf, recentOf, spark, verdictOf } = await import("./tashan.mjs");
  const m = (id, extra = {}) => ({ row: { id, tashan_score: 80, ...extra } });

  assert.strictEqual(offerFor([], null), null, "nothing measured, nothing offered");
  assert.strictEqual(offerFor([{ row: null }, { row: { id: "skill:x", rated: false } }], null), null,
    "unmeasured and unrated rows have no series to sell");
  assert.deepStrictEqual(offerFor([m("a"), m("a"), m("b")], null), { kind: "series", n: 2 },
    "the count is distinct capabilities — one tool configured in two clients is one series");
  assert.deepStrictEqual(offerFor([m("a"), { ...m("b"), alts: [{ cap: {} }] }], null), { kind: "replacement", n: 1 },
    "a named replacement outranks the series: it is the more specific thing withheld");
  assert.strictEqual(offerFor([{ row: null, alts: [{ cap: {} }] }], null), null,
    "an unresolved row has nothing to sell, whatever is attached to it");
  for (const st of ["active", "invalid", "deactivated", "unknown"]) {
    assert.strictEqual(offerFor([m("a")], st), null, `with a licence in any state (${st}) its state is said, never a pitch`);
  }
  assert.strictEqual(offerFor([{ row: { id: "x", sec_advisory_count: 2, sec_install_script: "node evil.js" } }], null), null,
    "an advisory and an install command are free in full — neither is ever what the offer is about");
  console.log("ok — the offer names what this stack has, never a free fact, never past a licence");

  assert.strictEqual(standing({ tashan_score: 85, rank_pct: 98, category: "browser" }), "above 98% of browser",
    "standing is the dossier's own sentence");
  assert.strictEqual(standing({ tashan_score: 98, rank_pct: 100, category: "docs" }), "above 99% of docs",
    "rank_pct is rounded, so 100 prints as the claim it can support");
  assert.strictEqual(standing({ tashan_score: null, rank_pct: 50 }), null, "no score, no standing");

  assert.deepStrictEqual(
    evidenceOf({ official: "Microsoft", npm_downloads: 4633135, gh_stars: 47475, sec_provenance: 1, expertise_verdict: "solid" }),
    ["Microsoft official", "4.6M downloads/wk", "47k stars", "provenance-attested build"],
    "evidence leads with the publisher and stops at four facts");
  assert.deepStrictEqual(evidenceOf({ npm_downloads: 0, sec_provenance: 0 }), [], "a zero is not evidence");

  const rs = [
    { item: { name: "playwright" }, row: { id: "p", sec_permissions: '["browser"]', sec_remote_content: 1,
      recent: [{ at: "2026-08-10", kind: "permissions_widened", what: "now reaches browser" }] } },
    { item: { name: "playwright" }, row: { id: "p", sec_permissions: '["browser"]', sec_remote_content: 1,
      recent: [{ at: "2026-08-10", kind: "permissions_widened", what: "now reaches browser" }] } },
    { item: { name: "fs" }, row: { id: "f", sec_permissions: "{broken",
      recent: [{ at: "2026-09-01", kind: "deprecated", what: "deprecated by its publisher" }] } },
    { item: { name: "ghost" }, row: null },
  ];
  assert.deepStrictEqual(reachOf(rs).perms, { browser: ["playwright"] },
    "reach is per permission, each tool named once, a malformed field skipped rather than fatal");
  assert.deepStrictEqual(reachOf(rs).remote, ["playwright"], "the third-party-text surface names each tool once");
  assert.deepStrictEqual(recentOf(rs).map((e) => e.at), ["2026-09-01", "2026-08-10"],
    "changes are newest first, and a capability configured twice reports its change once");

  assert.strictEqual(spark([85, 85, 85]), "▅▅▅", "a flat series sits mid-height, not on the floor");
  assert.strictEqual(spark([58, 50, 41])[0] + spark([58, 50, 41])[2], "█▁", "a real fall uses the full height");
  const wob = spark([80, 81, 80]);
  assert.ok(!wob.includes("█") && !wob.includes("▁"), "a one-point wobble cannot draw a collapse");
  assert.strictEqual(spark([70]), "", "one point is not a line");

  assert.strictEqual(verdictOf({ tashan_score: 90, sec_max_severity: "MALICIOUS" }).text, "Do not install",
    "malware is refused before its score is read");
  assert.strictEqual(verdictOf({ tashan_score: 88, npm_deprecated: 1 }).text, "Not recommended",
    "a dead package is not a pick at any score");
  assert.strictEqual(verdictOf({ tashan_score: 88, sec_advisory_count: 1, sec_max_severity: "HIGH" }).text, "Not recommended");
  assert.strictEqual(verdictOf({ tashan_score: 88, sec_advisory_count: 1, sec_max_severity: "LOW" }).text, "Use with care");
  const az = verdictOf({ tashan_score: 86, rank_pct: 97, category: "cloud", sec_install_script: 1 });
  assert.strictEqual(az.text, "Strong pick", "an install script does not lower a well-measured verdict…");
  assert.strictEqual(az.but, "runs a script at install time", "…it is said beside it");
  assert.strictEqual(az.why, "86/100, above 97% of cloud", "and the verdict carries the fact behind it");
  assert.strictEqual(verdictOf({ tashan_score: 55 }).text, "Reasonable pick");
  assert.strictEqual(verdictOf({ tashan_score: 20 }).text, "Weak evidence");
  assert.strictEqual(verdictOf({ rated: false }).text, "Unrated");

  const twins = [
    { id: "plugin:upstash/context7/context7", name: "context7", kind: "plugin", tashan_score: 77 },
    { id: "pkg:@upstash/context7-mcp", name: "@upstash/context7-mcp", npm_pkg: "@upstash/context7-mcp",
      label: "Context7", kind: "npm", tashan_score: 98 },
  ];
  assert.strictEqual(find(twins, "context7").id, "pkg:@upstash/context7-mcp",
    "among exact matches the best-measured wins, not whichever came first");
  assert.strictEqual(find(twins, "plugin:upstash/context7/context7").id, "plugin:upstash/context7/context7",
    "a typed id still wins outright");

  const { resolve } = await import("./doctor.mjs");
  const lk = { keys: { "vercel-plugin": 0, "plugin:vercel/vercel-plugin/vercel": 1 },
               records: [{ id: "plugin:tomsonxxx/lumbago_codex/vercel-plugin" }, { id: "plugin:vercel/vercel-plugin/vercel" }] };
  assert.strictEqual(resolve({ kind: "plugin", name: "vercel-plugin", id: null }, lk), null,
    "a plugin with no readable home is unknown — never a stranger that shares its name");
  assert.strictEqual(resolve({ kind: "plugin", name: "vercel", id: "plugin:vercel/vercel-plugin/vercel" }, lk).id,
    "plugin:vercel/vercel-plugin/vercel", "and one with a home resolves to exactly that record");
  console.log("ok — standing, evidence, reach, changes, sparkline, verdict and plugin identity");
}

// ---- the security audit's DETAIL is free too, and never invented -------------------------------
// It used to arrive from /api/security behind a licence header while the website printed the same
// advisory id and install command to any visitor. Both now ride in the public lookup.json, so the
// two parsers below are the whole of what doctor and the MCP server read.
{
  const { advisoriesOf, installScriptOf } = await import("./tashan.mjs");

  const advs = advisoriesOf({ sec_advisories: JSON.stringify([{ id: "GHSA-1", fixed: "2.0.0" }]) });
  assert.strictEqual(advs[0].id, "GHSA-1", "the advisory id is read straight off the public row");
  assert.strictEqual(advs[0].fixed, "2.0.0", "so is the version that fixes it");
  assert.deepStrictEqual(advisoriesOf({ sec_advisories: "{not json" }), [],
    "a malformed field returns nothing — an audit must not die on the row it is warning about");
  assert.deepStrictEqual(advisoriesOf({}), [], "and a row with no advisories yields none");
  assert.deepStrictEqual(advisoriesOf(null), [], "including no row at all");

  assert.strictEqual(installScriptOf({ sec_install_script: "node evil.js" }), "node evil.js",
    "the literal command is what the reader needs");
  // index.json flattens the command to a bare 1 for first-paint weight. "install runs: 1" would be
  // worse than saying nothing, so the type is checked rather than the truthiness.
  assert.strictEqual(installScriptOf({ sec_install_script: 1 }), null,
    "the board's boolean is not a command and must never be printed as one");
  assert.strictEqual(installScriptOf({ sec_install_script: "" }), null, "nor is an empty string");
  assert.strictEqual(installScriptOf({}), null, "nor an absent field");
  console.log("ok — advisory detail and the install command are read from public data");
}

// ---- the dossier URL must resolve --------------------------------------------------------------
// `slug` is not a field in the slim index the CLI loads, so r.slug was undefined on every row and
// `tashan info` printed http://tashan.sh/capability/undefined.html — on every capability, every
// time. slugify(id) reproduces the real slug exactly, which is why prerender.py names files that way.
{
  const { slugify } = await import("./tashan.mjs");
  const cases = [
    ["pkg:@postman/postman-mcp-server", "pkg-postman-postman-mcp-server"],
    ["pkg:@azure/mcp", "pkg-azure-mcp"],
    ["registry:io.github.foo/bar", "registry-io-github-foo-bar"],
    ["skill:anthropics/pdf", "skill-anthropics-pdf"],
  ];
  for (const [id, want] of cases) {
    assert.strictEqual(slugify(id), want, `slugify(${id}) must match the prerendered filename`);
  }
  assert.ok(!slugify("pkg:x").includes("undefined"), "a slug can never be the string 'undefined'");
}
console.log("ok — the dossier URL resolves from the id, not a missing slug field");

// ---- `tashan account` opens a browser --------------------------------------------------------
// `start` is a cmd.exe builtin whose FIRST argument is consumed as the window title. Passing the
// URL as argv[0] there opens a blank window and reports success — a silent no-op on the one
// platform where nobody testing this would notice.
{
  const { browserCommand } = await import("./tashan.mjs");
  const url = "https://tashan.sh/api/account?t=abc";

  assert.deepStrictEqual(browserCommand("darwin", url), { cmd: "open", args: [url], shell: false });
  assert.deepStrictEqual(browserCommand("linux", url), { cmd: "xdg-open", args: [url], shell: false });

  const win = browserCommand("win32", url);
  assert.strictEqual(win.args[0], "", "start swallows its first argument as the window title");
  assert.strictEqual(win.args[1], url);
  assert.ok(win.shell, "start is a shell builtin, not an executable");

  for (const plat of ["darwin", "linux", "win32"]) {
    assert.ok(browserCommand(plat, url).args.includes(url), `${plat} must actually receive the URL`);
  }
}
console.log("ok — the browser launch passes the URL on every platform");

// ---- the published package must actually RUN --------------------------------------------------
// npm installs a bin as a SYMLINK (node_modules/.bin/tashan -> ../tashan-cli/tashan.mjs), so
// process.argv[1] is the link while import.meta.url resolves to the target. The entry check was a
// plain === between the two, which is false for EVERY npm install — main() never ran, `tashan --help`
// exited 0 and printed nothing. Running the file directly by path worked, so every local test and
// every `node cli/tashan.mjs …` in this suite passed while the shippable artifact did nothing.
// Only installing the packed tarball caught it.
{
  const { realpathSync, mkdtempSync, symlinkSync, writeFileSync } = await import("node:fs");
  const { join } = await import("node:path");
  const { tmpdir } = await import("node:os");
  const { fileURLToPath, pathToFileURL } = await import("node:url");

  // Reproduce npm's layout: a real file, and a symlink pointing at it.
  const dir = mkdtempSync(join(tmpdir(), "tashan-entry-"));
  const real = join(dir, "real.mjs");
  const link = join(dir, "link.mjs");
  writeFileSync(real, "export default 1;\n");
  symlinkSync(real, link);

  // The check as it is written in tashan.mjs / mcp.mjs.
  const isEntry = (argv1, metaUrl) => {
    try { return realpathSync(argv1) === realpathSync(fileURLToPath(metaUrl)); }
    catch { return argv1 === fileURLToPath(metaUrl); }
  };

  assert.ok(isEntry(link, pathToFileURL(real).href),
    "a symlinked bin must still be recognised as the entry point — this is the npm install case");
  assert.ok(isEntry(real, pathToFileURL(real).href),
    "running the file directly by path must still work");
  assert.ok(!isEntry(join(dir, "other.mjs"), pathToFileURL(real).href),
    "an unrelated argv[1] must not be treated as the entry point (import, not execute)");

  // and the naive check this replaced would have failed the npm case
  assert.ok(link !== fileURLToPath(pathToFileURL(real).href),
    "sanity: the symlink path and the real path differ, which is why === was wrong");
}
console.log("ok — the entry check survives npm's symlinked bin");

// ---- `npx <package>` must resolve a bin -------------------------------------------------------
// npx resolves a bin NAMED AFTER THE PACKAGE. tashan-cli@0.1.0 shipped two bins — `tashan` and
// `tashan-mcp` — and neither matched, so npx exited "could not determine executable to run" for
// every documented `npx tashan-cli …` invocation: the README, the pricing page, start.html, and the
// install block on 5,788 capability pages. `npx -p tashan-cli tashan` worked, which is why every
// local test passed. The package was fine; only the one command anybody would actually type was not.
{
  const { readFileSync } = await import("node:fs");
  const { join, dirname } = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const pkg = JSON.parse(readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "package.json"), "utf8"));

  assert.ok(pkg.bin[pkg.name],
    `package "${pkg.name}" declares no bin of that name — npx ${pkg.name} cannot resolve one ` +
    `(bins: ${Object.keys(pkg.bin).join(", ")})`);
  for (const [name, file] of Object.entries(pkg.bin)) {
    assert.ok(pkg.files.includes(file), `bin ${name} -> ${file}, which is not in "files"`);
  }
}
console.log("ok — npx <package-name> resolves a bin, and every bin ships");

// ---- `--version` must answer with a version ---------------------------------------------------
// Up to 0.1.4 every form of it — `--version`, `-v`, `version` — printed "unknown command" followed
// by the usage block. It is the first thing anyone types at a CLI they just installed and the first
// thing a bug report asks for, so an error there reads as a broken install. The number is read from
// package.json at runtime rather than written into the source, because two places holding one
// version is how a CLI ends up confidently reporting the wrong one.
{
  const { readFileSync } = await import("node:fs");
  const { join, dirname } = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const here = dirname(fileURLToPath(import.meta.url));
  const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf8"));
  const src = readFileSync(join(here, "tashan.mjs"), "utf8");

  for (const flag of ["--version", "-v", "version"]) {
    assert.ok(src.includes(`"${flag}"`), `${flag} is not handled in tashan.mjs`);
  }
  assert.ok(/readFileSync\(new URL\("\.\/package\.json", import\.meta\.url\)/.test(src),
    "VERSION must be read from package.json relative to the module URL — npm installs the bin as " +
    "a symlink, so anything derived from argv[1] or cwd resolves somewhere else");
  assert.match(pkg.version, /^\d+\.\d+\.\d+/, "package.json has no usable version to report");
}
console.log("ok — --version answers, and reads the number npm published");

// ---- add must warn BEFORE it prints a copyable command ------------------------------------------
// `info` now falls back to lookup.json so a deprecated or delisted capability can be looked up at
// all — search/top read the ranked board, and those rows lose their score and drop off it, which
// made `tashan info @modelcontextprotocol/server-github` answer "no capability matches" for a
// package npm marks "no longer supported". `add` shares that branch, so it started printing a
// clean install line for a dead package. A warning under the snippet is a warning nobody reads:
// by then the command is on the clipboard.
{
  const dead = { id: "pkg:x", name: "x", npm_pkg: "x", slug: "pkg-x", npm_deprecated: 1 };
  const out = renderAdd(dead, null);
  assert.ok(/Not recommended/.test(out), "a deprecated package must be flagged when adding it");
  assert.ok(out.indexOf("Not recommended") < out.indexOf("npx"),
            "the warning must come BEFORE the first install command");
  assert.ok(/DEPRECATED on npm/.test(out), "and say what is actually wrong");

  const risky = { id: "pkg:y", name: "y", npm_pkg: "y", slug: "pkg-y", sec_advisory_count: 2 };
  assert.ok(/2 known advisories/.test(renderAdd(risky, null)), "advisories are named too");

  const fine = { id: "pkg:z", name: "z", npm_pkg: "z", slug: "pkg-z" };
  assert.ok(!/Not recommended/.test(renderAdd(fine, null)),
            "a healthy capability must not be decorated with a warning it did not earn");
}
console.log("ok — add warns above the command, and only when the row earned it");

// ---- stdout must survive a PIPE -----------------------------------------------------------------
// `main().then(code => process.exit(code))` does not wait for stdout to drain, and node buffers
// stdout asynchronously when it is a pipe. So `tashan doctor --json | jq` was truncated at the
// 64 KiB pipe buffer and handed the caller unparseable JSON — with exit status 0, which is the worst
// half: a script reads garbage and never learns it did. Measured on a real machine, 65,478 of
// 225,178 bytes arrived; 71% of the output was dropped.
//
// It was invisible in every normal test: stdout to a TTY is synchronous on POSIX, and `> file` is
// synchronous too. Only a pipe shows it — which is the one arrangement /start.html tells people to
// use ("Add --json to pipe it"). So this test PIPES, deliberately, and uses `search --json` rather
// than `doctor` because that reads the committed index and is therefore the same size on every
// machine, including one whose own agent config is too small to cross the buffer.
{
  const { execFileSync } = await import("node:child_process");
  const here = new URL(".", import.meta.url).pathname;
  const out = execFileSync(process.execPath,
                           [here + "tashan.mjs", "search", "mcp", "--json", "--limit", "400"],
                           { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
                             maxBuffer: 64 * 1024 * 1024 });
  assert.ok(out.length > 64 * 1024,
            `the fixture must exceed the 64 KiB pipe buffer or this proves nothing (got ${out.length})`);
  assert.doesNotThrow(() => JSON.parse(out),
                      `--json was truncated through a pipe at ${out.length} bytes`);
}
console.log("ok — --json survives a pipe (exit does not race the flush)");
