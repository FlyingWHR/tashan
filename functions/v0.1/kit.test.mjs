// node functions/v0.1/kit.test.mjs
//
// The highest-priced thing we sell, so the invariants matter most here: never recommend something
// with a live advisory, never gate a risk, never claim to sell somebody else's content.
import assert from "node:assert";
import { onRequestPost, onRequestGet } from "./kit.js";

let n = 0;
const ok = (name, cond, extra = "") => {
  n++;
  assert.ok(cond, name + (extra ? " — " + extra : ""));
  console.log("  ok   " + name);
};

const TAGS = { generated_at: "2026-08-14", tasks: { "web-scraping": [
  "pkg:good-a", "plugin:acme/pack/thing", "skill:acme/helper", "pkg:good-b",
  "pkg:sick", "pkg:dead", "pkg:remote" ] } };

const rec = (o) => ({ rated: true, vitality: "active", ...o });
const LOOKUP = {
  generated_at: "2026-08-14T00:00:00Z", scorer: "s5",
  records: [
    rec({ id: "pkg:good-a", name: "good-a", label: "Good A", slug: "pkg-good-a", tashan_score: 91,
          npm_pkg: "good-a", npm_latest_version: "2.1.0", sec_advisory_count: 0, sec_provenance: 1,
          npm_downloads: 120000, expertise_verdict: "deep", sec_scanned_at: "2026-08-13T00:00:00Z" }),
    rec({ id: "pkg:good-b", name: "good-b", label: "Good B", slug: "pkg-good-b", tashan_score: 84,
          npm_pkg: "good-b", npm_latest_version: "0.4.2", sec_advisory_count: 0 }),
    rec({ id: "pkg:sick", name: "sick", slug: "pkg-sick", tashan_score: 97,
          npm_pkg: "sick", npm_latest_version: "9.9.9", sec_advisory_count: 3 }),
    rec({ id: "pkg:dead", name: "dead", slug: "pkg-dead", tashan_score: 95,
          npm_pkg: "dead", npm_deprecated: 1, gh_archived: 1 }),
    rec({ id: "pkg:remote", name: "remote", slug: "pkg-remote", tashan_score: 70,
          npm_pkg: "remote", npm_latest_version: "1.0.0", sec_advisory_count: 0,
          remote_host: "mcp.remote.example" }),
    // A plugin and a skill: on a shelf, ranked, and NOT expressible as an mcpServers entry.
    rec({ id: "plugin:acme/pack/thing", name: "thing", slug: "plugin-acme-pack-thing",
          tashan_score: 88, source_repo: "acme/pack" }),
    rec({ id: "skill:acme/helper", name: "helper", slug: "skill-acme-helper",
          tashan_score: 82, source_repo: "acme/helper" }),
  ],
};

const TASKS = { tasks: [
  { slug: "web-scraping", label: "Web scraping", synonyms: ["crawler", "extraction", "scraping", "web scraping"] },
  { slug: "database-access", label: "Database access", synonyms: ["sql", "query databases"] },
  { slug: "code-review", label: "Code review", synonyms: ["review a pull request"] },
] };

const withFetch = async (fn) => {
  const real = globalThis.fetch;
  globalThis.fetch = async (u) => (String(u).includes("/data/tasks.json")
    ? { ok: true, json: async () => TASKS }
    : String(u).includes("/data/tags.json")
    ? { ok: true, json: async () => TAGS }
    : { ok: true, json: async () => LOOKUP });
  try { return await fn(); } finally { globalThis.fetch = real; }
};
const post = (body, { headers = {}, env = {}, stubLicence } = {}) => {
  const run = () => onRequestPost({
    request: new Request("https://tashan.sh/v0.1/kit", {
      method: "POST", headers: { "content-type": "application/json", ...headers },
      body: JSON.stringify(body),
    }),
    env,
  });
  if (!stubLicence) return withFetch(run);
  const real = globalThis.fetch;
  globalThis.fetch = async (u) => (String(u).includes("/data/tags.json")
    ? { ok: true, json: async () => TAGS }
    : String(u).includes("/data/lookup.json")
      ? { ok: true, json: async () => LOOKUP }
      : { ok: true, status: 200, json: async () => stubLicence });
  return run().finally(() => { globalThis.fetch = real; });
};
const read = async (r) => ({ status: r.status, body: await r.json(), headers: r.headers });

// ---- the free shortlist ---------------------------------------------------------------------------
{
  const { status, body } = await read(await post({ task: "web-scraping" }));
  ok("no credential: 200 with a shortlist", status === 200 && body.shortlist.length === 5,
     String(body.shortlist.length));

  const ids = body.shortlist.map((s) => s.id);
  ok("A CAPABILITY WITH A LIVE ADVISORY IS NEVER RECOMMENDED, even scoring highest",
     !ids.includes("pkg:sick"),
     "pkg:sick scores 97 — the highest in the set — and has 3 advisories");
  ok("...nor a deprecated and archived one", !ids.includes("pkg:dead"));
  ok("the shortlist is ranked by score",
     body.shortlist[0].id === "pkg:good-a" && body.shortlist[1].id === "plugin:acme/pack/thing",
     body.shortlist.map((s) => s.id).join(","));

  ok("what was EXCLUDED is named, with the reason — that is a risk, so it is free",
     body.excluded.length === 2
     && body.excluded.some((e) => e.id === "pkg:sick" && e.why_not.some((w) => /advisory/.test(w)))
     && body.excluded.some((e) => e.id === "pkg:dead" && e.why_not.some((w) => /deprecated/.test(w))),
     JSON.stringify(body.excluded));

  ok("each pick says why, from its own measured columns",
     /scores 91/.test(body.shortlist[0].because) && /deep documentation/.test(body.shortlist[0].because),
     body.shortlist[0].because);
  ok("EVERY pick links to its own source — npm for packages, the repo for plugins and skills",
     body.shortlist.every((s) => s.source
       && (s.source.includes("npmjs.com") || s.source.includes("github.com"))),
     JSON.stringify(body.shortlist.map((s) => s.source)));
  ok("the licence line disclaims redistributing anyone's content",
     /do not redistribute/i.test(body.licence) && /own licence/i.test(body.licence));
  ok("no kit in the free response", body.kit === undefined);
  ok("...but it says what the kit would add", Boolean(body.kit_available));
}

// ---- the kit is not assembled without payment -----------------------------------------------------
{
  const r = await post({ task: "web-scraping", kit: true });
  const { status, body } = await read(r);
  ok("kit without a credential is 402", status === 402);
  ok("no kit in the refusal", body.kit === undefined);
  ok("THE FREE SHORTLIST AND THE EXCLUSIONS ARE STILL RETURNED with the 402",
     body.free_result && body.free_result.shortlist.length === 5 && body.free_result.excluded.length === 2);
  ok("unconfigured x402: no accepts, no header",
     body.accepts === undefined && !r.headers.get("payment-required"));
}

// ---- paid: the assembly ---------------------------------------------------------------------------
{
  const { status, body } = await read(await post(
    { task: "web-scraping", kit: true, client: "cursor" },
    { headers: { authorization: "Bearer real" }, env: { POLAR_ORG_ID: "org" },
      stubLicence: { status: "granted" } }));
  ok("a valid licence assembles the kit", status === 200 && Boolean(body.kit));

  const pinned = body.kit.pinned.find((p) => p.id === "pkg:good-a");
  ok("EVERY PICK IS PINNED to a version, not left as latest",
     body.kit.pinned.every((p) => /@\d/.test(p.install)),
     JSON.stringify(body.kit.pinned.map((p) => p.install)));
  ok("...and the pin carries the version the scan actually cleared",
     pinned.version_checked === "2.1.0" && pinned.advisories_at_that_version === 0
     && pinned.scanned_at === "2026-08-13T00:00:00Z");

  ok("the config targets the client that was asked for",
     body.kit.client === "cursor" && body.kit.config_file === "~/.cursor/mcp.json");
  const servers = body.kit.config.mcpServers;
  ok("the config is ready to paste, with pinned args",
     servers["good-a"].command === "npx" && servers["good-a"].args.includes("good-a@2.1.0"),
     JSON.stringify(servers));
  ok("remote alternatives are surfaced where they exist",
     body.kit.remote_alternatives.some((x) => x.host === "mcp.remote.example"));
  ok("the free half is still present alongside the paid half",
     body.shortlist.length === 5 && body.excluded.length === 2);
}

// ---- not everything on a shelf is an mcpServers entry ---------------------------------------------
// 60% of picks on some real jobs are plugins and skills. A plugin is added from a marketplace and a
// skill is a folder you drop in — neither is a command a host can launch. Returning a five-row
// shortlist and a two-row config without saying why is a silent shortfall in a paid artifact.
{
  const { body } = await read(await post({ task: "web-scraping", limit: 5 }));
  const plug = body.shortlist.find((s) => s.id === "plugin:acme/pack/thing");
  const skill = body.shortlist.find((s) => s.id === "skill:acme/helper");
  ok("a plugin links to its own repository, not to nothing",
     plug.source === "https://github.com/acme/pack", plug.source);
  ok("a skill does too", skill.source === "https://github.com/acme/helper", skill.source);
  ok("each pick says how it is installed",
     plug.install_via === "claude-plugin" && skill.install_via === "agent-skill",
     plug.install_via + "/" + skill.install_via);

  const paid = await read(await post(
    { task: "web-scraping", kit: true, limit: 5 },
    { headers: { authorization: "Bearer real" }, env: { POLAR_ORG_ID: "org" },
      stubLicence: { status: "granted" } }));
  const k = paid.body.kit;
  ok("the config contains ONLY things a host can launch",
     Object.keys(k.config.mcpServers).every((n) => !/thing|helper/.test(n)),
     JSON.stringify(Object.keys(k.config.mcpServers)));
  ok("EVERY pick the config cannot express is listed, with how to install it instead",
     k.not_in_config.length === 2
     && k.not_in_config.every((x) => x.say && x.source),
     JSON.stringify(k.not_in_config));
  ok("...and the shortfall is explained in words, not left as arithmetic",
     k.not_in_config.some((x) => /marketplace/.test(x.say))
     && k.not_in_config.some((x) => /\.claude\/skills/.test(x.say)));
}

// ---- an agent speaks in sentences, not slugs ------------------------------------------------------
// Requiring the caller to already know our vocabulary makes the paid endpoint useless to exactly
// the caller it exists for: an agent holding a sentence from a user, that has never seen this API.
{
  const { body } = await read(await post({ goal: "I need to scrape websites for a client" }));
  ok("a plain-language goal resolves to a job", body.task === "web-scraping", JSON.stringify(body.task));
  ok("...and says WHICH sentence it matched, so the caller can disagree",
     body.resolved_from === "I need to scrape websites for a client");
  ok("...and still returns the shortlist", body.shortlist.length === 5);

  const { body: b2 } = await read(await post({ goal: "query databases with sql" }));
  ok("a different goal resolves to a different job", b2.task === "database-access", b2.task);

  const { status, body: b3 } = await read(await post({ goal: "xyzzy plugh" }));
  ok("an unmatchable goal is a 400 that names the alternative, NOT a wrong kit",
     status === 400 && /could not match/.test(b3.error) && /task/.test(b3.error),
     JSON.stringify(b3));

  const { body: b4 } = await read(await post({ task: "code-review", goal: "scrape websites" }));
  ok("an explicit task always beats a goal", b4.task === "code-review" && !b4.resolved_from);
}

// ---- the default client, which the paid path crashed on -------------------------------------------
// CLIENTS[fallback] ? body.client : fallback — the guard tested the fallback and assigned the
// ABSENT value, so `client` was undefined and assemble() threw on CLIENTS[undefined].file. Only the
// paid path assembles, so this was invisible until someone paid.
{
  const { status, body } = await read(await post(
    { task: "web-scraping", kit: true },                       // no `client`
    { headers: { authorization: "Bearer real" }, env: { POLAR_ORG_ID: "org" },
      stubLicence: { status: "granted" } }));
  ok("a kit with no client defaults to claude-code instead of throwing",
     status === 200 && body.kit.client === "claude-code", "status " + status);
  ok("...and the config file path is the real one",
     body.kit.config_file === "~/.claude.json", body.kit && body.kit.config_file);

  const { body: b2 } = await read(await post(
    { task: "web-scraping", kit: true, client: "nonsense-editor" },
    { headers: { authorization: "Bearer real" }, env: { POLAR_ORG_ID: "org" },
      stubLicence: { status: "granted" } }));
  ok("an unknown client falls back rather than producing a config for nothing",
     b2.kit.client === "claude-code", b2.kit && b2.kit.client);
}

// ---- shape ----------------------------------------------------------------------------------------
{
  const { status, body } = await read(await post({ task: "no-such-task" }));
  ok("an unknown task is a 404 that points at the task list",
     status === 404 && /tags.json/.test(body.tasks));
  const { status: s2 } = await read(await post({}));
  ok("a missing task is a 400", s2 === 400);
  const g = await read(await onRequestGet({ request: new Request("https://tashan.sh/x"), env: {} }));
  // A NAKED GET IS A DISCOVERY PROBE — it answered 400 with no payment terms, so x402 crawlers
  // read this as "not a paid endpoint". It still explains how to POST.
  ok("GET still explains how to POST", g.body.usage && g.body.usage.method === "POST");
  ok("...but answers 402 so discovery can see the price", g.status === 402);
  ok("...and says plainly what we do not sell", /do not sell/i.test(g.body.usage.not_sold));
}

console.log(`\nv0.1 kit: ${n}/${n} passed · all green`);
