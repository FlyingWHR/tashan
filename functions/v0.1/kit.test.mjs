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
  "pkg:good-a", "pkg:good-b", "pkg:sick", "pkg:dead", "pkg:remote" ] } };

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
  ],
};

const withFetch = async (fn) => {
  const real = globalThis.fetch;
  globalThis.fetch = async (u) => (String(u).includes("/data/tags.json")
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
  ok("no credential: 200 with a shortlist", status === 200 && body.shortlist.length === 3);

  const ids = body.shortlist.map((s) => s.id);
  ok("A CAPABILITY WITH A LIVE ADVISORY IS NEVER RECOMMENDED, even scoring highest",
     !ids.includes("pkg:sick"),
     "pkg:sick scores 97 — the highest in the set — and has 3 advisories");
  ok("...nor a deprecated and archived one", !ids.includes("pkg:dead"));
  ok("the shortlist is ranked by score", body.shortlist[0].id === "pkg:good-a");

  ok("what was EXCLUDED is named, with the reason — that is a risk, so it is free",
     body.excluded.length === 2
     && body.excluded.some((e) => e.id === "pkg:sick" && e.why_not.some((w) => /advisory/.test(w)))
     && body.excluded.some((e) => e.id === "pkg:dead" && e.why_not.some((w) => /deprecated/.test(w))),
     JSON.stringify(body.excluded));

  ok("each pick says why, from its own measured columns",
     /scores 91/.test(body.shortlist[0].because) && /deep documentation/.test(body.shortlist[0].because),
     body.shortlist[0].because);
  ok("each pick links to its own source, because we do not host it",
     body.shortlist.every((s) => s.source && s.source.includes("npmjs.com")));
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
     body.free_result && body.free_result.shortlist.length === 3 && body.free_result.excluded.length === 2);
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
     body.shortlist.length === 3 && body.excluded.length === 2);
}

// ---- shape ----------------------------------------------------------------------------------------
{
  const { status, body } = await read(await post({ task: "no-such-task" }));
  ok("an unknown task is a 404 that points at the task list",
     status === 404 && /tags.json/.test(body.tasks));
  const { status: s2 } = await read(await post({}));
  ok("a missing task is a 400", s2 === 400);
  const g = await read(await onRequestGet());
  ok("GET documents the endpoint instead of 404ing", g.status === 400 && g.body.usage.method === "POST");
  ok("...and says plainly what we do not sell", /do not sell/i.test(g.body.usage.not_sold));
}

console.log(`\nv0.1 kit: ${n}/${n} passed · all green`);
