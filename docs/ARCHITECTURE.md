# tashan — architecture & data-delivery (BE/DB review)

> Answers three questions: why detail pages were slow, whether we need a DB change, and when a
> real backend actually becomes necessary. TL;DR — **no DB change needed now; the fix was in the
> delivery layer, and a live DB is only required for WRITES (requests / watch / Pro), which is
> already the roadmap.**

## 1. How it works today (all static, no runtime backend)

```
public signal ──► Python pipeline ──► SQLite (data/tashan.db)  ──► JSON export ──► static site (web/)
 (npm, GitHub,     (build.py + enrich   THE SOURCE OF TRUTH        (build-time)     (Cloudflare Pages)
  registry,         passes; LLM grading  — a build artifact,
  configs)          in subagents)        not a live DB
```

- **SQLite is a build artifact**, committed to the repo. It is never queried at runtime and is never
  written to from the browser. The site ships as static files; there is no server, no live DB, no auth.
- Reads are served entirely from **pre-generated JSON**. "Routing the query" happens at **build time**
  (we pre-compute exactly what each page needs) instead of at runtime (a DB query per request).

## 2. Why detail pages were slow — and the fix (delivery layer, not the DB)

**Root cause:** every page fetched the **entire 1.2 MB `capabilities.json`** (109 KB gzipped, 800 caps ×
46 fields) — `capability.js`, `index.js`, `terminal.js` (the ticker, on *every* page), and
`methodology.js`. A detail page downloaded all 800 dossiers just to `find()` one. That is the whole
"painfully slow."

**Fix — split the export into three tiers by what each surface actually needs:**

| Surface | Needs | Now served by | Payload |
|---|---|---|---|
| **Detail page** | one cap, all fields | **inline** `<script type="application/json" id="cap-data">` in the prerendered HTML | **0 bytes fetched** |
| **Board / ticker / ⌘K** | all caps, ~15 fields | **slim** `web/data/index.json` | 426 KB → **36 KB gz** |
| **API / bulk download** | all caps, all fields | full `web/data/capabilities.json` (not loaded at runtime) | — |

- Detail pages are now **instant** — the data is in the HTML the crawler already served; `capability.js`
  reads the island (`JSON.parse`) and renders with no network. CSP-safe: `type="application/json"` is a
  non-executable data island, not a script.
- The slim index drops the heavy per-cap fields (`co_used`, `description`, `expertise_note`, `gh_topics`,
  install snippets, repo-health, community) — 3× smaller, so the board/ticker load fast too.
- `SLIM` field list lives in `build.py` `export()`; inline island in `prerender.py` `inline_data()`.

**This required no schema change** — it is purely how the same data is *delivered*.

## 3. When do we actually need a live DB / backend?

Reads do **not** need one — they scale statically. A backend is required only for:

| Feature | Why it needs a backend | Status |
|---|---|---|
| **Requests / demand board** (upvotes, USDC backing, patrons) | writes user state | roadmap (V1 is static + GitHub-issue submit) |
| **Watch / alerts** | per-user subscriptions + notifications | roadmap (Pro wedge) |
| **Pro billing / accounts** | auth + payment state | roadmap |
| **On-demand grading** ($0.20 pay-per-grade) | write + async job | roadmap |
| Full-text search at scale (10k+ caps) | server-side index | not yet (client-side over slim is fine at ~1k) |

Everything currently shipped (Index, detail, filters, sort, badges, learn, methodology) is **read-only
and static-friendly**. No backend is on the critical path today.

## 4. If/when we add the backend — the shape (no rewrite, no schema break)

- **Cloudflare D1** (SQLite-compatible) is the natural choice: the pipeline's SQLite schema ports to D1
  **as-is** — same `CREATE TABLE`, same columns. The pipeline can keep building the read snapshot; D1
  adds only the **write tables** the features above need (`requests`, `backings`, `watches`, `users`),
  which are *new* tables, not changes to `capabilities`.
- **Cloudflare Pages Functions** (already the deploy target) serve the write endpoints; the static site
  stays static. Relax `_headers` CSP (`form-action`, `connect-src`) only for those endpoints.
- Reads stay on the static tiers above; the Function layer is writes + truly-dynamic queries only.
- The existing `signal_history` table (daily trust/adoption snapshots) is the seed for trend charts —
  already accruing; a Function would serve it per-cap when the UI wants sparklines.

## 5. Scaling limits of the static approach

- **Slim index** grows ~linearly with cap count: 800 caps ≈ 36 KB gz; ~5k caps ≈ ~200 KB gz (still fine);
  beyond ~10k, move the board to server-side pagination + a search API (D1/Function or an external
  search index). Detail pages (inline) scale to *any* count — they never grow the per-page payload.
- **Prerender** writes one HTML file per cap (currently 800). At tens of thousands, generation time and
  file count argue for on-demand rendering (a Function) or incremental builds — but that is far off.

## 6. Recommendation

1. **Keep reads static.** The tiered delivery (inline + slim + full) fixes perf and scales to thousands
   of capabilities with no backend. ✅ done.
2. **Add D1 + Pages Functions only for the write features** (requests, watch, Pro) when we build them —
   new tables alongside the existing schema, no migration of `capabilities`.
3. **No DB change is needed for anything shipped today.**

> **Scaling to App-Store size?** When "tens of thousands → millions" is on the table, the staged path,
> the Cloudflare primitives (Workers + D1 FTS5 + on-demand SSR), and the concrete per-tier cost math
> (~$5/mo at 100k, ~$5–45/mo at 1M) live in [SCALE.md](SCALE.md). Nothing there is needed yet — the
> static model above is correct and free up to ~15–20k caps.
