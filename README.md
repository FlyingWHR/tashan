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

**Built in the window (12–13 September 2026).** Every commit in the window is listed by
`git log --since='2026-09-12T12:00:00+00:00' --oneline` — a count typed here would go stale by the
next commit, which is the defect this project exists to point at. The substantive ones:

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
| *(13 Sep)* | **`/paid.html` — the money signal, on the site.** Settled x402 payments on Base, read through The Graph's own Subgraph MCP server, joined to the catalog. A page, a row on every dossier, a `paid_demand` tool on our MCP server. |
| *(13 Sep)* | A ratchet that punished measuring more: the identity gate compared an absolute count, tripled overnight when 18 days of enrichment backlog cleared, and withheld the site. It ratchets the rate now. |
| *(13 Sep)* | UX: the stat grid had **no CSS at all** (so `/stats.html` shipped its headline numbers as a default `<dl>`), and the nav wrapped and collided with the wordmark on every phone. |
| *(13 Sep)* | The money signal added to the cross-surface consistency suite — ten assertions across the export, the dossier, the page and the agent JSON, because it had already drifted twice in one night. |
| *(13 Sep)* | `/v0.1/servers` carries settled receipts, so the agent-readable registry publishes the newest measurement too. |
| *(13 Sep)* | We are in our own paid table — last, $0.00, never paid. The page says so, rendered from that row. |

**The headline feature: which AI services actually get paid.** Every other number here is a proxy
for demand measured from outside — downloads, publish cadence, stars, appearances in public configs
— and all of them can exist without anyone finding the thing useful. A settled USDC payment cannot.
`/paid.html` asks the chain about all 1,079 x402 payment addresses harvested from the Bazaar's
listings: **997 have been paid at least once, 82 never have**, they have settled **$247,247 across
10.4 million payments**, and the **median service has earned $0.51 in its entire life**. Two thirds
of all volume is one receiver. The page publishes that distribution rather than the total, because a
sum is the one statistic a concentrated economy always passes.

It is read through The Graph's own Subgraph MCP server (`pipeline/subgraph_mcp.py` — an MCP client
over HTTP+SSE, stdlib only, no SDK and no `npx mcp-remote`), so the page can print the endpoint, the
tool and the query and invite you to re-run it. Payment is deliberately **not** an input to the
score, for the same reason the security columns are not.

**The eighteen-day bug, since it is the second most useful thing in this list.** `tests/test_consistency.py`
had been failing every night since 27 August, which by design withholds the whole site — so tashan.sh
served 25 August data for two and a half weeks. The cause: co-use links were filtered by *slug*
against a set of slugs. A slug is a label derived from an id, and `pkg:stripe-mcp` and
`pkg:@stripe/mcp` both derive `pkg-stripe-mcp` — so a link to the id the export had dropped matched
the surviving row's label, survived the filter, and was baked into eight pages. It took three
coincidences at once to show, which is why it never reproduced by hand; the case is now synthesised
in `pipeline/prerender.py --selftest`, asserted in both directions.

See `docs/STORY.md` for how to talk about this to a builder — the argument in the order it convinces, every number checkable on the site. `docs/HACKATHON.md` for the entry's state, `docs/AI-USAGE.md` for how AI was used.

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
