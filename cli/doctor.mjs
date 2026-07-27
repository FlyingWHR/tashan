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

/** The verdicts. Deliberately conservative: we flag what the evidence supports and say "unknown"
 *  rather than guessing. An audit tool that cries wolf gets uninstalled. */
export function assess(item, row) {
  const notes = [];
  if (!row) return { level: "unknown", notes: ["not in the tashan index — unmeasured, not necessarily bad"] };
  if (row.gh_archived) notes.push({ level: "alert", text: "source repository is archived" });
  if (row.npm_deprecated) notes.push({ level: "alert", text: "npm package is marked deprecated" });
  if (row.registry_status === "deprecated") notes.push({ level: "alert", text: "deprecated in the MCP registry" });
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
