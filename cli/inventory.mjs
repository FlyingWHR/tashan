// tashan inventory — everything you installed or wrote, and when it arrived.
//
// WHY THIS EXISTS. doctor answers "is anything in my stack dead or dangerous" about the things it
// can name. It cannot answer the question that comes first, which people only notice once the pile
// is big: WHAT DO I EVEN HAVE. A working machine here carries 113 skills, 7 plugins from 8
// marketplaces and 12 MCP servers spread across 52 projects. Nobody remembers installing most of
// that, nobody knows which ones they wrote themselves, and nothing on disk tells you.
//
// THREE THINGS THE OLD SCAN MISSED, all of them structural rather than cosmetic:
//
//   1. PROJECT-SCOPED SERVERS. ~/.claude.json carries `projects{}`, one entry per directory you
//      have opened, each with its own mcpServers block. doctor read the top-level block and a
//      .mcp.json in the CURRENT directory, so a server installed into another project was
//      invisible — 52 projects deep on the machine above. An audit that only sees where you happen
//      to be standing is not an audit.
//   2. PLUGINS. installed_plugins.json already records installedAt, lastUpdated and the commit sha
//      per plugin. That is provenance nobody was reading.
//   3. WHAT YOU WROTE. A skill you authored and a skill you installed are different risks and
//      different work: one is yours to maintain, the other is somebody else's to abandon. They sit
//      in the same directory and look identical until you check whether a plugin owns the path.
//
// FIRST SEEN IS OURS TO KEEP. Plugins record their own install date; skills and servers do not, and
// a file mtime is the last edit, not the arrival. So the ledger at ~/.tashan/inventory.json records
// the first run that saw each item. It is local, it is a plain JSON file you can read, and nothing
// is uploaded — the privacy rule in doctor.mjs applies here unchanged.
//
// Pure functions take injected fs so the tests never touch a real home directory.

import { readFileSync, readdirSync, existsSync, statSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const LEDGER = (home = homedir()) => join(home, ".tashan", "inventory.json");

/** The YAML frontmatter of a SKILL.md, shallowly. A skill's name and description are the only two
 *  fields worth reading, and a real YAML parser is not worth a dependency in a stdlib-only CLI. */
export function frontmatter(text) {
  const m = /^---\n([\s\S]*?)\n---/.exec(String(text || ""));
  if (!m) return {};
  const out = {};
  for (const line of m[1].split("\n")) {
    const kv = /^([a-z-]+):\s*(.*)$/i.exec(line);          // top level only; nested args are ignored
    if (kv && kv[2] !== "") out[kv[1]] = kv[2].replace(/^["']|["']$/g, "");
  }
  return out;
}

/** Every MCP server in ~/.claude.json, including the per-project blocks doctor never opened. */
export function serversFromClaudeJson(json) {
  const out = [];
  for (const [name, entry] of Object.entries(json?.mcpServers || {})) {
    out.push({ kind: "server", scope: "user", project: null, name, entry });
  }
  for (const [path, proj] of Object.entries(json?.projects || {})) {
    for (const [name, entry] of Object.entries(proj?.mcpServers || {})) {
      out.push({ kind: "server", scope: "project", project: path, name, entry });
    }
  }
  return out;
}

/** Installed plugins, with the provenance the file already carries. */
export function pluginsFrom(installed) {
  const out = [];
  for (const [key, rows] of Object.entries(installed?.plugins || {})) {
    for (const r of rows || []) {
      const [name, marketplace] = key.split("@");
      out.push({
        kind: "plugin",
        name,
        marketplace: marketplace || null,
        scope: r.scope || "user",
        version: r.version || null,
        installedAt: r.installedAt || null,
        lastUpdated: r.lastUpdated || null,
        sha: r.gitCommitSha || null,
        path: r.installPath || null,
      });
    }
  }
  return out;
}

/**
 * The capability id of an installed plugin, or null when its home cannot be read off disk.
 *
 * IDENTITY IS WHERE THE PLUGIN LIVES, and a name is not an identity: by name `vercel-plugin` resolves
 * to a third party's fork and `frontend-design` to three different rows. The marketplace manifest
 * says where each plugin lives — a relative `source` is a folder inside the marketplace's own GitHub
 * repository, a `url` source names the repository outright. A marketplace that is only a local
 * directory tells us nothing, and stays unresolved rather than guessed.
 */
export function pluginId(name, market, manifest) {
  const entry = (manifest?.plugins || []).find((p) => p && p.name === name);
  if (!entry) return null;
  const src = entry.source;
  let repo = null;
  if (typeof src === "string") repo = market?.source?.source === "github" ? market.source.repo : null;
  else if (src && typeof src.url === "string") {
    repo = (/github\.com[/:]([^/]+\/[^/#?]+?)(?:\.git)?(?:[/#?]|$)/.exec(src.url) || [])[1] || null;
  } else if (src && src.source === "github") repo = src.repo || null;
  return repo ? `plugin:${repo}/${name}`.toLowerCase() : null;
}

/**
 * Skills on disk, with the one distinction that matters: did you write this, or did something
 * install it. A skill whose directory sits inside a plugin's cache belongs to that plugin; anything
 * else under your skills directory is yours, and yours is the half nobody else will ever maintain.
 */
export function skillsIn(dirs, pluginPaths = [], deps = {}) {
  const exists = deps.exists || existsSync;
  const list = deps.list || readdirSync;
  const read = deps.read || readFileSync;
  const stat = deps.stat || statSync;
  const owned = (p) => pluginPaths.find((pp) => pp && p.startsWith(pp)) || null;
  const out = [];
  for (const d of dirs) {
    if (!exists(d.dir)) continue;
    let names = [];
    try { names = list(d.dir); } catch { continue; }
    for (const n of names) {
      if (String(n).startsWith(".")) continue;
      // A skill is a DIRECTORY. Listing one returns loose files too — a stray `_chain-audit.md`
      // was counted and reported as a skill by that name, which is how an inventory starts lying
      // about its own total. Match KNOWN file extensions, not "anything after a dot": the first
      // version used /\.[a-z0-9]+$/ and dropped every versioned skill directory on the machine,
      // `cinema-worldbuilder-pro-2.0` among them, because ".0" is a dot followed by a digit.
      if (/\.(md|markdown|json|ya?ml|txt|js|mjs|ts|sh|py|toml|lock|log|bak)$/i.test(String(n))) continue;
      const path = join(d.dir, n);
      const md = join(path, "SKILL.md");
      let meta = {};
      try { if (exists(md)) meta = frontmatter(read(md, "utf8")); } catch { /* a skill with an unreadable SKILL.md is still a skill */ }
      let modified = null;
      try { modified = stat(exists(md) ? md : path).mtime.toISOString().slice(0, 10); } catch { /* ignore */ }
      out.push({
        kind: "skill",
        name: meta.name || n,
        scope: d.scope,
        path,
        description: meta.description || null,
        documented: Boolean(meta.description),
        owner: owned(path),
        authored: !owned(path),
        modified,
      });
    }
  }
  return out;
}

/** One stable identity per item, so the ledger can follow it across runs and renames of the dir. */
export function idOf(item) {
  if (item.kind === "server") return `server:${item.scope}:${item.project ? `${item.project}:` : ""}${item.name}`;
  if (item.kind === "plugin") return `plugin:${item.name}@${item.marketplace || "local"}`;
  return `skill:${item.scope}:${item.name}`;
}

/**
 * Fold today's scan into the ledger. Returns what is new since last time and what has gone —
 * the two facts a pile this size makes impossible to hold in your head.
 *
 * `gone` is reported, never deleted: something absent today because a project directory is on an
 * unmounted disk has not been uninstalled, and quietly forgetting it would lose the first-seen date
 * that cannot be recovered.
 */
export function reconcile(prev, items, today) {
  const seen = prev?.seen || {};
  const next = { version: 1, updated: today, seen: { ...seen } };
  const fresh = [], returning = [];
  for (const it of items) {
    const id = idOf(it);
    const was = seen[id];
    if (!was) {
      next.seen[id] = { first: today, last: today, kind: it.kind, name: it.name };
      fresh.push(it);
    } else {
      if (was.last !== today && was.gone) returning.push(it);
      next.seen[id] = { ...was, last: today, kind: it.kind, name: it.name, gone: false };
    }
  }
  const here = new Set(items.map(idOf));
  const gone = [];
  for (const [id, row] of Object.entries(next.seen)) {
    if (here.has(id)) continue;
    next.seen[id] = { ...row, gone: true };
    // Only what was HERE last run is news. Everything already marked gone was reported again on every
    // run, forever — "gone since last run: _chain-audit.md" on each doctor, about a file that had
    // left weeks before.
    if (!row.gone) gone.push({ id, ...row });
  }
  return { ledger: next, fresh, gone, returning };
}

/** Read the whole picture off one machine. Never throws: a broken file is a finding, not a crash. */
export function scan(home = homedir(), cwd = process.cwd(), deps = {}) {
  const exists = deps.exists || existsSync;
  const read = deps.read || readFileSync;
  const problems = [];
  const readJson = (p) => {
    if (!exists(p)) return null;
    try { return JSON.parse(read(p, "utf8")); }
    catch { problems.push({ path: p, error: "unreadable or invalid JSON" }); return null; }
  };

  const claude = readJson(join(home, ".claude.json")) || {};
  const servers = serversFromClaudeJson(claude);
  const installed = readJson(join(home, ".claude", "plugins", "installed_plugins.json"));
  const plugins = pluginsFrom(installed);
  const known = readJson(join(home, ".claude", "plugins", "known_marketplaces.json")) || {};
  const marketplaces = Object.keys(known);
  // Each plugin's home, read off its marketplace's manifest, so doctor can audit plugins by identity
  // rather than by a name that several unrelated plugins share. One manifest read per marketplace.
  const manifests = {};
  for (const p of plugins) {
    const m = known[p.marketplace];
    if (m?.installLocation && !(p.marketplace in manifests)) {
      manifests[p.marketplace] = readJson(join(m.installLocation, ".claude-plugin", "marketplace.json"));
    }
    p.id = pluginId(p.name, m, manifests[p.marketplace]);
  }
  // Plugins ship skills inside their own install path, and those were never scanned — so every
  // skill on the machine looked unowned, which reads as "113 things nobody maintains" on a box
  // with 11 plugins. Scan the plugin directories too and the ownership line becomes true.
  const skills = skillsIn(
    [
      { scope: "user", dir: join(home, ".claude", "skills") },
      { scope: "project", dir: join(cwd, ".claude", "skills") },
      ...plugins.filter((p) => p.path).map((p) => ({ scope: "plugin", dir: join(p.path, "skills") })),
    ],
    plugins.map((p) => p.path),
    deps,
  );
  return { servers, plugins, skills, marketplaces, problems, projects: Object.keys(claude.projects || {}).length };
}

export function loadLedger(home = homedir(), deps = {}) {
  const exists = deps.exists || existsSync;
  const read = deps.read || readFileSync;
  const p = LEDGER(home);
  if (!exists(p)) return { version: 1, seen: {} };
  try { return JSON.parse(read(p, "utf8")); } catch { return { version: 1, seen: {} }; }
}

export function saveLedger(ledger, home = homedir()) {
  const p = LEDGER(home);
  try {
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, JSON.stringify(ledger, null, 2) + "\n");
    return true;
  } catch {
    return false;   // a read-only home is not a reason to fail a scan
  }
}

// ---- usage: what you call, not what you have ----------------------------------------------------
//
// Once the pile is big, a list of what is installed answers nobody's question. Which of it you USE
// does — and Claude Code already records both halves on this machine: every tool call lands in a
// session transcript under ~/.claude/projects, and ~/.claude.json keeps a usageCount and lastUsedAt
// per skill. Nothing is executed and nothing leaves the machine. The only things read out of a
// transcript are the name of an MCP tool that was called and the date; the scan matches the bytes
// around the tool_use marker and never parses a message.
//
// CLAUDE CODE ONLY. Cursor and Claude Desktop leave nothing this readable, so a server configured
// there gets NO usage figure — never a zero, which would read as "you never use it".

const TOOL_USE = Buffer.from('"type":"tool_use","id":"');
const NAME = Buffer.from('"name":"');

/** MCP calls recorded in one transcript's bytes, folded into `into`: { server: { calls, last } }.
 *  A tool_use quoted inside a tool result is escaped (\"type\"), so it never matches the marker. */
export function mcpCallsIn(buf, into = {}, sinceDay = "") {
  let i = 0;
  while ((i = buf.indexOf(TOOL_USE, i)) !== -1) {
    // The first "name" after the id is this block's own: an id is a bare token with no quotes in it.
    const n = buf.indexOf(NAME, i + TOOL_USE.length);
    if (n === -1) break;
    const start = n + NAME.length;
    i = start;
    if (buf.toString("utf8", start, start + 5) !== "mcp__") continue;
    const end = buf.indexOf(34, start);                            // 34 = the closing quote
    if (end === -1) break;
    const full = buf.toString("utf8", start + 5, end);             // "<server>__<tool>"
    const sep = full.indexOf("__");
    const server = sep > 0 ? full.slice(0, sep) : full;
    // ponytail: the first "timestamp" on the line is taken as the entry's own; a tool INPUT carrying
    // its own "timestamp" key could shadow it, which misdates one call and cannot miscount it.
    const ls = buf.lastIndexOf(10, n) + 1, le = buf.indexOf(10, end);
    const m = /"timestamp":"(\d{4}-\d\d-\d\d)/.exec(buf.toString("utf8", ls, le === -1 ? buf.length : le));
    const day = m ? m[1] : "";
    if (day >= sinceDay) {
      const u = into[server] || (into[server] = { calls: 0, last: "" });
      u.calls++;
      if (day > u.last) u.last = day;
    }
  }
  return into;
}

/** How Claude Code spells a configured server inside its tool names: anything outside
 *  [A-Za-z0-9_-] becomes "_" — "claude.ai Gmail" appears in transcripts as claude_ai_Gmail. */
export function toolPrefix(name) {
  return String(name || "").replace(/[^A-Za-z0-9_-]/g, "_");
}

/** Everything Claude Code has recorded about what gets used over the last `days`. Never throws. */
export function usage(home = homedir(), now = Date.now(), days = 30, deps = {}) {
  const list = deps.list || readdirSync, stat = deps.stat || statSync, read = deps.read || readFileSync;
  const sinceMs = now - days * 864e5;
  const since = new Date(sinceMs).toISOString().slice(0, 10);
  const servers = {};
  let files = 0;
  const root = join(home, ".claude", "projects");
  let dirs = [];
  try { dirs = list(root); } catch { /* no Claude Code history on this machine */ }
  for (const d of dirs) {
    let names = [];
    try { names = list(join(root, d)); } catch { continue; }
    for (const f of names) {
      if (!String(f).endsWith(".jsonl")) continue;
      const p = join(root, d, f);
      try {
        if (stat(p).mtimeMs < sinceMs) continue;     // untouched since before the window: nothing in it counts
        mcpCallsIn(read(p), servers, since);
        files++;
      } catch { /* a transcript mid-write or unreadable is skipped, never fatal */ }
    }
  }
  let skills = {};
  try { skills = JSON.parse(read(join(home, ".claude.json"), "utf8")).skillUsage || {}; } catch { /* none recorded */ }
  return { since, days, sinceMs, files, servers, skills, available: files > 0 };
}

/**
 * One configured item's usage, or null where nothing readable records it. null is not zero.
 *   - a Claude Code server: calls inside the window, from the transcripts
 *   - a skill: Claude Code's own counter, and whether its last use falls inside the window
 *   - a plugin: only ever a POSITIVE figure. Hooks, agents and commands leave no trace in a
 *     transcript, so a plugin that is never "called" may be working on every session — ponytail is a
 *     SessionStart hook — and silence from it is not disuse.
 */
export function usageOf(item, u) {
  if (!u || !item) return null;
  if (item.type === "skill" || item.kind === "skill") {
    if (!Object.keys(u.skills || {}).length) return null;
    const s = u.skills[item.plugin ? `${item.plugin}:${item.name}` : item.name];
    return { calls: (s && s.usageCount) || 0, recent: Boolean(s && s.lastUsedAt >= u.sinceMs),
             last: s && s.lastUsedAt ? new Date(s.lastUsedAt).toISOString().slice(0, 10) : null };
  }
  if (!u.available || item.client !== "Claude Code") return null;
  if (item.type === "plugin") {
    let calls = 0, last = "";
    const pre = `plugin_${toolPrefix(item.name)}_`;
    for (const [srv, v] of Object.entries(u.servers)) {
      if (srv.startsWith(pre)) { calls += v.calls; if (v.last > last) last = v.last; }
    }
    return calls ? { calls, last, recent: true } : null;
  }
  const v = u.servers[toolPrefix(item.name)];
  return { calls: v ? v.calls : 0, last: v ? v.last : null, recent: Boolean(v) };
}

/* ---------------------------------------------------------------- self-check ------------------ */

function selftest() {
  const fm = frontmatter("---\nname: adapt\ndescription: Adapt designs across devices.\nuser-invokable: true\n---\n# body");
  if (fm.name !== "adapt" || !fm.description) throw new Error("frontmatter: name/description not read");
  if (frontmatter("no frontmatter here").name) throw new Error("frontmatter: invented a field");

  // The bug this whole file exists to fix: servers living in other projects.
  const s = serversFromClaudeJson({
    mcpServers: { a: {} },
    projects: { "/p/one": { mcpServers: { b: {} } }, "/p/two": { mcpServers: { c: {} } }, "/p/three": {} },
  });
  if (s.length !== 3) throw new Error(`expected 3 servers across user + projects, got ${s.length}`);
  if (!s.some((x) => x.project === "/p/two" && x.name === "c")) throw new Error("project-scoped server lost");

  const p = pluginsFrom({ plugins: { "telegram@official": [{ scope: "user", version: "0.0.7", installedAt: "2026-03-23T14:15:49Z", installPath: "/h/.claude/plugins/cache/official/telegram/0.0.7" }] } });
  if (p[0].name !== "telegram" || p[0].marketplace !== "official") throw new Error("plugin key not split");
  if (!p[0].installedAt) throw new Error("plugin install date dropped — it is the only provenance on disk");

  // Authored vs installed, which is the distinction the pile hides.
  const files = {
    "/h/.claude/skills/mine/SKILL.md": "---\nname: mine\ndescription: something I wrote.\n---",
    "/h/.claude/plugins/cache/official/telegram/0.0.7/skills/theirs/SKILL.md": "---\nname: theirs\n---",
  };
  const deps = {
    exists: (q) => q in files || Object.keys(files).some((f) => f.startsWith(q + "/")),
    list: (d) => (d === "/h/.claude/skills" ? ["mine"] : ["theirs"]),
    read: (q) => files[q],
    stat: () => ({ mtime: new Date("2026-09-01T00:00:00Z") }),
  };
  const sk = skillsIn(
    [{ scope: "user", dir: "/h/.claude/skills" },
     { scope: "user", dir: "/h/.claude/plugins/cache/official/telegram/0.0.7/skills" }],
    ["/h/.claude/plugins/cache/official/telegram/0.0.7"],
    deps,
  );
  const mine = sk.find((x) => x.name === "mine");
  const theirs = sk.find((x) => x.name === "theirs");
  if (!mine.authored) throw new Error("a skill you wrote was attributed to a plugin");
  if (theirs.authored) throw new Error("a plugin's skill was reported as yours to maintain");
  if (mine.documented !== true || theirs.documented !== false) throw new Error("undocumented skills must be visible as such");

  // The ledger: first seen is kept, absence is recorded rather than forgotten.
  const day1 = reconcile({ version: 1, seen: {} }, [{ kind: "skill", scope: "user", name: "a" }], "2026-09-01");
  if (day1.fresh.length !== 1) throw new Error("first run should report everything as new");
  const day2 = reconcile(day1.ledger, [{ kind: "skill", scope: "user", name: "a" }, { kind: "skill", scope: "user", name: "b" }], "2026-09-02");
  if (day2.fresh.length !== 1 || day2.fresh[0].name !== "b") throw new Error("only the genuinely new item is new");
  if (day2.ledger.seen["skill:user:a"].first !== "2026-09-01") throw new Error("first-seen was overwritten — it cannot be recovered");
  const day3 = reconcile(day2.ledger, [{ kind: "skill", scope: "user", name: "a" }], "2026-09-03");
  if (day3.gone.length !== 1 || day3.gone[0].name !== "b") throw new Error("a disappearance must be reported");
  if (!day3.ledger.seen["skill:user:b"]) throw new Error("a disappeared item was deleted from the ledger, losing its history");

  console.log("ok   servers in every project are found, not only the one you are standing in");
  console.log("ok   what you wrote is told apart from what a plugin installed");
  console.log("ok   first-seen survives, and a disappearance is recorded rather than forgotten");
}

// Run directly, not merely imported by something whose NAME ends the same way. The first version
// of this guard said `argv[1].endsWith("inventory.mjs")`, which is also true of
// tests/test_inventory.mjs — so importing the module from its own test printed a full scan of the
// developer's machine into the test output and buried the results.
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.includes("--selftest")) selftest();
  else console.log(JSON.stringify(scan(), null, 2));
}
