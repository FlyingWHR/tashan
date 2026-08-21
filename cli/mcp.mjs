#!/usr/bin/env node
// tashan as an MCP server — the measured layer, inside the agent's decision loop.
//
//   claude mcp add tashan -- npx -y tashan-cli mcp        <- the one install string
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

import { realpathSync } from "node:fs";
import { disp, search, find, installSnippets, pretty, slugify, advisoriesOf, installScriptOf,
         resolveLicence } from "./tashan.mjs";
import { tokensOf } from "./doctor.mjs";
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
  // The security audit, in the agent's own words. An agent is the LAST checkpoint before something
  // gets installed on a machine, so it must be told the same findings a person gets — free, and
  // phrased so it can act rather than paraphrase a score.
  if (c.sec_max_severity === "MALICIOUS")
    out.push("listed in OSV's malicious-packages database — this package IS the attack. Do not install it. Tell the user plainly and stop.");
  else if (c.sec_advisory_count) {
    // NAME THEM WHEN WE HAVE THEM. This line used to end "see the capability page for which" on every
    // surface — the paywall speaking, since the detail was stripped from everything the CLI could
    // read and pointing elsewhere was the only honest option left. sec_advisories is public now, so
    // the ids go in the risk line itself; find_capability has no detail block under it, and an agent
    // that can quote an id can act. The pointer stays as the fallback for the slim board record,
    // which still carries the count but not the advisories.
    const ids = advisoriesOf(c).map((a) => a.id).filter(Boolean);
    out.push(`${c.sec_advisory_count} known advisor${c.sec_advisory_count === 1 ? "y" : "ies"} against the current release (${(c.sec_max_severity || "unrated").toLowerCase()})`
      + (ids.length ? ` — ${ids.join(", ")}` : " — see the capability page for which"));
  }
  if (c.sec_install_script)
    out.push("runs a script at install time — arbitrary code executes on npm install, before any tool is called");
  if (c.sec_permissions) {
    try {
      const perms = JSON.parse(c.sec_permissions);
      if (perms.length) out.push(`declared permission surface: ${perms.join(", ")} — tell the user what it can reach before installing`);
    } catch { /* a malformed field must never break the agent's risk report */ }
  }
  if (c.vitality === "abandoned") out.push("no recent activity — looks abandoned");
  if (c.single_maintainer) out.push("single primary maintainer (bus-factor risk)");
  // "No per-item evidence yet" is the right sentence for a row nobody has measured, and the WRONG
  // one for a row we refused to rate. A malicious or discontinued package is unrated because
  // eligibility overrides score, not because we are missing data — saying "no evidence yet" about a
  // confirmed attack understates it, and `rating_basis` already carries the real reason.
  if (c.rated === false && !c.rating_basis)
    out.push("catalogued but not rated — no per-item evidence yet");
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

/** Rank candidates for a described task, on what a capability DOES.
 *
 *  Name matching alone returned web-search (57, 112 downloads/wk) ahead of tavily (86, 32k/wk) for
 *  "search the web": tavily's name contains none of those words, its description contains all of them.
 *  lookup.json now ships a token bag per record (built from name + description, with once-seen noise
 *  and >8%-of-corpus topic words already dropped), so the match is against meaning, not spelling.
 *
 *  Scoring is idf-weighted — a rarer shared word is stronger evidence — and the tashan score breaks
 *  ties rather than driving the order, because a well-measured wrong tool is still the wrong tool.
 */
export function forTask(all, task, limit, lookup = null) {
  const stem = (t) => (t.endsWith("s") && t.length > 3 ? t.slice(0, -1) : t);
  const toks = taskTokens(task);
  const cats = inferCategories(task);

  if (lookup && lookup.terms) {
    // Index on the STEM, not the surface form. Otherwise "pdfs" and "pdf" are two tokens with two
    // different rarities, and a capability whose blurb happens to use the plural outranks one using
    // the singular — which is how "work with PDFs" surfaced brandsystem over opendataloader-pdf.
    const df = new Map();
    const bags = lookup.terms.map((b) => new Set(b.split(" ").filter(Boolean).map(stem)));
    for (const bag of bags) for (const t of bag) df.set(t, (df.get(t) || 0) + 1);
    const N = bags.length;
    const scored = [];
    for (let i = 0; i < lookup.records.length; i++) {
      const r = lookup.records[i];
      if (r.tashan_score == null) continue;
      const bag = bags[i] || new Set();
      let rel = 0;
      for (const q of new Set(toks.map(stem))) {
        // Clamped positive. log(N/(1+df)) goes NEGATIVE once a token is in more than about half the
        // corpus, which would make a genuine match count AGAINST the capability that has it. The 8%
        // cut in the pipeline makes that unreachable in production and it is trivially reachable in a
        // small set, so the arithmetic should not depend on the corpus being large.
        if (bag.has(q)) rel += Math.max(0.05, Math.log(N / (1 + (df.get(q) || 1))));
      }
      // NO CATEGORY NUDGE. It was here before descriptions were matchable, as the only signal that a
      // capability was even in the right area. Now the terms bag carries that and the nudge only
      // distorts: a flat +0.5 is worth more than a real token match on a common word, which is how
      // trusty-squire — a website SIGN-UP tool that matched only "website" — kept beating
      // @screenshotink/mcp for "take a screenshot". Categories are 15 buckets with 67% of the corpus
      // in two of them; that is too coarse to outweigh evidence about the words themselves.
      if (rel <= 0) continue;
      // THE MEASUREMENT HAS TO WEIGH ON THE RANKING, not merely break ties. Pure idf rewards a RARE
      // shared word, so "work with PDFs" surfaced morosss-sdfsdf and "manage kubernetes" surfaced two
      // unknown CLIs — junk whose descriptions happened to contain an uncommon token, beating the
      // obvious well-measured answer by a fraction. Multiplying by the score keeps relevance in
      // charge (a twice-better match still wins) while making an unmeasured stranger lose to a
      // comparable match that thousands of people actually run.
      // Exponent swept against a judged set of ten real phrases, not chosen by feel:
      //   0.0 -> 6/10 correct at rank 1   (relevance alone surfaces junk that merely matches)
      //   1.0 -> 8/10                     (score too weak: a partial match still loses to noise)
      //   1.5 -> 10/10                    <- chosen
      //   2.0 -> 9/10                     (score too strong: trusty-squire, which matched only
      //                                    "website", beat @screenshotink/mcp, which matched both
      //                                    "screenshot" and "website", purely on 75 vs 43)
      // Relevance stays in charge; the measurement tilts between comparable matches and cannot
      // overturn a capability that actually matched more of what was asked for.
      const w = r.tashan_score / 100;
      scored.push({ r, rel: rel * Math.pow(w, 1.5) });
    }
    scored.sort((a, b) => (b.rel - a.rel) || (b.r.tashan_score - a.r.tashan_score));
    return scored.slice(0, limit).map((x) => x.r);
  }

  // Fallback for a caller without the terms bag: name matching only, the old behaviour.
  const hay = (c) => `${c.name || ""} ${c.npm_pkg || ""} ${c.id || ""}`.toLowerCase();
  const out = all.filter((c) => c.tashan_score != null
      && toks.some((t) => hay(c).includes(t) || hay(c).includes(stem(t))))
    .sort((a, b) => b.tashan_score - a.tashan_score);
  return out.slice(0, limit);
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
    L.push(`${i + 1}. ${disp(c)}${c.official ? ` — official (${c.official})` : ""}`);
    L.push(`   ${evidence(c)}`);
    for (const r of risks(c)) L.push(`   ⚠ ${r}`);
    const snip = installSnippets(c, client || "claude")[0];
    if (snip) {
      // NEVER take just the first line. Cursor/Codex/Desktop snippets are multi-line JSON or TOML
      // stanzas, and "[mcp_servers.web-search]" on its own is broken config an agent would happily
      // paste into a user's machine.
      const lines = String(snip.cmd).split("\n");
      L.push(`   install (${snip.client}): ${lines[0]}`);
      for (const l of lines.slice(1)) L.push(`     ${l}`);
    }
    L.push(`   details: ${SITE}/capability/${c.slug || slugify(c.id)}`);
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
  // STOP-FIRST FOR CONFIRMED MALWARE. Everything else here reads top-down as description, then
  // caveats — which is right for a deprecated package and wrong for an attack. claude-cup opened
  // with "4,837,320 downloads/wk · active" and put "this package IS the attack" three lines below,
  // where an agent summarising for a human can drop it. The adoption figure still appears further
  // down, because how far it spread is the point; it just no longer arrives first, dressed as
  // popularity.
  if (c.sec_max_severity === "MALICIOUS") {
    return [
      `DO NOT INSTALL ${disp(c)}.`,
      "",
      "It is listed in OSV's malicious-packages database — the package IS the attack, not a package",
      "with a vulnerability. Tell the user plainly and stop; do not add it to any config.",
      "",
      `Measured: ${evidence(c)}`,
      c.npm_downloads
        ? `Its ${c.npm_downloads.toLocaleString()} downloads/wk are a measure of how far it spread, not of quality.`
        : null,
      "",
      ...(rs.length > 1 ? ["Also:", ...rs.filter((r) => !/malicious-packages/.test(r)).map((r) => `  ⚠ ${r}`)] : []),
      // Drop only the absent lines. Filtering every "" — the first version of this — collapsed the
      // paragraph breaks too, and the result read as one undifferentiated block on the one message
      // in this codebase that most needs to be skimmable.
    ].filter((s) => s !== null).join("\n");
  }
  const L = [`${disp(c)} — ${evidence(c)}`, ""];
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
      + "config; tashan Pro names a measured replacement — https://tashan.sh/pricing");
  }
  // THE DETAIL ITSELF, NOT A DESCRIPTION OF WHERE IT IS KEPT.
  // This block used to say "which advisory and the version that fixes it" and "the exact command it
  // runs at install time" were behind a Pro licence, then hand the agent a licensed URL to fetch —
  // while the website printed both to any visitor. So the agent was told to warn and forbidden to
  // act, over facts a browser gives away, and a model told a fix exists but not what it is will
  // either hedge or invent one. The pipeline stopped redacting these (build.py's redact_paid), so
  // they arrive in the public lookup.json, and the agent now gets them the way a reader does.
  const advs = advisoriesOf(c);
  const script = installScriptOf(c);
  if (advs.length) {
    L.push("", "Advisories against the version you would install today:");
    for (const a of advs) {
      L.push(`  ${a.id}  ${(a.severity || "unrated").toLowerCase()}${a.summary ? ` — ${a.summary}` : ""}`);
      // The fixing version is the only actionable line here. "No fix published" has to be said out
      // loud rather than omitted, or the agent reads silence as "already fixed, install away".
      L.push(a.fixed ? `    fixed in ${a.fixed} — pin at or above it, or pick another capability`
                     : "    no fixed version published — treat the current release as affected");
    }
  }
  if (script) {
    L.push("", `Runs this at install time, before any tool is called: ${script}`);
    L.push("Show the user the command itself if they are deciding whether to install.");
  }
  L.push("", `Details: ${SITE}/capability/${c.slug || slugify(c.id)}`);
  L.push("A tashan score measures adoption and maintenance, not security. We do not read its code.");
  return L.join("\n");
}

async function callTool(name, args) {
  if (name === "find_capability") {
    const [all, lk] = [await rows(), await lookup().catch(() => null)];
    const list = forTask(all, String(args.task || ""), Math.max(1, Math.min(10, args.limit || 3)), lk);
    return renderFind(list, args.task, args.client);
  }
  if (name === "check_capability") {
    // THE BOARD IS THE RANKING, NOT THE RECORD, and checking one named capability is a lookup
    // question, not a ranking question. index.json carries 1,592 ranked rows, slimmed for the
    // website's first paint: no sec_advisories, no sec_max_severity, no sec_permissions, and
    // sec_install_script flattened to a bare 1. lookup.json carries all 5,951, in full.
    //
    // Checking the board alone was wrong in both directions. Every row we know an advisory about is
    // OFF the board — low scores never rank, and the two dependency-confusion canaries are dropped
    // from it on purpose — so an agent asking about mcp-server-taskwarrior, which has a command
    // injection advisory, was told "not in the tashan index, unmeasured, not necessarily bad". And
    // for the rows that did match, the slim record had none of the detail to relay.
    //
    // So: match the board (find() does fuzzy name/package matching, which the keyed lookup cannot),
    // overlay the full public record, and fall back to the lookup when the board has never heard of
    // it. Same lookup.json find_capability and audit_config already fetch, same cache, no licence.
    const q = String(args.name || "");
    const [all, lk] = [await rows(), await lookup().catch(() => null)];
    const c = find(all, q);
    const rec = lk ? resolve({ id: c ? c.id : q }, lk) : null;
    return renderCheck(c || rec ? { ...(c || {}), ...(rec || {}) } : null, q);
  }
  if (name === "audit_config") {
    const lk = await lookup();
    const { found, problems } = collect(configLocations(), skillLocations());
    // Keep the RESOLVED ROW, not just the verdict: assess() returns {level, notes} and carries no
    // id, so reading r.assessment.id would have been undefined on every row and the trend block
    // below would have silently sent nothing at all.
    const results = found.map((item) => {
      const row = resolve(item, lk);
      return { item, row, assessment: assess(item, row) };
    });
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

    // THE TREND, WHICH IS THE ONE THING THE LOCAL FILES CANNOT TELL YOU.
    //
    // Everything above is derived from this machine plus the public lookup table: what is dead,
    // deprecated, or impersonating an official name. All free, and it stays free. What no local
    // file knows is DIRECTION — whether a server the user depends on is a project getting better
    // or one quietly sliding. That is the retention series, it is the paid half, and this is the
    // moment it is worth most: the agent is holding the actual list.
    //
    // With a licence we fetch it. Without one we say what it would have told them, sized to THEIR
    // config — a specific number beats a generic upsell, and it is the difference between an offer
    // and a nag. Nothing is uploaded in the free path; the ids only leave the machine when the user
    // has paid and asked for the trend.
    const ids = [...new Set(results.map((r) => r.row && r.row.id).filter(Boolean))];
    const lic = resolveLicence({});
    if (lic && lic.key && ids.length) {
      try {
        const res = await fetch(`${SITE}/v0.1/audit`, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: `Bearer ${lic.key}`,
            ...(lic.activation_id ? { "x-tashan-activation": lic.activation_id } : {}),
          },
          body: JSON.stringify({ servers: ids, history: true }),
        });
        if (res.ok) {
          const { history } = await res.json();
          L.push(...trendBlock({ history }));
        } else if (res.status === 402 || res.status === 403) {
          L.push(...trendBlock({ status: res.status }));
        }
      } catch { /* offline: the audit above is complete and correct on its own */ }
    } else if (ids.length) {
      // NO LICENCE: ask what it would cost, WITHOUT naming anything. The promise two paragraphs up
      // is that these ids leave the machine only once the user has paid, and it holds — the quote
      // carries a count and nothing else. Before this, the agent got a sentence with a price in it
      // and no way to act: an agent with a funded wallet could not pay, and an agent that wanted to
      // was invisible to us. Now it gets the real x402 terms and can decide.
      let quote = null;
      try {
        const res = await fetch(`${SITE}/v0.1/audit`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ history: true, count: ids.length }),
        });
        if (res.status === 402) quote = await res.json();
      } catch { /* offline: the free audit above is complete and correct on its own */ }
      L.push(...trendBlock({ count: ids.length, quote }));
    }
    return L.join("\n");
  }
  throw new Error(`unknown tool: ${name}`);
}


/**
 * The Pro half of an audit, as lines — pure, so it can be tested without a filesystem or a network.
 *
 * Four states, and the distinctions matter more than the wording. "Your licence was refused" and
 * "you have no licence" send someone to two different places, and guessing wrong wastes the one
 * moment they were willing to act. "Nothing moved" is a real, reassuring answer and must not read
 * as a failure to fetch. And the unlicensed pitch is sized to THEIR config, because a specific
 * number is the difference between an offer and a nag.
 */
export function trendBlock({ history, status, count, quote } = {}) {
  if (status === 403) return ["", "tashan Pro: this licence was refused — check https://polar.sh/tashan/portal"];
  if (status === 402) return ["", "tashan Pro would add the trend here — https://tashan.sh/pricing"];
  if (count) {
    // NOT "watches". `watch` is status:planned in entitlements.json — proactive notification does
    // not exist, and the same sentence was being sold from four generators and the pricing page
    // before anyone checked. What ships is the series and a named replacement.
    const L = ["", `tashan Pro adds direction for these ${count} — the whole series behind each, so `
      + "you can tell a project getting better from one on its way down — and names a measured "
      + "replacement when one dies. $6/mo, 7 days free: https://tashan.sh/pricing"];
    // THE TERMS, MACHINE-READABLE, when the deployment quoted them. An agent holding a wallet can
    // act on this; a sentence with a dollar sign in it is only actionable by a human.
    const a = quote && Array.isArray(quote.accepts) && quote.accepts[0];
    if (a && a.amount && a.asset) {
      L.push(`Or pay per call with x402: ${(Number(a.amount) / 1e6).toFixed(2)} USDC on `
        + `${a.network} to ${a.payTo} — POST ${SITE}/v0.1/audit with your servers and a `
        + "PAYMENT-SIGNATURE header. Nothing is named until you do.");
    }
    return L;
  }
  const moved = Object.entries(history || {})
    .filter(([, h]) => h && h.direction && h.direction !== "flat" && Number.isFinite(h.change))
    .sort((a, b) => Math.abs(b[1].change) - Math.abs(a[1].change));
  if (!moved.length) {
    return ["", "tashan Pro: nothing in this config has moved since we started measuring it."];
  }
  const L = ["", "Moving (tashan Pro — the score series behind each one):"];
  for (const [id, h] of moved.slice(0, 12)) {
    L.push(`  ${h.direction === "up" ? "↑" : "↓"} ${id}  ${h.change > 0 ? "+" : ""}${h.change} since ${h.first}`);
  }
  return L;
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
      + "a tashan score as the security audit — they are separate, and both are reported.",
  };
}

export async function handle(msg) {
  const { id, method, params } = msg || {};
  const reply = (result) => ({ jsonrpc: "2.0", id, result });
  try {
    if (method === "initialize") return reply(handshake(params));
    if (method === "tools/list") return reply({ tools: TOOLS });
    if (method === "tools/call") {
      const args = params.arguments || {};
      // A MISSING REQUIRED ARGUMENT IS A CALLER ERROR, NOT A FINDING. Calling find_capability with
      // the wrong property name answered `No measured capability matches "undefined"` — the same
      // sentence we use for a genuine miss. On a measurement product that is the worst possible
      // confusion: a typo in the host's tool call reads as "nothing like this exists", and an agent
      // would relay that to a person as evidence. Say which parameter is missing instead.
      const spec = TOOLS.find((t) => t.name === params.name);
      const missing = ((spec && spec.inputSchema && spec.inputSchema.required) || [])
        .filter((k) => args[k] === undefined || args[k] === null || args[k] === "");
      if (missing.length) {
        return reply({
          isError: true,
          content: [{ type: "text", text:
            `${params.name} requires ${missing.map((m) => `"${m}"`).join(", ")}. `
            + `This is a problem with the call, not a result — do not report it as "nothing found".` }],
        });
      }
      const text = await callTool(params.name, args);
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

// IS THIS FILE THE ENTRY POINT? Compare REAL paths, not the strings.
//
// npm installs a bin as a SYMLINK — node_modules/.bin/tashan -> ../tashan-cli/tashan.mjs — so
// process.argv[1] is the link and import.meta.url resolves to the target. A plain === between them
// is false for every npm install, which meant main() never ran: `tashan --help` exited 0 and printed
// NOTHING. Running the file directly by path worked, so every local test passed and the published
// package would have done nothing at all. Caught only by installing the packed tarball.
function isEntry(metaUrl) {
  if (!process.argv[1]) return false;
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(metaUrl));
  } catch {
    return process.argv[1] === fileURLToPath(metaUrl);
  }
}

if (isEntry(import.meta.url)) serve();
