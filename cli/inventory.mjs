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
    gone.push({ id, ...row });
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
  const marketplaces = Object.keys(readJson(join(home, ".claude", "plugins", "known_marketplaces.json")) || {});
  const skills = skillsIn(
    [
      { scope: "user", dir: join(home, ".claude", "skills") },
      { scope: "project", dir: join(cwd, ".claude", "skills") },
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
