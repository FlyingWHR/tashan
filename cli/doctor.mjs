// tashan doctor — audit the agent config you actually have.
//
//   npx tashan doctor            what's installed, what's dead, what's risky
//   npx tashan doctor --json     machine-readable
//
// WHY THIS EXISTS, AND WHY IT IS NOT A REVIEW SITE
// Every other index in this field measures the artifact: is it well-built, well-described, hosted,
// popular on their platform. Nobody answers the question a developer actually has at 2am — *is anything
// in MY stack dead, deprecated, or impersonating something official?* That question needs no traffic, no
// liquidity, and no reviews to be worth answering, which is why it is the right first tool for us and a
// review platform is not: reviews need a crowd we do not have and produce opinion, which is the one
// thing we do not sell.
//
// PRIVACY IS THE PRODUCT, NOT A SETTING. This reads local files and compares them against a public JSON
// index. Nothing is uploaded. There is no account, no key, no beacon, and no opt-out to find — because
// there is nothing to opt out of. If aggregate contribution is ever added it will be a separate, explicit
// command, and the rule in docs/PRIVACY-RULE (below) applies.
//
// THE RULE, if telemetry ever feeds a score: it must be published. The moment tashan scores on data
// only tashan can see, tashan becomes Smithery — a first party asking to be trusted about numbers nobody
// can audit. Public inputs or it does not count toward a score.

import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// Where the clients actually keep their config. Order matters only for reporting.
export function configLocations(home = homedir(), cwd = process.cwd()) {
  return [
    { client: "Claude Code",    path: join(home, ".claude.json"),        key: "mcpServers" },
    { client: "Claude Code",    path: join(cwd, ".mcp.json"),            key: "mcpServers", scope: "project" },
    { client: "Claude Desktop", path: join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json"), key: "mcpServers" },
    { client: "Claude Desktop", path: join(home, ".config", "Claude", "claude_desktop_config.json"), key: "mcpServers" },
    { client: "Cursor",         path: join(home, ".cursor", "mcp.json"), key: "mcpServers" },
    { client: "Cursor",         path: join(cwd, ".cursor", "mcp.json"),  key: "mcpServers", scope: "project" },
    { client: "VS Code",        path: join(cwd, ".vscode", "mcp.json"),  key: "servers", scope: "project" },
    { client: "Windsurf",       path: join(home, ".codeium", "windsurf", "mcp_config.json"), key: "mcpServers" },
  ];
}

export function skillLocations(home = homedir(), cwd = process.cwd()) {
  return [
    { scope: "user",    dir: join(home, ".claude", "skills") },
    { scope: "project", dir: join(cwd, ".claude", "skills") },
  ];
}

/** Drop a trailing @version/@tag from an npm specifier.
 *  Must not eat the leading @ of a scoped package: "@playwright/mcp@latest" -> "@playwright/mcp",
 *  "chrome-devtools-mcp@latest" -> "chrome-devtools-mcp", "@upstash/context7-mcp" -> unchanged.
 *  (A numeric-only regex missed "@latest" and silently made every pinned server unmatchable.) */
export function stripVersion(spec) {
  const at = spec.lastIndexOf("@");
  return at > 0 ? spec.slice(0, at) : spec;
}

/** Pull the npm package (or command identity) out of one MCP server config block. */
export function identify(entry) {
  if (!entry || typeof entry !== "object") return null;
  if (entry.url) {                                   // remote / streamable-http server
    try { return { kind: "remote", id: new URL(entry.url).host }; } catch { return { kind: "remote", id: entry.url }; }
  }
  const args = Array.isArray(entry.args) ? entry.args : [];
  const cmd = String(entry.command || "");
  // npx -y <pkg>  |  npx <pkg>  — the overwhelmingly common shape
  if (/npx$/.test(cmd)) {
    const pkg = args.find((x) => typeof x === "string" && !x.startsWith("-"));
    if (pkg) return { kind: "npm", id: stripVersion(String(pkg)) };
  }
  if (/^(uvx|uv)$/.test(cmd)) {
    const pkg = args.find((x) => typeof x === "string" && !x.startsWith("-"));
    if (pkg) return { kind: "python", id: pkg };
  }
  if (/docker$/.test(cmd)) {
    const img = args.find((x) => typeof x === "string" && !x.startsWith("-") && x !== "run");
    if (img) return { kind: "docker", id: img };
  }
  return cmd ? { kind: "local", id: cmd } : null;
}

/** Read every config we can find. Never throws on a malformed or unreadable file — a broken config is
 *  itself worth reporting, and a crash here would make the tool useless exactly when it is needed. */
export function collect(locations, skillDirs, read = readFileSync, exists = existsSync, list = readdirSync) {
  const found = [], problems = [];
  for (const loc of locations) {
    if (!exists(loc.path)) continue;
    let json;
    try { json = JSON.parse(read(loc.path, "utf8")); }
    catch (e) { problems.push({ path: loc.path, error: "unreadable or invalid JSON" }); continue; }
    const block = json[loc.key] || {};
    for (const [name, entry] of Object.entries(block)) {
      const ident = identify(entry);
      found.push({ type: "server", client: loc.client, scope: loc.scope || "user", name, path: loc.path, ...(ident || {}) });
    }
  }
  for (const s of skillDirs) {
    if (!exists(s.dir)) continue;
    let names = [];
    try { names = list(s.dir); } catch { continue; }
    for (const n of names) {
      if (n.startsWith(".")) continue;
      found.push({ type: "skill", client: "Claude", scope: s.scope, name: n, id: n, kind: "skill", path: join(s.dir, n) });
    }
  }
  return { found, problems };
}

/** Match one installed item against the tashan index. */
export function match(item, rows) {
  const idl = String(item.id || item.name || "").toLowerCase();
  if (!idl) return null;
  if (item.kind === "npm") {
    const hit = rows.find((r) => (r.npm_pkg || "").toLowerCase() === idl);
    if (hit) return hit;
  }
  if (item.kind === "skill") {
    const hit = rows.find((r) => r.kind === "skill" && String(r.name || "").toLowerCase() === idl);
    if (hit) return hit;
  }
  const bare = idl.replace(/^@[^/]+\//, "");
  return rows.find((r) => {
    const n = String(r.name || "").toLowerCase();
    return n === idl || n === bare || (r.npm_pkg || "").toLowerCase() === idl;
  }) || null;
}

/** Resolve a config entry against the LOOKUP table (web/data/lookup.json).
 *
 *  match() above searches the ranked board, which is why doctor only ever recognised npm and skills:
 *  the board carries no remote, docker or python rows at all, and only 522 of 1,380 measured npm
 *  packages. It answered "not in the tashan index — unmeasured" for things we had scored, which reads
 *  as reassurance and is the worst way to be wrong.
 *
 *  The lookup is keyed by every identity a config can produce — npm package, python package, docker
 *  image, capability id, and the id with its `kind:` prefix stripped — so one indexed hit replaces the
 *  scan. Pure: the caller supplies the parsed lookup, nothing fetches here.
 */
export function resolve(item, lookup) {
  if (!item || !lookup || !lookup.keys) return null;
  const rec = (k) => {
    if (!k) return null;
    const i = lookup.keys[String(k).toLowerCase()];
    return i === undefined ? null : lookup.records[i];
  };
  const id = item.id || item.name || "";
  return rec(id)
      // a scoped package may be configured bare, and vice versa
      || rec(String(id).replace(/^@[^/]+\//, ""))
      // docker images and remote hosts arrive without the `kind:` prefix the id carries
      || rec(`${item.kind}:${id}`)
      || null;
}

/** The verdicts. Deliberately conservative: we flag what the evidence supports and say "unknown"
 *  rather than guessing. An audit tool that cries wolf gets uninstalled. */
export function assess(item, row) {
  const notes = [];
  if (!row) return { level: "unknown", notes: ["not in the tashan index — unmeasured, not necessarily bad"] };
  if (row.gh_archived) notes.push({ level: "alert", text: "source repository is archived" });
  if (row.npm_deprecated) notes.push({ level: "alert", text: "npm package is marked deprecated" });
  if (row.registry_status === "deprecated") notes.push({ level: "alert", text: "deprecated in the MCP registry" });
  // The registry's moderation policy says `deleted` typically means spam, malware or illegal content.
  // It is the single most serious thing we can tell a user about something they are already running,
  // and it is free, permanently.
  if (row.registry_status === "deleted") notes.push({ level: "alert",
    text: "REMOVED from the MCP registry — its policy lists spam, malware or illegal content as the usual reasons. Stop using it and verify the source." });
  if (row.vitality === "abandoned") notes.push({ level: "warn", text: "no recent activity — looks abandoned" });
  if (row.similar_official) notes.push({ level: "alert", text: `an official package with a similar name exists: ${row.similar_official}` });
  if (row.single_maintainer) notes.push({ level: "note", text: "single primary maintainer (bus-factor risk)" });
  if (row.rated === false) notes.push({ level: "note", text: "catalogued but not rated — no per-item evidence yet" });
  // "rated:false" must not render as a green tick. We know the item exists and know nothing about its
  // quality — that is its own state, distinct from both "fine" and "never heard of it".
  const level = notes.some((n) => n.level === "alert") ? "alert"
    : notes.some((n) => n.level === "warn") ? "warn"
    : row.rated === false ? "unrated" : "ok";
  return { level, notes };
}

export function summarize(results) {
  const s = { total: results.length, servers: 0, skills: 0, alert: 0, warn: 0, ok: 0, unknown: 0 };
  for (const r of results) {
    if (r.item.type === "skill") s.skills++; else s.servers++;
    s[r.assessment.level] = (s[r.assessment.level] || 0) + 1;
  }
  return s;
}

// ---------------------------------------------------------------------------------------------
// TREND — the paid half of doctor, and the reason history is worth $6.
//
// Free doctor answers "is anything in my stack dead RIGHT NOW". That question is answerable from
// today's export, so it stays free. It is also the wrong question to ask on the day it matters,
// because by the time a capability is archived or deprecated you have already been depending on it
// for months. The question worth paying for is the one nobody else can answer: "is anything in my
// stack DYING" — which needs the series, and the series cannot be backfilled by anyone, us included.
//
// Pure function on purpose: no fetch, no clock, no filesystem. The caller supplies the series it got
// from /api/history, so this is fully testable and the network stays at the edge of the program.
// series shape: { tashan_score: { "2026-07-23": 61, ... }, adoption: { ... } }

export function trend(series, scorers = null, minDays = 3) {
  let entries = Object.entries((series && series.tashan_score) || {});
  // ONLY COMPARE WITHIN ONE SCORER VERSION. The scorer was rewritten four times inside the first week
  // of history, so pkg:3dstreet-mcp reads 43,43,43,43,42,40 with every step caused by us, not by the
  // capability. Trending across that bills a customer to be told our own recalibration was decline.
  // Keep the newest version's points and drop the rest; if that leaves too few, say so rather than
  // reaching back across the boundary.
  if (scorers && Object.keys(scorers).length) {
    const dates = entries.map(([d]) => d).sort();
    const newest = scorers[dates[dates.length - 1]];
    if (newest) entries = entries.filter(([d]) => scorers[d] === newest);
  }
  const points = entries.sort((a, b) => (a[0] < b[0] ? -1 : 1));
  if (points.length < minDays) {
    return { level: "note", direction: "new", days: points.length,
             text: `only ${points.length} day(s) of comparable history — not enough to call a trend yet` };
  }
  const first = points[0][1], last = points[points.length - 1][1];
  const delta = Math.round(last - first);
  const days = points.length;
  const lo = Math.min(...points.map((p) => p[1]));
  const off = Math.round(last - lo);

  // A DROP IS NOT THE SAME AS A LOW SCORE, and only the drop is news. A capability that has sat at
  // 32 for a month is already visible on the free board; one that fell from 58 to 41 this week is
  // the thing you would never notice by looking at it today.
  if (delta <= -10) {
    return { level: "alert", direction: "falling", days, delta,
             text: `fell ${Math.abs(delta)} points over ${days} days (${first} → ${last})` };
  }
  if (delta <= -4) {
    return { level: "warn", direction: "slipping", days, delta,
             text: `down ${Math.abs(delta)} points over ${days} days (${first} → ${last})` };
  }
  if (delta >= 6 && off >= 4) {
    return { level: "note", direction: "recovering", days, delta,
             text: `recovering — up ${delta} points over ${days} days (${first} → ${last})` };
  }
  return { level: "ok", direction: "steady", days, delta, text: `steady over ${days} days (${last})` };
}

// Fold trends into the free assessment. Escalates a level but never de-escalates one: a falling score
// can make a clean row worth looking at, but a rising score must never quiet an archived repository.
export function withTrend(assessment, tr) {
  if (!tr) return assessment;
  const notes = assessment.notes.concat([{ level: tr.level, text: tr.text, trend: true }]);
  const rank = { ok: 0, unrated: 1, note: 1, warn: 2, alert: 3 };
  const level = (rank[tr.level] || 0) > (rank[assessment.level] || 0) ? tr.level : assessment.level;
  return { ...assessment, level, notes, trend: tr };
}

// ---------------------------------------------------------------------------------------------
// SUGGEST — what to switch to. The paid half's actual value, and the reason history alone was not
// enough to sell.
//
// Category is useless as a partition here: 67% of scored capabilities sit in `productivity` or
// `devtools`, and ranking by score inside a category proposed a Lark comms server be replaced by an
// SEO plugin. Co-use is populated on 1% of rows and none of the skills or plugins. Task tags cover
// none of the npm/remote servers that actually appear in configs.
//
// What does work is a SHARED LOW-FREQUENCY TOKEN. If a dead capability and a live one both contain a
// word that few other capabilities contain — `cloudflare`, `sqlite`, `gmail` — they are almost always
// the same integration. Measured on the real export, 109 of 267 dead capabilities get a confident
// suggestion this way, and the ones it declines to answer are better left unanswered: "no confident
// alternative" is a real answer and the honest default.
//
// Pure: the caller supplies the candidate pool. No fetch, no clock.
const STOPWORDS = new Set(["mcp", "server", "servers", "cli", "api", "tool", "tools", "app", "agent",
  "plugin", "skill", "skills", "claude", "ai", "the", "for", "and", "with", "sdk", "js", "ts", "node",
  "python", "py", "lib", "core", "client", "service", "integration", "official", "open", "source"]);

export function tokensOf(cap) {
  const src = `${cap.npm_pkg || ""} ${cap.name || ""} ${cap.id || ""}`.toLowerCase();
  return new Set(src.split(/[^a-z0-9]+/).filter((w) => w.length > 2 && !STOPWORDS.has(w)));
}

/** How many capabilities in the pool contain each token — a token in half the corpus says nothing. */
export function tokenFrequency(pool) {
  const df = new Map();
  for (const c of pool) for (const t of tokensOf(c)) df.set(t, (df.get(t) || 0) + 1);
  return df;
}

export function isDying(c) {
  return Boolean(c && (c.gh_archived || c.npm_deprecated
    || c.registry_status === "deprecated" || c.registry_status === "deleted"
    || c.vitality === "abandoned"));
}

/** Alternatives to `cap`, best first. Empty when nothing is confidently comparable. */
export function suggest(cap, pool, df = null, opts = {}) {
  if (!cap) return [];
  const maxDf = opts.maxDf || 60;      // a token shared by more than this is a category word, not an integration
  const limit = opts.limit || 2;
  const freq = df || tokenFrequency(pool);
  const mine = tokensOf(cap);
  const out = [];
  for (const p of pool) {
    if (!p || p.id === cap.id || p.tashan_score == null) continue;
    if (isDying(p)) continue;                                  // never replace a dead thing with a dead thing
    if (p.tashan_score <= (cap.tashan_score || 0)) continue;   // and never with a worse-measured one
    const shared = [...mine].filter((t) => tokensOf(p).has(t) && (freq.get(t) || 0) <= maxDf);
    if (shared.length) out.push({ cap: p, shared, score: p.tashan_score });
  }
  out.sort((a, b) => (b.shared.length - a.shared.length) || (b.score - a.score));
  return out.slice(0, limit);
}
