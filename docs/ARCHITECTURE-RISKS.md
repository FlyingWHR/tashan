# tashan — architecture risk review (future-scale & data-intensity)

> A code-grounded audit of where the current architecture is **not designed for the stated future** —
> App-Store scale (tens of thousands → millions of capabilities) and the pivot to a **store that sells**
> capabilities behind an **unbuyable ranking**. Ranked by what bites first. Complements [SCALE.md](SCALE.md)
> (which covers only the read/delivery layer) and [MONETIZATION.md](MONETIZATION.md).

## Status — fixed in the 2026-07-25 pass (verified, tests green)

Code-level, safely-fixable items are **done**; large infra needing founder setup is **built-where-buildable + documented**.

- **§0 board rows dead → FIXED** (real `<a>` + delegated row-click; verified live: a row click opens the detail page). Guarded by `tests/test_site.py`.
- **§1 pipeline (data-intensity) → DONE:** 7 indexes on filtered/sorted columns + `signal_history` + `PRAGMA user_version`; **error-aware GitHub caching** (404 vs transient, 30-day TTL that auto-purges the 367 poisoned entries); **fixed circular enrichment ordering** (never-enriched-first, adoption proxy instead of not-yet-computed trust); **junk-ingestion guard** (`bad_pkg`, tested); **SQL-limited export** (top-N via `idx_trust`, not full-table materialize).
- **§2 runtime → DONE:** session-cached shared index loader (fetch/parse once per session, not per navigation); **board "show more" pagination** (no more 100/300 hard cap); ⌘K **debounce + precomputed lowercase**; **facet counts memoized** (was 3× O(n) per click).
- **§3 firewall → ENFORCED IN CODE:** `tests/test_firewall.py` asserts `compute_scores()` reads only a public-signal allowlist and no commerce term appears in the scorer or schema. Wired into `tests/run.sh`.
- **§1.3 grading moat → SCAFFOLDED:** `pipeline/grade_expertise.py` runs the exact rubric as an automated API job (stdlib, `--dry-run` self-check passes) — the scalable replacement for manual subagent grading.
- **Honesty:** dead `/pay/grade` link → real GitHub-issue demand signal; Pro marked *in development / waitlist* (was buy-now vaporware); `CLAUDE.md`/`PROJECT.md` drift corrected (`tashan.db` untracked + no backup; 24 graded not 299; `v=33`).

**Deferred (need founder setup or a larger migration, documented below):** incremental scoring refactor (§1.1); the SSR/D1 cutover (§2.2, SCALE.md); the store itself — write path, auth, payments, delivery, cron/CI (§3) — plus a single asset-version constant. All suites green: `bash tests/run.sh`.

## The one-sentence thesis

**Today's architecture is a read-only, periodic-batch, static *publication*. The stated future is a
write-heavy, real-time, authenticated, transactional *marketplace*.** The read side and the neutrality
economics are soundly designed and pivot-ready; almost every risk below is on the three things the docs
don't cover: the **ingest pipeline's** scaling, the **entirely-unbuilt store** (write path, auth, payments,
delivery, live data), and the fact that the two advertised differentiators — the *unbuyable-ranking
firewall* and the *LLM expertise moat* — are respectively **enforced only by the current absence of
commerce data** and **hand-graded to ~1% coverage**.

---

## 0. Live issues (not scale — broken or drifting right now)

- **[FIXED this session] Board rows were dead.** `index.js` rendered `<tr data-href=…>` but nothing read
  it and the rows had no `<a>`, so clicking a listing did nothing *and* crawlers saw zero links to the N
  detail pages (a pure SEO ceiling on the pages meant to be indexed). A regression from committed `44e147b`,
  shipped because the test suite never executed the board JS. Fixed: real `<a class="cap__link">` on the
  name + delegated whole-row click; guarded by a new check in `tests/test_site.py`.
- **Cache-bust `?v=N` has already drifted and couples trivial edits to the build wall.** The version is
  hand-maintained across 8 source locations *and baked into every prerendered page* (4×/page). `CLAUDE.md`
  still says `v=11`; actual is `v=29`. At 100k pages, a one-line CSS edit forces re-rendering + re-committing
  100k files just to bump a query string. **Fix:** one asset-version constant imported by both generators
  (or content-hashed filenames); the SSR template later removes per-file embedding entirely.
- **Docs overstate reality.** `CLAUDE.md` says `data/tashan.db` is committed — it's **untracked** (`??`),
  so the "un-backfillable retention moat" (`signal_history`) lives only on one laptop with no backup.
  `PROJECT.md` implies ~299 expertise-graded; the DB has **24**. `kind='skill'` count is **0** (skills, half
  the pitched SKU set, have never been ingested). Fix the claims or the code, but don't ship the gap.

---

## 1. The ingest pipeline has no scale plan at all (SCALE.md stops at delivery)

The read side has a migration path; the **write/ingest side does not**. These bite well before 1M — most before 100k.

| # | Risk | Evidence | Breaks at | Fix direction |
|---|---|---|---|---|
| 1 | **Every run is a full O(N) rescan + per-row UPDATE.** No watermark, no dirty-flag; `compute_scores` SELECTs the whole table with no WHERE, materializes it in RAM to normalize two maxes, then does one UPDATE/row. Registry ingest re-walks from cursor-0 every run. | `build.py:304-360`, `:99-148` | The nightly job grows linearly with the corpus even when nothing changed — painful by ~100k, wasteful long before | `inputs_hash`/`dirty` column; recompute only changed rows; persist `max_dl`/`max_reach`; stored registry cursor + `updated` watermark |
| 2 | **`gh` subprocess-per-item enrichment: throughput ceiling + cache poisoning.** 3 `gh` spawns/repo; every failure (timeout, 403 rate-limit, JSON error) collapses to `None` → cached as `{"missing":1}` **forever**, no TTL, no retry. Partial failures cache silently-wrong bus-factor/freshness. Live cache is already **36% `missing`**. | `build.py:199-251` | 5000 req/hr ÷ 3 = ~1,666 repos/hr → **1M repos ≈ 25 days/pass**; poisoning worsens the longer a run goes | Distinguish 404 (cache) from 403/timeout (retry, don't cache); TTL on `missing`; batch via GitHub **GraphQL** (3 calls→1); GitHub App token + backoff |
| 3 | **LLM expertise/category grading is manual subagent-in-session — the core moat covers ~1%.** No queue, no batch API, no re-grade-on-change. 24/2012 graded, 299 categorized. | `fetch_readmes.py:10` (`TOP_N=24`), `merge_expertise.py` | Architecturally can't reach 100k, let alone 1M; new store listings would be ~all ungraded | Move grading to a **batched Claude API job** (Message Batches API) off a `needs_grading` watermark; keep the rubric; human grading becomes spot-check |
| 4 | **The board is hard-capped at 800 in the exporter, via full-materialize-then-slice.** `SELECT … WHERE trust IS NOT NULL OR config_reach>0 ORDER BY …` (TEMP B-TREE, no index) `.fetchall()`s everything, then `[:800]`. Already at 757. | `build.py:394-418` | Permanent product ceiling **now**; RAM blowup to emit 800 from 1M | Push `ORDER BY trust DESC LIMIT ?` into SQL behind `idx_trust`; paginate, not magic-slice |
| 5 | **`signal_history` unbounded & unindexed** (no PK, no index; dedup guard full-scans on `at`). | `build.py:45-47`, `:366-376` | ~730M rows/yr at 1M caps; every chart full-scans | Index `(cap_id, metric, at)` + `(at)`; roll up beyond N days |
| 6 | **Junk ingestion:** Windows paths (`pkg:C:\Users\…\index.js`) become fake npm packages; DENY filter splits on `/` only so `\` paths bypass it. **17% of the npm-enrichment pool is this garbage**, each wasting a 404. | `build.py:401`, `scraper/scrape.py:81` | Pollution grows with the config corpus; dilutes the capped enrichment budget | One regex guard at the ingest trust boundary (reject `\`, `:`, path separators) |
| 7 | **Enrichment ordering is capped, non-rotating, and circular.** npm always re-enriches the same top-1200 by `config_reach`; github orders by `trust`, which doesn't exist until *after* github enrichment runs. | `build.py:153-154`, `:213-214` | The long tail past the cap is **never** enriched at 100k | Order by `updated_at ASC NULLS FIRST` (stalest first); break trust-circularity with a pre-scoring proxy |
| 8 | **Unqueryable JSON-blob columns + missing indexes** (`co_used` TEXT-JSON, `gh_topics` CSV; only `idx_trust` exists; `category`/`config_reach`/`npm_pkg` unindexed). | `build.py:38,57` | Every facet query is O(N) full-scan + per-row parse at 100k | Index filtered/sorted columns; normalize `co_used` to a join table or FTS5 (SCALE.md already plans this) |
| 9 | **`MIGRATE[]` ALTER-on-open only ever adds columns, and has drifted** — live DB has an orphaned `hn_count` not in `MIGRATE` and referenced nowhere. | `build.py:52-70` | Untracked schema debt accretes; no version to reason about state | `PRAGMA user_version` + numbered migrations; drop `hn_count`/`hn_cache.json` |

---

## 2. Runtime & delivery — client-side scale walls

SCALE.md prescribes the right end-state (Workers + D1 FTS5 + SSR-on-demand). These are the concrete triggers and the cheap interim fixes before that cutover.

| # | Risk | Evidence | Breaks at | Interim fix |
|---|---|---|---|---|
| 1 | **`terminal.js` fetches + `JSON.parse`s the FULL slim index on EVERY page**, `no-cache` so it revalidates each navigation — to render a 26-item ticker. Detail pages already have their data inline yet still pull this. | `terminal.js:118`, `_headers:18` | index.json **~4 MB gz at 100k**; parse blocks the main thread; SCALE.md's own trigger is ~10k | `sessionStorage` cache keyed by `generated_at`; immutable `?v=` URL (not `no-cache`); split a tiny `ticker.json` |
| 2 | **Prerender-all: one HTML file per cap, committed to git.** | `prerender.py:218` | Cloudflare **20k files (free) / 100k (paid)**; 20-min build; 100k-file git tree | SSR-on-demand in a Worker reusing `page()`; prerender only the top ~10k |
| 3 | **Board has no pagination — silently shows only 100 (or 300 filtered) rows.** The DOM cap is a good instinct with no "load more". | `index.js:197` | Any corpus > 300 — a **product** limit now, not a perf one | Keyset / "show more" now (trivial client-side); server keyset at the D1 stage |
| 4 | **⌘K palette: O(n) scan per keystroke, no debounce**, rebuilds+lowercases a string per cap per key. | `terminal.js:62,76` | Laggy ~10k, bad ~100k | Debounce ~120ms + precompute a lowercased field; D1 FTS5 structurally |
| 5 | **Every filter click recomputes 3× O(n) passes + an O(n log n) sort** over all caps. | `index.js:161,115-124,195` | Tens of ms jank/interaction at 100k | Compute facet counts once per load; memoize sorted arrays |
| 6 | **Single sitemap file** — 50k-URL / 50 MB spec ceiling. | `prerender.py:191-206` | ~50k caps | Shard into a sitemap index |
| 7 | **CSP `default-src 'self'` blocks every future external feature** (search backend, Stripe, third-party analytics) without a header edit. | `_headers:7` | On any external integration | Per-route scoped CSP; keep same-origin (Cloudflare-first) elsewhere |

---

## 3. Store-readiness — the marketplace is 0% built and the CSP forbids the payment step

The only server code in the repo is the analytics beacon (`functions/api/e.js`). No D1/R2/KV/DO, no `wrangler.toml`, no auth, no writes.

- **The entire write path is absent** — listings, accounts, sales, payments, reviews, artifact delivery. The literal "Get Pro" mechanism today is a **`mailto:`** (`pricing.html:64`); the grade-bounty "Back +$0.20" links to a `/pay/grade` route that **doesn't exist** (`requests.js:19`). → Pages Functions + **D1** write tables (already named in `SCALE.md:129`), **Stripe Connect** (creator = seller-of-record), webhook → Worker → D1.
- **The CSP categorically forbids client-side payments.** `_headers:7` — `script-src 'self'` blocks `js.stripe.com`, `connect-src 'self'` blocks `api.stripe.com`/x402, no `frame-src` blocks Checkout iframes, `form-action 'none'` blocks *any* form POST. All three advertised rails (card + USDC) are CSP-impossible as configured. → **Scoped** `/checkout/*` CSP; prefer a server-side Stripe redirect. Don't relax globally (the strict CSP is a real feature).
- **No auth/identity of any kind** — no accounts/sessions table, no login anywhere. A marketplace can't attribute a listing, gate a purchase, deliver a paid artifact, or pay a creator without it. → D1 `accounts`/`sessions` + KV for hot session lookup; Stripe Connect covers *seller* KYC only, not buyer entitlement.
- **The recommended monetization core — the "rendering"/delivery service — has zero infrastructure.** No Worker-as-MCP-server, no R2 for bundles, no metering table. The CLI only reads static data. → Worker (Static Assets) as MCP proxy + **R2** (free egress) + D1 metering + KV curation. Proxy+pin upstreams, don't rehost (liability).
- **The "unbuyable ranking" firewall is enforced only by the *absence* of commerce data — no guard, no test.** It holds today because the schema has no price/GMV columns and `compute_scores` reads only public signal (`build.py:304-307`) — but that's coincidence, not enforcement; once `listings`/`sales` land, one JOIN erodes it. → Keep commerce in physically separate D1 tables the scorer never binds; **add a test asserting the scorer's SELECT column-set ⊆ a public-signal allowlist** (cheap, fits `tests/`). This is the whole differentiator — make it code.
- **Data freshness is a manual rebuild** — no cron, no CI; deploy is a manual `wrangler` command **blocked on re-auth**; `signal_history` has only 2 dates. A store needs live price/inventory/availability the static export can't provide. → **Cloudflare Cron Triggers** for daily enrichment+deploy; serve mutable commerce fields from D1 at request time with purge-on-write.
- **`signal_history` is collected but never exported or served**, yet `pricing.html:60` sells "full history." Data with no delivery path. → A D1-backed history endpoint (the sparkline seed named in `ARCHITECTURE.md:70`).
- **Pricing/Requests sell unbuilt features** — watch/alerts, compare, API (with an *unenforceable* "60/day" cap on a static CDN file), export, on-demand grading. For a product whose value prop is honesty, this is a credibility risk. → Gate behind the D1+Functions build or remove until real.
- **Operational maturity:** no CI (the good `tests/run.sh` runs by hand), no monitoring/alerting on the one Function, single-owner/single-region source of truth committed to git as the only backup, `gh` enrichment with no unattended token/rate-limit strategy. → GitHub Actions + Cloudflare Logpush/alerts; D1 Time-Travel/replication when commerce (money records) lands; GitHub App token.

---

## What is soundly designed — do NOT rebuild these

- **The inline-data island** (`prerender.py:186` → `capability.js` `boot()` fast-path): a cap's full data ships in its own HTML as a non-executable JSON island, rendered with **0 bytes fetched**. Scales to any N — the one piece to keep.
- **Legacy `?id=` redirects instead of fetching the 1.2 MB export**; co-use links pruned to prerendered slugs so they never 404. The bulk export is genuinely bulk-only at runtime.
- **Read/write table separation** (`SCALE.md:129`): the pipeline keeps owning `capabilities`; commerce is *new* tables. The pivot does **not** require rewriting reads — the single best structural decision for it.
- **The neutrality economics** — a thin, **flat**, outcome-independent cut (honesty is affordable) — is internally coherent; flat-not-% is the right load-bearing invariant.
- **Scores compute from public signal, `None` never faked to 0** (`build.py:316,350`); env-cap knobs (`REG_CAP`/`NPM_CAP`/`GH_CAP`/`TOP_N`) throttle stages without code edits; the export/board/prerender alignment (one trust-ranked set feeds all three).
- **The JSON sidecar caches** make re-runs cheap (the only flaw is error-unaware caching, §1.2 — the caching idea is right).
- **The analytics collector** (`functions/api/e.js`) is a correct model for the write path: CSP-clean same-origin, input clamped against hostile payloads, silent-fail. `/api/checkout` etc. can follow its exact shape.
- **SCALE.md itself** is a strong, honest plan for the read side.

---

## What to do, in order

1. **Now (done/cheap):** board-nav fix (done); fix the doc/reality drifts; add the firewall column-allowlist test; single asset-version constant.
2. **Before any scale work (data-intensity, bites < 100k):** pipeline incrementalism (§1.1), GitHub GraphQL + error-aware caching (§1.2), batched-API grading (§1.3), ingest junk guard (§1.6), `sessionStorage`+immutable index / tiny `ticker.json` (§2.1), board pagination (§2.3).
3. **The store (from-scratch):** D1 write tables + auth (accounts/sessions) + Stripe Connect behind a scoped `/checkout` CSP + R2 delivery; Cron Triggers for freshness; keep commerce tables un-joinable to the scorer.
4. **Then the SCALE.md cutover** (Workers Static Assets + SSR-on-demand + D1 FTS5) when file count > ~15–20k or writes ship.
