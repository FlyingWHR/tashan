#!/usr/bin/env node
// tashan as an MCP server — the measured layer, inside the agent's decision loop.
//
//   claude mcp add tashan -- npx -y tashan mcp        <- the one install string
//
// WHY THIS EXISTS AND /v0.1/* DOES NOT REPLACE IT
// /v0.1/servers is byte-compatible with the MCP registry, which is elegant and passive: a host has to
// already know we exist and choose to point at it. That is a B2B integration path, and it does nothing
// for the person who opens Claude Code or Codex, has never heard of tashan, and says "I want to work
// with PDFs". Today their agent answers that from training data or a web search — no measurement, no
// check that the thing is still maintained, and no check that the name is not shadowing an official
// package. This server makes us the thing the agent asks at exactly that moment.
//
// THE FREE/PAID LINE IS THE SAME HERE AS EVERYWHERE. Finding, checking and auditing are free: we do
// not charge anyone to learn that what they are about to install is deprecated or impersonating
// something official. The paid layer is what to do about it.
//
// PRIVACY. audit_config reads local files and sends nothing. find/check send only a search term or a
// capability name to a public JSON endpoint — the same one the website fetches.
//
// Zero dependencies, stdio transport, newline-delimited JSON-RPC 2.0.

import { search, find, installSnippets, pretty, slugify } from "./tashan.mjs";
import { configLocations, skillLocations, collect, resolve, assess, summarize } from "./doctor.mjs";

const SITE = process.env.TASHAN_SITE || "https://tashan.sh";
const NAME = "tashan";
const VERSION = "0.1.0";
// The client tells us which protocol revision it speaks. Echoing it back is deliberate: this server
// uses only the universal core (initialize / tools/list / tools/call), so pinning a hardcoded date
// would break against a newer client for no reason. Falls back to a known-good revision.
const FALLBACK_PROTOCOL = "2025-06-18";

let cache = null, lookupCache = null;
async function get(path) {
  const r = await fetch(`${SITE}${path}`, { headers: { "user-agent": `${NAME}-mcp/${VERSION}` } });
  if (!r.ok) throw new Error(`tashan ${path} unavailable (HTTP ${r.status})`);
  return r.json();
}
// The board answers "what is good" (ranked, for find/check); the lookup answers "what is this"
// (complete and keyed, for audit). Using the board for both is what made audit blind to every remote,
// docker and python entry and to two thirds of the npm packages we measure.
async function rows() {
  if (!cache) { const d = await get("/data/index.json"); cache = d.capabilities || d; }
  return cache;
}
async function lookup() {
  if (!lookupCache) lookupCache = await get("/data/lookup.json");
  return lookupCache;
}

// ---- the evidence line. One string an agent can quote to a human without over-claiming. ----
export function evidence(c) {
  const bits = [];
  if (c.tashan_score != null) bits.push(`tashan score ${Math.round(c.tashan_score)}/100`);
  if (c.expertise_verdict) bits.push(`expertise: ${c.expertise_verdict}`);
  if (c.npm_downloads) bits.push(`${c.npm_downloads.toLocaleString()} downloads/wk`);
  else if (c.gh_stars) bits.push(`${c.gh_stars.toLocaleString()} stars`);
  if (c.vitality) bits.push(c.vitality);
  return bits.join(" · ") || "no measurement yet";
}

// ---- risk. Free, always. Mirrors assess() so the CLI and the agent never disagree. ----
export function risks(c) {
  const out = [];
  if (c.gh_archived) out.push("the source repository is ARCHIVED");
  if (c.npm_deprecated) out.push("the npm package is marked DEPRECATED");
  if (c.registry_status === "deprecated") out.push("DEPRECATED in the MCP registry");
  if (c.registry_status === "deleted") out.push("REMOVED from the MCP registry — its policy lists spam, malware or illegal content as the usual reasons. Do not install it; tell the user plainly.");
  if (c.similar_official) out.push(`an official package with a similar name exists: ${c.similar_official} — check you meant this one`);
  if (c.vitality === "abandoned") out.push("no recent activity — looks abandoned");
  if (c.single_maintainer) out.push("single primary maintainer (bus-factor risk)");
  if (c.rated === false) out.push("catalogued but not rated — no per-item evidence yet");
  return out;
}

// A PERSON DESCRIBES A JOB, NOT A PACKAGE. search() in the CLI matches names and npm scopes, which is
// right when you already know what you want — but the whole point of this server is the user who does
// not. "search the web" matched nothing at all, because no capability is called that. So the task
// phrase is mapped onto the taxonomy first, and name matching is the fallback rather than the entry.
// Keyed off the 15 categories in web/data/categories.json; keep in step with merge_categories.py.
const TASK_WORDS = {
  search: ["search", "web search", "google", "look up", "research", "find information", "browse the web", "scrape", "crawl"],
  browser: ["browser", "chrome", "playwright", "puppeteer", "click", "screenshot", "automate a website", "e2e"],
  docs: ["docs", "documentation", "pdf", "document", "markdown", "notion", "confluence", "write up", "readme"],
  database: ["database", "sql", "postgres", "mysql", "sqlite", "query data", "schema", "mongo"],
  data: ["data", "csv", "spreadsheet", "excel", "analytics", "dataframe", "etl", "pipeline"],
  devtools: ["code", "repo", "git", "github", "pull request", "review", "debug", "test", "lint", "build", "deploy", "ci"],
  cloud: ["cloud", "aws", "azure", "gcp", "kubernetes", "docker", "infrastructure", "terraform", "server"],
  files: ["file", "filesystem", "folder", "directory", "read a file", "write a file", "disk"],
  comms: ["slack", "email", "gmail", "discord", "message", "chat", "notify", "teams", "telegram"],
  design: ["design", "figma", "ui", "ux", "css", "layout", "component", "style", "frontend"],
  finance: ["finance", "stock", "market", "payment", "invoice", "accounting", "crypto", "trading"],
  security: ["security", "vulnerability", "cve", "secret", "audit", "pentest", "compliance"],
  ai: ["llm", "model", "embedding", "prompt", "agent", "rag", "fine-tune", "eval"],
  productivity: ["calendar", "task", "todo", "note", "reminder", "project management", "jira", "linear"],
};

export function inferCategories(task) {
  const t = " " + String(task || "").toLowerCase() + " ";
  const hits = [];
  for (const [cat, words] of Object.entries(TASK_WORDS)) {
    const score = words.reduce((n, w) => n + (t.includes(w) ? w.length : 0), 0);
    if (score) hits.push([cat, score]);
  }
  // longest phrase wins: "web search" should beat a bare "web" appearing in another list
  return hits.sort((a, b) => b[1] - a[1]).map(([c]) => c);
}

// Words that say nothing about which capability is wanted.
const NOISE = new Set(["the", "a", "an", "my", "i", "to", "for", "with", "of", "and", "on", "in", "up",
  "want", "need", "use", "using", "get", "some", "please", "can", "you", "help", "me", "do", "make",
  "work", "working", "how", "what", "is", "it", "that", "this", "from", "into", "server", "mcp", "skill"]);

export function taskTokens(task) {
  return String(task || "").toLowerCase().split(/[^a-z0-9+]+/)
    .filter((w) => w.length > 1 && !NOISE.has(w));
}

/** Rank candidates for a described task.
 *
 *  RELEVANCE BEFORE SCORE, which is the opposite of the board. Taking the top-scored row of an
 *  inferred category gave "send a slack message" -> claude-seo (top of `comms`, nothing to do with
 *  Slack) and "work with PDFs" -> context7 (top of `docs`, a docs-fetcher, not a PDF tool). A high
 *  score for the wrong tool is worse than a lower score for the right one: the agent installs it and
 *  the user concludes the recommendation is noise. So a token the user actually said has to appear in
 *  the capability's name before its score is allowed to matter, and the category is only the tie-break
 *  pool. search() is still consulted first for the case where someone names the package outright. */
export function forTask(all, task, limit) {
  const toks = taskTokens(task);
  const cats = inferCategories(task);
  const hit = (c) => {
    const hay = `${c.name || ""} ${c.npm_pkg || ""} ${c.id || ""}`.toLowerCase();
    // crude singularisation: "PDFs" must find pdf-toolkit, "issues" must find issue. Cheaper and more
    // predictable than a stemmer, and a wrong stem only costs a ranking place, never a wrong answer.
    return toks.filter((t) => hay.includes(t) || (t.endsWith("s") && t.length > 3 && hay.includes(t.slice(0, -1)))).length;
  };
  const scored = all
    .filter((c) => c.tashan_score != null)
    .map((c) => ({ c, m: hit(c), inCat: cats.includes(c.category) ? 1 : 0 }))
    // a name match outranks everything; then being in the inferred category; then the score
    .filter((x) => x.m > 0 || x.inCat)
    .sort((a, b) => (b.m - a.m) || (b.inCat - a.inCat) || (b.c.tashan_score - a.c.tashan_score));

  // search() is name-oriented and does NOT filter on score, so it must be filtered here too: an
  // unscored row means we have no evidence, and handing an agent something we have not measured is
  // exactly the guessing this server exists to replace.
  const named = search(all, task).filter((c) => c.tashan_score != null);
  const seen = new Set(), out = [];
  for (const c of [...named, ...scored.map((x) => x.c)]) {
    if (seen.has(c.id)) continue;
    seen.add(c.id); out.push(c);
    if (out.length >= limit) break;
  }
  return out;
}

const TOOLS = [
  {
    name: "find_capability",
    description:
      "Find an MCP server or agent skill for a task, ranked on public evidence rather than guesswork. "
      + "Use this BEFORE suggesting or installing any MCP server or skill, so the recommendation is "
      + "measured and carries its evidence. Returns the install command for the user's client.",
    inputSchema: {
      type: "object",
      properties: {
        task: { type: "string", description: "What the user wants to do, e.g. 'search the web', 'work with PDFs', 'query postgres'" },
        client: { type: "string", description: "Target client for the install command: claude, cursor, desktop, codex or npx", enum: ["claude", "cursor", "desktop", "codex", "npx"] },
        limit: { type: "number", description: "How many candidates to return (default 3)" },
      },
      required: ["task"],
    },
  },
  {
    name: "check_capability",
    description:
      "Check one named MCP server or skill before installing it: is it maintained, deprecated, "
      + "archived, or shadowing an official package name? Always free. Use this whenever the user "
      + "names a specific capability, or before running any install command you did not get from find_capability.",
    inputSchema: {
      type: "object",
      properties: { name: { type: "string", description: "Capability, npm package or slug, e.g. 'tavily-mcp'" } },
      required: ["name"],
    },
  },
  {
    name: "audit_config",
    description:
      "Audit the agent configuration already on this machine — every MCP server and skill the user "
      + "has installed across Claude Code, Claude Desktop, Cursor, VS Code and Windsurf — and report "
      + "what is dead, deprecated or risky. Reads local files only; nothing is uploaded.",
    inputSchema: { type: "object", properties: {} },
  },
];

// ---- tool implementations (pure-ish; exported for the test) ----
export function renderFind(matches, task, client) {
  if (!matches.length) {
    return `No measured capability matches "${task}".\n\n`
      + `That means we have no evidence, not that nothing exists — say so rather than guessing. `
      + `Browse ${SITE} or try a broader term.`;
  }
  const L = [`Measured candidates for "${task}" (ranked on public evidence):\n`];
  matches.forEach((c, i) => {
    L.push(`${i + 1}. ${pretty(c.name)}${c.official ? ` — official (${c.official})` : ""}`);
    L.push(`   ${evidence(c)}`);
    for (const r of risks(c)) L.push(`   ⚠ ${r}`);
    const snip = installSnippets(c, client || "claude")[0];
    if (snip) L.push(`   install: ${snip.cmd.split("\n")[0]}`);
    L.push(`   details: ${SITE}/capability/${c.slug || slugify(c.id)}.html`);
    L.push("");
  });
  L.push("A tashan score measures adoption and maintenance. It is NOT a security audit — "
    + "we do not read the capability's code. Tell the user that if they ask whether it is safe.");
  return L.join("\n");
}

export function renderCheck(c, name) {
  if (!c) {
    return `"${name}" is not in the tashan index.\n\nThat is unmeasured, not necessarily bad — `
      + `it may be new, private, or named differently. Do not present absence as a warning.`;
  }
  const rs = risks(c);
  const L = [`${pretty(c.name)} — ${evidence(c)}`, ""];
  if (rs.length) {
    L.push("Risks found:");
    for (const r of rs) L.push(`  ⚠ ${r}`);
  } else {
    L.push("No deprecation, archival or name-confusion flags.");
  }
  // If it is dying, the user's next question is always the same one. Answer it here rather than
  // making the agent guess, and say plainly where the answer comes from.
  if (rs.some((r) => /ARCHIVED|DEPRECATED|REMOVED|abandoned/.test(r))) {
    L.push("", "This one is not maintained. `tashan doctor` (free) will tell you if it is in the user's "
      + "config; tashan Pro names a measured replacement — https://tashan.sh/pricing.html");
  }
  L.push("", `Details: ${SITE}/capability/${c.slug || slugify(c.id)}.html`);
  L.push("A tashan score measures adoption and maintenance, not security. We do not read its code.");
  return L.join("\n");
}

async function callTool(name, args) {
  if (name === "find_capability") {
    const all = await rows();
    const list = forTask(all, String(args.task || ""), Math.max(1, Math.min(10, args.limit || 3)));
    return renderFind(list, args.task, args.client);
  }
  if (name === "check_capability") {
    const all = await rows();
    return renderCheck(find(all, String(args.name || "")), args.name);
  }
  if (name === "audit_config") {
    const lk = await lookup();
    const { found, problems } = collect(configLocations(), skillLocations());
    const results = found.map((item) => ({ item, assessment: assess(item, resolve(item, lk)) }));
    const sum = summarize(results);
    const L = [`${sum.total} capabilities installed · ${sum.alert} need attention · ${sum.warn} worth a look`, ""];
    for (const r of results) {
      const notes = r.assessment.notes.map((n) => n.text);
      if (r.assessment.level === "ok" || !notes.length) continue;
      L.push(`${r.assessment.level.toUpperCase()}  ${r.item.id}  (${r.item.client || r.item.kind})`);
      for (const n of notes) L.push(`    ${n}`);
    }
    if (sum.alert === 0 && sum.warn === 0) L.push("Nothing deprecated, archived or abandoned.");
    for (const p of problems) L.push(`could not read ${p.path}: ${p.error}`);
    L.push("", "Read from local files only. Nothing was uploaded.");
    return L.join("\n");
  }
  throw new Error(`unknown tool: ${name}`);
}

// ---- JSON-RPC plumbing ----
export function handshake(params) {
  return {
    protocolVersion: (params && params.protocolVersion) || FALLBACK_PROTOCOL,
    capabilities: { tools: {} },
    serverInfo: { name: NAME, version: VERSION },
    instructions:
      "Before recommending or installing any MCP server or agent skill, call find_capability (to pick "
      + "one on evidence) or check_capability (to vet one the user named). Both are free. Never present "
      + "a tashan score as a security audit.",
  };
}

export async function handle(msg) {
  const { id, method, params } = msg || {};
  const reply = (result) => ({ jsonrpc: "2.0", id, result });
  try {
    if (method === "initialize") return reply(handshake(params));
    if (method === "tools/list") return reply({ tools: TOOLS });
    if (method === "tools/call") {
      const text = await callTool(params.name, params.arguments || {});
      return reply({ content: [{ type: "text", text }] });
    }
    if (method === "ping") return reply({});
    // Notifications carry no id and must never be answered.
    if (id === undefined || id === null) return null;
    return { jsonrpc: "2.0", id, error: { code: -32601, message: `method not found: ${method}` } };
  } catch (e) {
    if (id === undefined || id === null) return null;
    // A tool failure is a RESULT with isError, not a protocol error — the agent should see the text
    // and be able to tell the user, rather than the whole call blowing up.
    if (method === "tools/call") {
      return reply({ content: [{ type: "text", text: `tashan: ${e.message}` }], isError: true });
    }
    return { jsonrpc: "2.0", id, error: { code: -32603, message: String(e.message || e) } };
  }
}

export async function serve() {
  let buf = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    buf += chunk;
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      let msg;
      try { msg = JSON.parse(line); } catch { continue; }   // never die on one bad frame
      const out = await handle(msg);
      if (out) process.stdout.write(JSON.stringify(out) + "\n");
    }
  }
}

import { fileURLToPath } from "node:url";
if (process.argv[1] === fileURLToPath(import.meta.url)) serve();
