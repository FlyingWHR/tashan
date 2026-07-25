# tashan — architecture at App-Store scale (decision doc)

> Builds on [ARCHITECTURE.md](ARCHITECTURE.md) (today's static delivery layer). This answers the
> next question: what carries us from 800 capabilities to **tens of thousands → millions**, weighing
> **performance and price**. TL;DR — the "proper" architecture (Cloudflare Workers + D1 + FTS5 +
> on-demand SSR) costs **~$5/mo flat at 100k caps and ~$5–45/mo at 1M**. It is not meaningfully more
> expensive than the cheap hack, so per the founder's rule ("if the proper one doesn't cost much, use
> the proper one") there is no interim step worth building.

## TL;DR — the recommendation

Keep the parts that already scale (the inline-data detail-page technique), move the two that don't
(the ship-all-rows board index, and one-HTML-file-per-cap) to the edge — but **not yet**. The current
static model is correct and free up to ~15–20k caps.

| Stage | Caps | Detail pages | Board + search | Backend | Cost |
|---|---|---|---|---|---|
| **Now** | 800 → ~15k | Prerender-all static (keep) | Client-side over slim `index.json` (keep) | None | **$0** |
| **100k** (or when marketplace writes ship) | 15k → 100k | Hybrid: prerender top ~10k as assets, **SSR + edge-cache** the long tail | **Worker + D1 FTS5 (BM25)** + server pagination | Workers + D1 | **~$5/mo** |
| **1M** | 100k → 1M+ | SSR-on-demand + edge cache (keep top-N prerendered) | D1 FTS5 keyword; **Vectorize** for semantic when it earns it | Workers + D1 + R2 + KV + Vectorize | **~$5–45/mo** |

---

## 1. Where the static-prerender approach breaks

Today: 800 caps → 800 HTML files (~7 KB each), `index.json` 324 KB / **29 KB gz**, `capabilities.json`
1.2 MB / ~110 KB gz (a bulk export, **never fetched at runtime**), `web/` ≈ 11 MB. Everything is linear
in cap count, so extrapolate:

**At 10k caps — still fine, the slim index starts to hurt.** 10k HTML files < 20k free-plan cap; slim
index ~370 KB gz shipped to every board visitor to render the top rows (wasteful but survivable);
client `⌘K` search does 10k string scans per keystroke (sluggish but debounce-able). **Static holds.**

**At 100k caps — the static model is dead. Three independent hard walls:**
- **File count.** Cloudflare Pages / Workers-Assets cap deployments at **20,000 files (free) / 100,000
  (paid)**. 100k caps + CSS/JS/learn/sitemap blows the paid cap; you blow the *free* cap at ~20k caps.
- **Build.** Rendering + git-committing 100k HTML files (~700 MB tree) won't survive the **20-minute
  Pages build timeout** and is untenable in version control.
- **Slim index.** ~35 MB raw / ~3.5 MB gz to every visitor — dead on arrival.
- **Sitemap.** 100k URLs exceeds the sitemap spec's **50,000-URL / 50 MB** ceiling → must split into a
  sitemap index.
- **Client search over 100k rows: impossible to keep snappy.**

**At 1M caps — not even a question.** 1M files is 10× over the hard cap and can't be built or committed.
Slim index ≈ 35 MB gz. Everything must be server-driven.

**The key nuance:** the inline-data island technique (`prerender.py:inline_data()` → `capability.js`
fast-path) scales to *any* cap count — the per-page payload is 0 bytes fetched. What breaks is **file
count and build time**, not the rendering technique. So the fix is to keep producing that exact HTML,
but produce it **at request-time in a Worker** instead of at build-time-into-a-file.

---

## 2. The snappy-at-scale architecture, Cloudflare-first

Build new work on **Workers with Static Assets** (Wrangler ≥ 4.34) rather than Pages — same static
serving, but one deploy unifies static assets + SSR + D1/KV/R2/Vectorize bindings.

| Primitive | Role in tashan |
|---|---|
| **Workers (Static Assets)** | Serve prerendered top-N pages + CSS/JS as free, unlimited static assets (not billed). |
| **Workers (SSR)** | On-demand render the long-tail detail pages + the board/search endpoints. Runs only on cache miss. |
| **D1** (SQLite at edge) | The read snapshot (`capabilities`) **and** the write tables (listings, sales, accounts, reviews). The pipeline's SQLite schema ports as-is. FTS5 lives here. |
| **Cache API / edge cache** | `Cache-Control: public, s-maxage=…, stale-while-revalidate` on SSR responses → repeat views served from CDN edge with **no Worker invocation, no bill**. |
| **KV** | Hot, rarely-changing config: feature flags, category metadata, homepage "top" lists, sessions. |
| **R2** | The marketplace delivery CDN — the actual skill/server bundles sold, plus generated OG images. **Egress is free** (decisive for a delivery service). |
| **Vectorize** | Semantic "find similar" / NL search — added at 1M *only when the product wants it*. |

**Detail pages: SSR-on-demand + edge cache (keep the inline-data trick).** Port `prerender.py`'s
`page()`/`summary()`/`jsonld()` into a Worker template. On a request: `SELECT … WHERE slug = ?` (indexed
point lookup) → render the identical HTML including the same `<script type="application/json"
id="cap-data">` island → return with `s-maxage` so the CDN caches it. **Hybrid is the recommendation:**
keep prerendering the top ~10k most-trafficked caps as static assets (fastest, free, best for crawlers)
and SSR the long tail on demand.

**Board search + pagination: D1 FTS5, decisively.** D1 supports SQLite **FTS5 with BM25** natively —
full-text search in the same DB, co-located with the Worker, no external service. The board becomes a
Worker endpoint doing `MATCH` + `ORDER BY rank` + keyset pagination. (Caveat: FTS5 virtual tables can't
be D1-exported — drop/recreate them around exports.)

Search decision per scale: **now→10k** client-side over the slim index (already good, keep it);
**10k→1M** D1 FTS5 (free, in-DB, edge-local); **semantic (1M)** add Vectorize when the product wants it.
Algolia is cost-disqualified at App-Store record counts (see §3); Typesense only if you need
instant-search-as-you-type typo-tolerance BM25 can't match.

**OG images at scale:** do not prerender 1M PNGs. Generate on demand in a Worker (satori/resvg or
Browser Rendering), cache-key by `slug + data-hash`, store in R2 + CDN edge.

---

## 3. Cost analysis — concrete, per tier

Assumptions: 85% detail / 15% board traffic; detail SSR ~95% edge-cache hit; ~2 KB/row in D1.
10k caps → 1M pv/mo · 100k caps → 10M pv/mo · 1M caps → 50M pv/mo.

**Cloudflare-first (the recommendation):**
- **@ 100k caps / 10M pv:** ~1.2M Worker requests (of 10M included), D1 reads well under the 25B/mo
  included, storage ~0.4 GB (of 5 GB). → **$5/mo** (just the Workers Paid base fee).
- **@ 1M caps / 50M pv:** ~5.9M Worker requests (under 10M included), D1 reads ~3.75B (under 25B),
  storage ~4 GB. → **$5/mo**, plus Vectorize *if semantic is on*: ~$0.38/mo storage + ~$13–38/mo
  queried-dims (halve with 256-dim vectors). → **$5–45/mo total.**

> **10 GB D1 cap:** at ~1M caps + FTS5 you approach it. Fix: keep heavy blob fields (long descriptions,
> install snippets, artifacts) in R2/KV, keep D1 lean for query; or shard (50,000 DBs/account on paid).

**The comparison @ 1M caps / 50M pv:**

| Stack | Est. monthly | Why |
|---|---|---|
| **Cloudflare (recommended)** | **$5–45** | Asset serving free; edge-cached SSR bills only misses; D1 FTS5 free; R2 egress free |
| **Vercel** | **~$100–120** | $20 base + edge requests 10M incl then $2/M → 40M billable = $80; + functions + ISR |
| **Algolia (search only)** | **~$2,850** | 900k records × $0.40/1k + 5M searches × $0.50/1k — disqualifying |
| **Typesense Cloud (search only)** | **~$36–75** | RAM-priced always-on node for a 1M-doc index; not edge-local |

The punchline the founder suspected is correct: **the proper Cloudflare architecture is the cheapest
option and cheap in absolute terms.** Vercel's edge-request billing is ~10–20× CF at this scale;
Algolia's per-record + per-search model explodes at App-Store record counts.

---

## 4. Reads vs writes — how they coexist

**Reads stay static/edge-cached, effectively free:** top-N caps → prerendered static assets; long-tail
detail + board → SSR Workers with `s-maxage` → CDN serves repeats with no Worker bill; D1 queried only
on cache miss.

**Writes need D1 + Workers** (the marketplace: listings, sales, accounts, reviews; the rendering /
delivery service):
- **New tables alongside the snapshot** (`listings`, `sales`, `accounts`, `reviews`) — the build
  pipeline keeps owning the `capabilities` snapshot; writes never touch it, so it can rebuild anytime.
- Worker endpoints behind auth (Stripe webhook → Worker → D1 for payments).
- **On write, purge the affected cached read URLs** (targeted purge / cache tags) so reads stay fresh
  without going dynamic everywhere.
- **R2** stores sold artifacts (free egress = the delivery CDN). **Durable Objects** only where you
  need per-object coordination (live inventory counters, per-account rate limits) — add when contention
  demands it. If board/search read volume outgrows one D1, use **D1 read replication** (writes stay on
  one primary).

---

## 5. Staged migration path + triggers

**Stage 0 — Now (800 → ~15k caps): do nothing structural.** The static model is correct and free. Keep
prerender-all, the slim index, client-side search.
- **Trigger to move:** file count > ~15k, OR slim `index.json` > ~400 KB gz, OR board TTI > 1s, OR
  marketplace writes ship — whichever comes first.

**Stage 1 — ~100k / marketplace launch: adopt the Workers + D1 spine (go straight to proper).** Move to
Workers (Static Assets); import the snapshot into D1. Board → Worker + D1 FTS5 + server pagination
(retire the ship-all-rows index). Detail → hybrid (prerender top ~10k, SSR + edge-cache the rest).
Sitemap → sitemap index. Add write tables + Worker endpoints; purge-on-write for cache coherence.
- **Trigger to move on:** caps > 20k (blows the free file cap) OR writes ship.

**Stage 2 — ~1M: fully server-driven reads, keep the head prerendered.** Detail: SSR-on-demand + edge
cache, top-N prerendered. Search: D1 FTS5 keyword + Vectorize semantic when the product wants it. R2 as
artifact + OG-image CDN; KV for hot config/flags/sessions. Move heavy blobs to R2/KV to stay under the
10 GB D1 cap; shard if needed.
- **Trigger:** D1 approaching 10 GB, search latency, or query volume beyond a single index.

---

## Sources

Cloudflare [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) ·
[D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) /
[limits](https://developers.cloudflare.com/d1/platform/limits/) /
[SQL & FTS5](https://developers.cloudflare.com/d1/sql-api/sql-statements/) ·
[KV](https://developers.cloudflare.com/kv/platform/pricing/) ·
[R2](https://developers.cloudflare.com/r2/pricing/) ·
[Vectorize](https://developers.cloudflare.com/vectorize/platform/pricing/) ·
[Pages limits](https://developers.cloudflare.com/pages/platform/limits/) ·
[increased asset limits (20k/100k)](https://developers.cloudflare.com/changelog/post/2025-09-02-increased-static-asset-limits/) ·
[Vercel pricing](https://vercel.com/pricing) · [Algolia pricing](https://www.algolia.com/pricing) ·
[Typesense Cloud pricing](https://cloud.typesense.org/pricing)
