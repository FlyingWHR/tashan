# tashan — project reference

> **tashan** · *the intelligence layer for AI capabilities* · **measure what actually works.**
> Domain: **tashan.sh** · Repo: `~/ProjectW/tashan` · Company: SeroLabs, Inc.

This is the master doc. Deep-dives live in `docs/COMPETITIVE.md`, `docs/GROWTH.md`, `brand/BRAND.md`,
and `README.md` (how to run). Everything below is current as of 2026-07-24.

---

## 1. What it is, in one breath

There are ~61,000–81,000 MCP servers and ~333,000 skills in the wild, and almost no honest signal about
which ones actually work. **tashan is a measurement layer: it measures what people actually keep, and
publishes the arithmetic.** Real adoption from public configs, how actively a thing is maintained, how
fresh it is, and an LLM read of how good the actual *expertise* is.

It is a **thin layer, not a destination** — not a store, not a runtime, not another directory. Closer to
Consumer Reports than to npm or the GPT Store: trusted because it **measures**, independently, and
**sells, hosts and runs none of what it scores.**

**Say the denominator.** We hold ~1,240 capabilities against a field of tens of thousands. "Whole-field
coverage" is an aspiration, not a fact, and claiming it is the same sin as any other unmeasured claim —
publish `N of ~M known, from these sources, synced T` (see `docs/SOURCING.md` §0).

### The name (the whole thesis in three characters)
**他山** (*tashan*), from **他山之石，可以攻玉** — *a stone from another mountain can polish your jade.*
We bring no stone of our own to sell; we judge the field with the field's **own public evidence** (its
stones — the registry, npm, git history, the READMEs people wrote) and let the jade show itself. Always
**lowercase** — it's a command you run (`tashan`, `tashan.sh`, `npx tashan`), not a brand you shout.

---

## 2. Positioning & the moat

**The one defensible advantage is structural, not a feature: tashan doesn't sell the inventory it
scores, so it can be a neutral rating authority.** A store (Agensi) earns a cut of the listings it would
grade — it structurally cannot publish honest evidence-based scores without cannibalizing itself. "A
competitor can add a downloads column in a weekend; it can't buy disinterest."

Reinforced by two things a store can't copy:
1. **Coverage beyond opted-in supply** — we can rank what nobody submitted and nobody sells.
2. **Compounding, un-backfillable data** — retention/churn history from git needs *time* to accrue.

### The strategy in one line: a thin layer, one niche dataset, maximum cast range

The 2026-07-26 landscape sweep (`docs/MARKET.md`) killed the idea that scoring is itself the edge —
**Smithery, Glama and LobeHub all ship a score.** What none of them has:

- **The niche dataset.** What developers actually *keep in real public configs, over time.* Smithery has
  runtime telemetry but only for servers it hosts; LobeHub has installs only inside its own app; Glama
  and PulseMCP have crawl metadata. Nobody has the config corpus, and nobody can backfill it. It is also
  **cheap to collect** — a code search and a git-history walk. No runtime, no proxy, no hosting.
- **Disinterest.** Every one of them earns from the shelf: LobeHub and Smithery from consumption, Agensi
  from a 30% cut. LobeHub's public rubric even docks a server for not claiming its listing. We earn from
  none of it.
- **A measurement of skills.** ~333,000 exist; not one carries a published quality grade anywhere.

**Cast range is the distribution strategy.** A rating nobody sees at install time changes nothing, so the
measurement must travel *off* the site: embeddable badges (in the maintainer's own README), `llms.txt`,
the machine-readable export, the CLI, and eventually a subregistry endpoint serving scores under `_meta`
so MCP hosts consume them natively (`docs/SOURCING.md` §6). We do not need traffic; we need the number
to be present where the decision is made.

**Stay thin.** The temptation is to answer LobeHub with more surface — a runtime, a marketplace, 650k
listings. That trade loses: it costs the neutrality, which is the only asset a funded competitor cannot
buy. One command runs the whole pipeline (`pipeline/run.py`); if a stage isn't feeding the dataset or
its cast range, it shouldn't exist.

**The firewall (absolute rule):** *You never pay to change a score, a rank, or a listing. You pay for
depth, access, and tooling.* If a maintainer could pay to look better, the instrument is worthless.

**Honest risks:** (1) **platform risk** — Anthropic already ships a security-scanned "Verified"
directory and owns the standard/client/telemetry; (2) revenue tension — neutrality forecloses the
obvious monetization (can't take a transaction cut), addressed via subscription + a future data/API tier.

---

## 3. Competitive landscape  → `docs/COMPETITIVE.md`

- **Agensi** (agensi.io) — a curated **store that sells** agent-skills (30% take, security-scan + human
  review, ~2,200 listings, Antler-backed, launched ~Apr 2026). Listings show **name/price/description
  only — no downloads, ratings, or scores. It curates and sells; it does not measure.** Its category
  taxonomy is **8 flat functional buckets** (Frontend & Design, Testing & QA, DevOps, Code Review, Docs,
  Productivity, Data Engineering, API Development), a vertical list, no filters/sorting. Thin — the gap
  we beat on depth.
- Adjacent: mcp.so, Smithery, Glama, PulseMCP, the official MCP registry, awesome-mcp-servers. All
  **directories** (list supply); none measure demand + quality the way tashan does.

---

## 4. Architecture & data engine

Public signal → **SQLite** (`data/tashan.db`, source of truth) → scores → **static JSON export**
(`web/data/capabilities.json`) → **zero-dependency static site**. No backend yet (deliberate — see §9).

```
scraper/scrape.py         config-adoption miner (public GitHub mcp.json / claude_desktop_config / .cursor)
                          → data/capabilities.json  (reach, repos, stars, freshness, co-use)
pipeline/build.py         THE pipeline. A) load config-adoption  B) ingest official MCP registry
                          (registry.modelcontextprotocol.io/v0/servers, cursor-paginated) for coverage
                          C) enrich npm-linked caps (downloads, last-publish, maintainers, versions,
                          deprecated)  D) compute transparent scores  E) export web JSON.
                          SQLite schema self-migrates new columns via MIGRATE[] + ALTER on open.
pipeline/fetch_readmes.py pull top caps' READMEs for expertise-eval (TOP_N env to scale)
pipeline/merge_expertise.py   merge LLM expertise grades → DB → re-export
pipeline/classify_prep.py     dump ranked caps for category classification
pipeline/merge_categories.py  merge LLM category assignments → DB → re-export
pipeline/gen_badges.py    generate embeddable per-cap SVG badges → web/badge/<slug>.svg
```

**Coverage today:** 2,012 capabilities tracked · 294 npm-enriched · 757 ranked (trust-scored) · **24
expertise-graded** · 299 categorized. Tunable via `REG_CAP` / `NPM_CAP` / `TOP_N`. Note the expertise
moat is only ~1% covered because grading is still manual subagent-in-session — the batched-API grading
job (see `docs/ARCHITECTURE-RISKS.md` §1.3) is what makes it a moat at scale.

---

## 5. Signals & scoring (all transparent, shown per-capability, never a black box)

| Signal | Source | Meaning |
|---|---|---|
| **Adoption** | npm weekly downloads (log) + config reach | real usage; downloads alone never rank — they only *gate* |
| **Maintenance** | npm cadence, maintainer count, deprecated flag, registry status | is it kept alive? |
| **Freshness** | latest release / host-repo push | living vs. abandoned |
| **Trust** | `mean(Maintenance, Freshness) × gate(Adoption)` | the single Index rank |
| **Expertise** ⭐ | **LLM reads the README** vs a fixed rubric | `deep / solid / thin / wrapper / slop` + a written verdict — the signal no directory has |
| **Category** | **LLM classification** into a 15-cat taxonomy | browse-by-domain, ranked within category |
| Co-use | configs | what real stacks pair it with |
| *(roadmap)* Retention | git history "added-then-removed" | the most honest review |

**Expertise proves the thesis on real data:** chrome-devtools & kubernetes = *deep* (87) while
server-memory & filesystem = *thin* (55/62) **despite** far higher adoption. Quality ≠ popularity.

### The 15-category taxonomy (`web/data/categories.json`)
browser · search · database · devtools · cloud · files · data · docs · comms · design · ai · finance ·
productivity · security · other. Grounded in the community-standard awesome-mcp-servers, **LLM-classified**
(not keyword-hacked) — better-curated than Agensi's 8 flat buckets, and every item still carries scores,
install path, and official tags Agensi lacks.

---

## 6. Design system  → `brand/BRAND.md`

**Cool developer instrument, not an exchange.** (Pivoted off the original amber-on-black, which read
"Binance.")

- **Palette:** warm **stone-black greyscale** (`--bg #0b0b0a`, neutral greys with a slight warm/stone
  tint) + one **luminous jade-green accent `#34e0a0`** (brightened per a Robinhood/Hyperliquid/Higgsfield
  study — all luminous-green-on-black). Accent is **reserved for measured data only** (the Polar lesson:
  restraint, not just hue). `--jade-bright #5cf0c0`.
- **Type:** Geist (sans, UI) + GeistMono (all data/numbers/labels — the instrument readout), self-hosted
  woff2, no external requests. Serif reserved for the occasional editorial pull-quote.
- **Logo/mark:** a **jade stone** (他山之石) — organic pebble with a polished facet. `favicon.svg` +
  `.brand__mark` (CSS mask so the `--jade` token drives color; shape-following drop-shadow glow).
- **Signature motifs:** ASCII mountain ridge in the hero (他山); the 他山之石 name-story line; a cool
  jade-teal canvas smoke (`js/smoke.js`, CSP-safe, reduced-motion aware); staggered headline + "works"
  underline draw + rotating dimension line + blinking caret (`js/hero.js`).
- **Terminal frame** (`js/terminal.js`, every page): a scrolling **ticker** (live cap readouts +
  verdicts), a tmux-style **status line** (`◆ tashan.sh · counts · ⌘K`), and a **⌘K / `/` command
  palette** (fuzzy search, filter by verdict e.g. `deep`, `tashan ❯` prompt).
- **Architecture:** strict-CSP, **zero-dependency, vanilla JS, no build step** — a deliberate feature
  (fast, private, self-contained). No framework was added for the catalog; the "high-quality library" is
  the community taxonomy + our LLM classifier, not JS deps. CSS versioned via `?v=N` (currently `v8`).

---

## 7. Product surface (what's live on the site)

- **The Index** — a **category catalog**, not a list: a browse-by-category grid (counts, click-to-filter,
  `?cat=` deep links) over a trust-ranked leaderboard; rows carry expertise verdicts, `✓ official`
  model-company tags, category tags.
- **Capability detail** — stat grid (Trust, Expertise, Adoption, Maintenance, Freshness, Maintainers), the
  **"expert read"** (LLM's written verdict), a **working install path** (`npx` + `mcp.json` snippet, copy
  buttons) + links to the original (npm / source / registry), co-use, and the **"Show your score"** badge
  embed.
- **Official tagging** — Anthropic / OpenAI / Google / Microsoft auto-detected from npm scope / repo owner,
  jade `✓ official` tag on board + detail. (All official model-company capabilities surfaced + tagged.)
- **Pricing** — free Index forever; **tashan Pro $6/mo ($60/yr)**; pay by **card or USDC (Coinbase x402)**;
  plus **$0.20 USDC pay-per-use** deep-grade with no account. Neutrality guarantee stated plainly.
- **Methodology / About** — the trust core: exactly what's measured, the Trust formula, what we *don't*
  do, and the 他山之石 story.
- **Badges** — 299 embeddable jade SVGs at `/badge/<slug>.svg` (the flagship growth loop).

---

## 8. Revenue & PLG  → `docs/GROWTH.md`

- **Subscription:** Index free forever (the free tier *is* the growth engine); **Pro $6/mo** unlocks depth
  (unlimited watches/alerts, compare, full API/CLI, history/trends, on-demand deep expertise, export). Real
  money is later: **Team** (org audits) + **Data/API** tiers.
- **Payments day 1:** card or USDC (x402); pay-per-use micropayment. Crypto = launch *convenience*
  (instant, global, machine-native), not a rail we operate.
- **Four compounding PLG loops:** (1) **badges** [built] — maintainers embed → backlinks + brand on their
  repos; a store can't run this loop. (2) SEO from capability + compare pages. (3) `npx tashan` CLI —
  distribution inside the terminal. (4) watch/alerts — retention + the Pro wedge.
- **Flywheel:** coverage → badges → backlinks → traffic → more data → better scores → more coverage.
  Retention data can't be backfilled — the moat is the integral of the loops over time.

---

## 9. Roadmap (staged — honest about what's not built)

1. **Backend** (the next unlock) — a small **Cloudflare D1/Postgres + Functions** layer. Needed by
   watch/alerts, the API, Pro billing, and catalog persistence. One investment, multiple features.
2. **Retention/churn** from git history — the 2nd unique moat signal ("added-then-removed").
3. **Skills, not just MCP** — ingest agent-skills incl. **official model-company skills** and best
   community ones (e.g. **impeccable** for design), unified capability model.
4. **Full coverage parity+** vs Agensi/mcp.so/Smithery; classify the ~182 tail caps beyond the ranked set.
5. **Security eval** — CVEs, single-maintainer risk, typosquats, tool-description prompt-injection.
6. **`npx tashan` CLI** + per-capability OG images + capability-page prerender (for SEO loop 2).
7. **On-chain (later):** be the **ERC-8004 reputation oracle** payment/escrow rails *read* — NOT a payment
   rail (that would sell what we score). tashan occupies agent trust-stack layers 1 (Discovery), 6
   (Verification), 7 (Reputation); monetize via protocol/enterprise API, never a transaction cut.

---

## 10. Repo map

```
tashan/
├── PROJECT.md              ← this file (master reference)
├── README.md               how to run the pipeline + deploy
├── brand/BRAND.md          identity & design system
├── docs/
│   ├── COMPETITIVE.md      Agensi + field analysis, the moat
│   └── GROWTH.md           revenue, pricing, the 4 PLG loops, on-chain
├── scraper/scrape.py       config-adoption miner
├── pipeline/               build.py + fetch_readmes / merge_expertise / classify_prep /
│                           merge_categories / gen_badges
├── data/                   tashan.db (source of truth) · capabilities.json · npm_cache.json ·
│                           readmes/ · classify/ · raw/
└── web/                    the static site (deploy this)
    ├── index · capability · methodology · about · pricing (.html)
    ├── css/site.css        the whole design system (jade/stone, terminal, catalog)
    ├── js/                 index · capability · terminal · smoke · hero · site · methodology
    ├── data/               capabilities.json (export) · categories.json
    ├── badge/              299 embeddable SVG badges
    ├── assets/             fonts (Geist/GeistMono woff2) · favicon.svg (jade stone)
    └── _headers _redirects robots.txt sitemap.xml
```

---

## 11. Build / run / deploy

```sh
# regenerate data
python3 scraper/scrape.py            # 1. config-adoption  (uses gh CLI token)
python3 pipeline/build.py            # 2. registry + npm → SQLite → web JSON
# expertise (parallelized via subagents in-session): fetch_readmes → grade → merge_expertise
# categories (parallelized via subagents in-session): classify_prep → classify → merge_categories
python3 pipeline/gen_badges.py       # embeddable badges

# preview locally
cd web && python3 -m http.server 4173 --bind 127.0.0.1   # → http://localhost:4173

# deploy (static)  — Cloudflare Pages, project "tashan", domain tashan.sh
npx wrangler@3 pages deploy web --project-name tashan
```

**Deploy status: BLOCKED on Cloudflare re-auth.** Run `npx wrangler@3 login`, then the deploy command
above. Same CF account as stilltime.io. The earlier OAuth token expired.

---

## 12. Taste & working principles (for whoever builds next)

- **Plain, grounded copy.** No precious/poetic marketing ("装逼"). Under-write. The one endorsed flourish
  is the 他山之石 story — kept to a single sentence.
- **Convenience is felt, not sold.** Payment ease shows up at checkout, never as a feature bullet.
- **Premium = restraint + one clean number**, not price or saturation. (Pro is round $6, not $5.99;
  accent on data only.)
- **Measured, not claimed.** If we can't derive it from public evidence, we don't publish it — and we say
  plainly what we can't yet measure (that's the roadmap, not a secret).
- **Quality over keyword hacks.** Expertise and categories are LLM-judged, because "better curated" has to
  be true, not asserted.
- **Zero-dependency, strict-CSP static** is a feature. Don't add a framework without a real reason.
