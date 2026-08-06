// Tests for GET /capability/<slug>.md, served from sharded data instead of 9,013 files.
//
// Two failure modes matter more than the rest:
//
//   1. THE HASH DIVERGING from pipeline/prerender.py::md_shard(). The Function computes which shard
//      to fetch; if the two ever disagree, every dossier 404s at once — not one, all of them.
//   2. THE FALL-THROUGH. This Function mounts on /capability/*, where 9,013 real .html files live.
//      A mistake here does not degrade the markdown tier, it takes every capability page off the
//      air. `next()` is the runtime's fall-through; fetch(request) re-enters this Function and loops.
//
// Run: node functions/capability/path.test.mjs
import assert from "node:assert";
import { onRequestGet, shard } from "./[[path]].js";

const DOSSIER = "# Tavily\n\n## Facts\n- tashan score: 86.0 / 100\n";
const SLUG = "pkg-tavily-mcp";

let fetched = [];
globalThis.fetch = async (u) => {
  const s = String(u);
  fetched.push(s);
  const m = s.match(/\/data\/md\/(\d+)\.json$/);
  if (!m) return new Response("nope", { status: 404 });
  // Only the shard the slug actually hashes to carries it — proving the Function asked for the
  // right one, not merely that it found the string somewhere.
  const want = String(shard(SLUG)).padStart(2, "0");
  return new Response(JSON.stringify(m[1] === want ? { [SLUG]: DOSSIER } : {}), { status: 200 });
};

const ctx = (path, { nextImpl } = {}) => ({
  request: new Request("https://tashan.sh" + path),
  params: { path: path.replace(/^\/capability\//, "").split("/") },
  next: nextImpl || (async () => new Response("ASSET", { status: 200 })),
});

let n = 0;
const ok = (name, cond, extra = "") => {
  n++;
  assert.ok(cond, name + (extra ? " — " + extra : ""));
  console.log("  ok   " + name);
};

// ---- the .html twins must be untouched ------------------------------------------------------
{
  let called = 0;
  const r = await onRequestGet(ctx("/capability/pkg-tavily-mcp.html", {
    nextImpl: async () => { called++; return new Response("ASSET", { status: 200 }); },
  }));
  ok("a .html dossier falls through to the real file", (await r.text()) === "ASSET");
  ok("via next(), not a re-fetch of the same URL", called === 1);
  ok("and no shard is fetched for it", fetched.length === 0);
}

// ---- the markdown tier -----------------------------------------------------------------------
{
  fetched = [];
  const r = await onRequestGet(ctx(`/capability/${SLUG}.md`));
  ok("a dossier is served from its shard", (await r.text()) === DOSSIER);
  ok("it fetched exactly the shard the hash names",
     fetched.length === 1 && fetched[0].endsWith(`/${String(shard(SLUG)).padStart(2, "0")}.json`),
     fetched.join(","));
  // Without this a .md downloads instead of rendering, and several crawlers skip an attachment
  // outright. _headers does not apply to Function responses, so the Function must set it.
  ok("served as text/markdown", r.headers.get("content-type") === "text/markdown; charset=utf-8");
  ok("and CORS-open", r.headers.get("access-control-allow-origin") === "*");
}
{
  // A warm isolate must not refetch — 9,013 dossiers across 64 shards means the same shard is hit
  // constantly, and an uncached Function would fetch its own origin on every request.
  fetched = [];
  await onRequestGet(ctx(`/capability/${SLUG}.md`));
  ok("a second request for the same shard is served from memory", fetched.length === 0);
}
{
  const r = await onRequestGet(ctx("/capability/pkg-not-a-real-thing.md"));
  ok("an unknown slug falls through so the site 404s in its own voice",
     (await r.text()) === "ASSET");
}
{
  // Path traversal / junk must never reach a fetch.
  fetched = [];
  for (const bad of ["/capability/..%2F..%2Fetc%2Fpasswd.md", "/capability/UPPER.md", "/capability/.md"]) {
    const r = await onRequestGet(ctx(bad));
    assert.strictEqual(await r.text(), "ASSET", bad);
  }
  ok("a malformed slug is refused before any fetch", fetched.length === 0);
}
{
  globalThis.fetch = async () => new Response("boom", { status: 500 });
  const r = await onRequestGet(ctx("/capability/pkg-uncached-" + Date.now() + ".md"));
  // Never an empty 200: a blank dossier reads to a summariser as a capability with nothing on it,
  // rather than as an outage.
  ok("an unreachable shard is an error, never an empty dossier",
     r.status === 502 || (await r.text()) === "ASSET", "status " + r.status);
}

console.log(`\ncapability .md route: ${n}/${n} passed · all green`);
