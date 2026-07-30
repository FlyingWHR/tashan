# Overnight run — 2026-07-25 (morning report)

You asked for a snappy experience, tech-architecture research for App-Store scale, a comprehensive test
structure, a terminal experience, and analytics wired up for PLG — an overnight optimization round. Here
is what shipped, verified, with the **one bug that was blocking you** fixed first.

## ✅ Fixed: the listing page you couldn't see ("loading so slow or have bugs")

**Root cause (three compounding bugs, now all fixed):**
1. **Co-use links pulled the 1.2 MB export.** Every "Configured alongside" link on a capability page
   pointed at the legacy `/capability.html?id=…` route, which downloads the entire 1.2 MB
   `capabilities.json` to find one row. Clicking between listings = a 1.2 MB fetch each time (uncompressed
   on the local server). → Now they point at the prerendered `/capability/<slug>.html` page (inline data,
   **0-byte** fetch). `web/js/capability.js`.
2. **The legacy `?id=` route itself fetched 1.2 MB.** → Now it redirects to the fast prerendered page.
   **Nothing fetches the 1.2 MB export at runtime anymore** (it's a bulk export only).
3. **The board shipped 139 broken rows.** `index.json` had 939 rows but only 800 pages existed, and 43 of
   those 800 were junk (someone's local `C:\Users\david\OneDrive\…` paths ingested as fake npm packages,
   `trust: null`). Clicking them 404'd. → The board, the export, and the prerendered pages are now the
   **same trust-ranked 757-capability set** — every row has a real page, no junk, no 404. `pipeline/build.py`,
   `pipeline/prerender.py`.

**Result:** detail pages render instantly from inline data; the slim board index dropped **426 KB → 324 KB**
(29 KB gzipped); zero broken links across 205 co-use links and 757 board rows. Verified green by the new
test suite below.

### The deeper bug behind "richness didn't improve" + the reload loop (found on review)

`capability.js` calls `render()` from a fast-path at the top of the file, but the category-label map
`var CAT = {…}` is declared lower down — and `var` hoists only the name (as `undefined`), not the value. So
`render()` read `CAT[c.category]` → **TypeError on every categorized capability**, threw, and users saw only
the thin server summary — none of the install tabs, repo-health, registry cross-links, or community that the
prior session built. (My legacy-`?id=` redirect then turned that silent throw into an infinite reload loop.)
**Fix:** the entry logic is wrapped in `boot()` and called at the *end* of the IIFE (everything initialized
first); island pages never redirect; the legacy redirect guards against pointing at itself. Now the full
dossier renders. Guarded by a new headless render test that runs `capability.js` against real data across 64
pages. Also calmed the hero ridge art (it was rendering as dense scratchy hatching → a clean subtle ridgeline)
and versioned all JS/CSS to `?v=28` so the fixes actually reach cached browsers.

## ✅ Comprehensive test structure (one command)

`bash tests/run.sh` → **40 checks, all green.** Three suites:
- **`tests/test_site.py`** (36 checks): every board row has a page (no 404s), no orphan pages, no runtime
  fetch of the 1.2 MB export, load budgets (detail HTML ≤ 20 KB, index ≤ 45 KB gz), SEO/AEO (title, meta,
  canonical, OG, JSON-LD `SoftwareApplication`, inline island — all parse), sitemap == pages, strict CSP,
  analytics wiring + privacy. Also live-HTTP: sampled pages all 200, fast, within budget.
- **`functions/api/e.test.mjs`**: analytics field-shaping + clamping.
- **`cli/tashan.test.mjs`**: CLI search/rank/find/install logic.

This locks in the fix above — the 404/slow-path regressions can't come back silently.

## ✅ Analytics wired up (first-party, privacy-first, PLG-ready) — needs a 2-min activation

A cookieless, **CSP-clean** event pipeline that ships with the site — no third-party script, no consent
banner, **$0** on Cloudflare's free Analytics Engine, and **SQL-queryable** for growth funnels.
- **Client** (`web/js/site.js`, every page): `pageview` + delegated capture of the PLG events — **copy**
  (install snippet / badge), **outbound** (registry/repo/community, keyed by host), **conav** (graph
  traversal). `window.t.track()` for custom events. Honors Do-Not-Track / GPC; no cookies, no fingerprint.
- **Collector** (`functions/api/e.js`): same-origin `/api/e` → Analytics Engine. Silent-fails if unbound.
- **Activate:** bind an Analytics Engine dataset as `TASHAN_AE` in the Cloudflare dashboard and redeploy.
  Full steps + funnel queries (view→install conversion, outbound flow, acquisition) in **`docs/ANALYTICS.md`**.
- Deliberately **not** Cloudflare Web Analytics — its script is a third-party origin that breaks our strict
  CSP and only counts page views. First-party is CSP-clean, event-capable, equally free.

## ✅ Terminal experience — `npx tashan-cli` (context7-grade, zero backend)

A single-file, dependency-free CLI that reads the **live static `index.json`** — no backend needed.
```
npx tashan-cli search database     npx tashan-cli top browser
npx tashan-cli info context7       npx tashan-cli add context7      ← the money shot
```
`add` prints the exact install command (`--client claude|cursor|desktop|codex|npx`), generated by the
**same logic as the website** so they never disagree. `--json` for scripting. Tested. `cli/` +
`cli/README.md`. **Not published to npm** — that's your call (name check + publish).

## ✅ Architecture at App-Store scale (perf + price) — `docs/SCALE.md`

The answer to "tens of thousands → millions, weighing performance and price": adopt the proper Cloudflare
architecture (Workers + D1 + FTS5 + on-demand SSR). It costs **~$5/mo at 100k capabilities, ~$5–45/mo at
1M** — cheaper in absolute terms than Vercel (~$100–120) or Algolia (~$2,850 at 1M), so per your own rule
there's no interim cheap step worth building. The current static model is correct and free to ~15–20k caps;
the doc has the staged path, the exact triggers to migrate, and the per-tier cost math. Keep the inline-data
technique (it scales to any count) — only the ship-all-rows board and one-file-per-cap move to the edge.

## Also
- **Tabular figures** on the detail-page stat grid (matches the board's already-tabular columns).

## ⏳ Still needs you (unchanged from the last round)
- **The monetization decision** — `docs/MONETIZATION.md`. Store confirmed as the direction ("it has to be a
  store; the thesis needs reframing"), and the reframe is written (a thin, flat, outcome-independent cut is
  what *lets* the ranking stay honest). What's yours to set: flat-fee vs %, referral-first vs hosted store,
  the creator-share number to advertise. The store checkout (Stripe) needs your account setup — I did not
  build payments unattended.
- **Third-party styling (#25)** — "respect the source platform's styling while adapting to ours" for the
  registry/repo cross-links. I did **not** ship this: it's a visual change and the browser extension
  disconnected overnight, so I couldn't verify it pixel-for-pixel. Proposal: a subtle per-source monochrome
  glyph + brand-tinted hairline on each cross-link, ordered by directness. Ready to implement the moment we
  can eyeball it together.

## Verification & constraints
- `bash tests/run.sh` → 40/40 green. CLI + collector unit tests green. Pipeline re-exported (757 caps) and
  re-prerendered; sitemap current; 43 junk pages removed from disk.
- **Nothing deployed or committed.** All changes local and reviewable on the dev server (:4173).
