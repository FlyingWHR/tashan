# tashan

**The intelligence layer for AI capabilities.** *Measure what actually works.*

Not another directory — an instrument that scores capabilities on **public evidence**
(not stars, not listings, not opinions). V2 tracks the **whole MCP field** (official registry)
and ranks it by a transparent **Trust** score — maintenance + freshness, gated by real
adoption. Roadmap: retention/churn, expertise eval, security, controlled evals, cost.

## ETHOnline 2026 — what is pre-existing and what was built in the window

Entered on the **Continuity** track, which is the one that admits a project that already existed.
This split is stated up front so nothing here has to be taken on trust: every claim below is
checkable with `git log` or `npm view`.

**Pre-existing (23 July – 11 September 2026, 386 commits).** The instrument itself: the SQLite
pipeline, the scorer (`s5`, frozen and published through 2026-11-01), the four-layer security audit,
the static site and its generated SEO/GEO tier, the CLI and MCP server (`tashan-cli` on npm, first
published 2026-07-31, registry entry `sh.tashan/tashan`), and 34 test files. None of it counts as
hackathon work and none of it is presented as such.

**Built in the window (12–13 September 2026).** Eight commits, listed with what each one actually
did — and one of them is a bug fix that had cost the project eighteen days of publishing:

| commit | what landed |
|---|---|
| `12723dfb` | The daily pipeline had been dead for twelve days on an event tuple with four fields unpacked into five. Fixed; the module's self-check now reads its own source. |
| `dad625d1` | **The subgraph.** USDC transfers on Base filtered to 1,079 x402 receivers harvested from the Bazaar — indexing the receipts, not the listings. |
| `76266dc4` | `tashan doctor` gained an inventory: every project's servers, plugins with install dates, skills told apart by owner, and a local first-seen ledger. |
| `1a23cf1d` | `pipeline/paid_demand.py` — the subgraph joined to the capability catalog by exact host. The only signal in this product that is money. |
| `4ec7adf0` | Two audits applied: the paywall contradiction, four disagreeing ecosystem counts, twelve CLI verbs reduced to five. |
| `47abe203` | Directory data quality: 2,030 identities exist as more than one kind and 460 carry disagreeing scores. Measured and baselined so it cannot grow. |
| `c565d8e9` | Co-use links filtered by id rather than by derived slug. |
| *(13 Sep)* | That filter **was** the cross-surface consistency failure — proven, not guessed (see below), plus a freshness claim that was reading the render clock instead of the data. |

**The eighteen-day bug, since it is the most useful thing in this list.** `tests/test_consistency.py`
had been failing every night since 27 August, which by design withholds the whole site — so tashan.sh
served 25 August data for two and a half weeks. The cause: co-use links were filtered by *slug*
against a set of slugs. A slug is a label derived from an id, and `pkg:stripe-mcp` and
`pkg:@stripe/mcp` both derive `pkg-stripe-mcp` — so a link to the id the export had dropped matched
the surviving row's label, survived the filter, and was baked into eight pages. It took three
coincidences at once to show, which is why it never reproduced by hand; the case is now synthesised
in `pipeline/prerender.py --selftest`, asserted in both directions.

See `docs/HACKATHON.md` for the entry's state and `docs/AI-USAGE.md` for how AI was used.

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
python3 pipeline/run.py       # the whole pipeline, correct order, every stage idempotent
python3 pipeline/run.py --site   # regenerate the site only, no network
python3 pipeline/run.py --list   # show the stages
```
`run.py` schedules the stages below; `scraper/scrape.py` and `pipeline/build.py` are still
independently runnable.
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
compounded per capability — become an evidence base no listing can copy. See `PROJECT.md` for the thesis and `brand/BRAND.md` for the design system.
