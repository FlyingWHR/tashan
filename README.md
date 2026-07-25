# tashan

**The intelligence layer for AI capabilities.** *Measure what actually works.*

Not another directory — an instrument that scores capabilities on **public evidence**
(not stars, not listings, not opinions). V2 tracks the **whole MCP field** (official registry)
and ranks it by a transparent **Trust** score — maintenance + freshness, gated by real
adoption. Roadmap: retention/churn, expertise eval, security, controlled evals, cost.

## Structure
```
pipeline/build.py   v2 data pipeline: registry + configs + npm → SQLite → scores → site JSON
scraper/scrape.py   config-adoption scraper (GitHub configs → data/capabilities.json)
data/               tashan.db (SQLite, source of truth) · capabilities.json (config-adoption)
                    npm_cache.json · repo_meta.json · raw/ file cache
web/                the site (static, deployable) — reads /data/capabilities.json (an export)
  css/ js/ assets/  design system (Geist + Geist Mono self-hosted), leaderboard + detail
  index / methodology / about / capability
brand/BRAND.md      identity + design system (near-black + amber "terminal")
```

## Run the pipeline (v2)
```sh
python3 scraper/scrape.py     # 1. config-adoption → data/capabilities.json (gh CLI auth)
python3 pipeline/build.py     # 2. registry coverage + npm quality → SQLite + web/data JSON
```
`build.py` phases: **A** load config-adoption · **B** ingest the official MCP registry for
coverage (thousands of capabilities: name/desc/status/repo/package) · **C** enrich npm-linked
capabilities (weekly downloads, last-publish, maintainers, versions, deprecated) · **D** compute
transparent scores (Adoption, Maintenance, Freshness, Trust) · **E** export `web/data/capabilities.json`.
- Tunable: `REG_CAP` (registry servers to ingest), `NPM_CAP` (npm packages to enrich per run).
- Resumable: registry is idempotent (upsert); npm results cache in `data/npm_cache.json`.
- Honest: adoption/maintenance ≠ outcome quality (see `web/methodology.html`).

## Database
SQLite at `data/tashan.db` is the source of truth — one `capabilities` table (identity +
enrichment + scores) plus a `signal_history` stub for longitudinal (retention/trend) data.
The site JSON is an **export**, not the store. Prod path: SQLite → Cloudflare D1 / Postgres.

## Build / deploy
`build.py` already writes `web/data/capabilities.json`. Deploy `web/` as a static site
(Cloudflare Pages — same setup as stilltime.io):
```sh
npx wrangler@3 pages deploy web --project-name tashan
```
`_headers` ships a strict CSP + revalidating CSS/JS/data + hard-cached fonts. No build step,
no framework, no external requests.

## The moat (why this isn't scrapeable)
Directories list supply; **tashan measures demand.** Owner-reach, retention, evals, and cost —
compounded per capability — become an evidence base no listing can copy. See `brand/BRAND.md`
and `../skills-marketplace-research/REPORT.md` for the thesis.
