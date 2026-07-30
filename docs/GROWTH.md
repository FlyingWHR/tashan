# tashan — Revenue & PLG engine

*2026-07-23. How tashan makes money without breaking the one thing that makes it valuable
(neutrality), and the product-led growth loops that compound coverage into a moat.*

---

## The core tension (and the resolution)

tashan's moat is **structural neutrality** — it doesn't sell the inventory it scores (see
`COMPETITIVE.md`). The obvious monetizations all break it: pay-to-rank, promoted listings,
taking a cut of sales. So the rule is absolute:

> **You never pay to change a score, a rank, or a listing. You pay for depth, access, and tooling.**

Everything below respects that firewall. The public Index — every capability, every score,
the methodology — stays **free forever**, because the free tier *is* the growth engine.

---

## Revenue: subscription (start here)

One small subscription now; expand tiers later. The free/paid line is drawn at **depth and
scale**, never at the integrity of the public data.

| | **Free** (the instrument) | **tashan Pro — $6/mo** ($60/yr) |
|---|---|---|
| The Index, all Trust/Expertise scores | ✓ | ✓ |
| Command-palette search, methodology | ✓ | ✓ |
| Capability detail + expert read + install path | ✓ | ✓ |
| **Watch / alerts** (email when a capability you use is deprecated, churns, or a score drops) | 3 watches | unlimited |
| **Compare** (A vs B vs C, side by side) | 2 at a time | unlimited + saved |
| **API / CLI access** (scores, JSON, badges at scale) | 60 req/day | full |
| **Trends & history** (score over time, the longitudinal data) | last 30d | full history |
| **On-demand deep expertise** (grade any capability now, not just top-ranked) | — | ✓ |
| **Export** (CSV/JSON of any view) | — | ✓ |

> **This table is the PLAN, not what ships today (checked 2026-07-29).** Watch/alerts, compare, and
> on-demand grading are unbuilt, and the free API is deliberately **unmetered** rather than 60/day —
> free and uncapped *is* the distribution strategy, and a static site cannot meter without auth
> anyway. The free tier advertised three of these rows as live and a visitor could falsify all three
> in thirty seconds; that shipped and had to be removed. **Nothing from this table goes on
> `pricing.html` until it exists.** What Pro actually sells today is full score history over a keyed
> API — see `docs/PAYMENTS.md`.

Why **$6** (round, not $5.99 — .99 reads retail; was $12): the sweet spot is *cheap enough to be a no-question signup* (Brave Search
Premium = $3) while premium *feel* comes from the product + a generous free tier + one clean number,
not the price. Cheap consumer tier is top-of-funnel; the real money is later (Team/Data). Annual
($60) nudges cash + retention.

### Payments — crypto from day 1
Accept **card or USDC** (Coinbase **x402**). Crypto isn't a roadmap item, it's a launch convenience:
instant, global (180+ countries, no bank/KYC), machine-native. Two paths:
- **Subscription** payable in card or USDC.
- **Pay-per-use micropayment** — **$0.20 USDC** deep-grades any capability on the spot, no account.
  Sub-cent-friendly rails make this the lowest-friction possible entry *and* a showcase of the
  convenience. (Live on `pricing.html`.)
The full 8-layer agent trust-stack (escrow, ZK, insurance) stays **roadmap** — see On-chain below.

**Later tiers (not now):** *Team* ($40/seat — private capability audits for an org's own
internal skills/MCP servers, SSO, shared watchlists) and a *Data* tier (the full evidence
base via API for platforms/registries that want to embed tashan scores). The Team tier is
where real money is — orgs auditing what their agents are allowed to run — but it needs the
free flywheel spinning first.

**What we will never sell:** rank, placement, a "verified" badge you buy, or removal of a bad
score. If a maintainer could pay to look better, the whole instrument is worthless.

---

## The PLG engine — loops, not funnels

A funnel leaks. A **loop** feeds its own top. tashan has four loops; each also deepens the
structural moat (more coverage → more evidence → better scores → more reason to embed → more
coverage).

### Loop 1 — Badges (the flagship, ship first)
Every measured capability gets an embeddable SVG badge: `tashan ▸ Trust 91 · deep`.
Maintainers put it in their README because a good score is social proof they *want* to show.
- **The loop:** we measure X → maintainer embeds the badge → every visitor to X's repo sees
  tashan + a backlink to the capability page → some click through, some are maintainers who
  want their own badge → they check *their* score → they embed → repeat.
- **Why it's structural:** this is the [shields.io / "Powered by Vercel"] pattern — thousands
  of backlinks we don't pay for, SEO authority no competitor can buy, and a brand impression
  on the exact repos that matter. A store *can't* run this loop: nobody proudly embeds "for
  sale on Agensi." You embed a *measurement*, not a price tag.
- Free for all; Pro unlocks badges at scale via API for orgs with many repos.

### Loop 2 — SEO surface (capability + compare pages)
Every capability page and every `A vs B` compare page is a long-tail landing page for the
exact query a developer types: *"is context7 mcp good," "notion-mcp vs …," "best mcp server
for kubernetes."* 2,000 capabilities × compare permutations = a large, honest, evidence-rich
SEO surface that directories (thin listing pages) and stores (sales pages) can't match on
depth. **The loop:** more coverage → more indexed pages → more organic search → more traffic →
more badge installs → more coverage.

### Loop 3 — The CLI / developer touchpoint (`npx tashan-cli`)
`npx tashan-cli check` reads your `mcp.json` / `claude_desktop_config.json` and prints a Trust +
Expertise readout for everything you're running — right in the terminal where the audience
lives. Flags the thin/deprecated ones. This is *distribution inside the workflow*: it runs
where the decision is made, links back to the site for detail, and is the natural top of the
Pro/API conversion. (Also the most on-brand possible surface — tashan literally *is* a
terminal readout.)

### Loop 4 — Watch / alerts (retention + re-engagement)
Free users watch up to 3 capabilities; we email them when something changes (deprecated,
score drop, replaced-by-something-better, new CVE). This is the retention loop *and* the Pro
wedge — the moment you're running 10+ capabilities in production, unlimited watches + trend
history is worth $6. Every alert is a re-engagement touchpoint that pulls people back.

### Activation path
Land (SEO / badge / CLI / share) → `⌘K` search or scan the Index → open a capability → the
**aha is the expertise verdict + expert read** (nobody else has it) → watch it (free) → hit a
depth limit → Pro.

---

## Touchpoint map — everywhere tashan shows up

| Surface | Touchpoint | Loop |
|---|---|---|
| GitHub repos / READMEs | Embedded badge | 1 |
| Google / AI search | Capability & compare pages | 2 |
| The terminal (dev's home) | `npx tashan-cli` CLI | 3 |
| Email inbox | Watch alerts, weekly "movers" digest | 4 |
| Social / Slack / X | Shareable capability OG cards | 1,2 |
| Agent / IDE | tashan score in-context (later: MCP that returns scores) | 3 |
| The site | Command palette, ticker, Index | all |

The compounding claim: coverage and longitudinal data are **cumulative and can't be
backfilled**. Retention/churn history from git needs *time* to accrue — a competitor starting
today can copy the schema but not the two years of "added-then-removed" signal. Every loop
above adds coverage or data; the moat is the integral of the loops over time.

---

## Sequencing

1. **Now:** Badges (loop 1) + command palette + Pro pricing page. The badge is the growth
   primitive; ship it first.
2. **Next:** Compare pages (loop 2 SEO) + Watch/alerts (loop 4, needs a tiny backend or a
   serverless function + email).
3. **Then:** `npx tashan-cli` CLI (loop 3) + per-capability OG image generation.
4. **Later:** Team tier + Data API + in-agent MCP that returns tashan scores.

---

## Product roadmap — from leaderboard to curated catalog

The Index today is a ranked leaderboard. To match (and beat) directories/stores it needs to be a
**category catalog** — browse by domain, ranked *within* category, better-organized and more curated
than the competition. Staged because these need new data work, not a UI tweak:

- **DONE this pass:** install path (`npx` + `mcp.json` snippet) + links to the original (npm/source/
  registry) on every detail page; **official model-company tagging** (Anthropic/OpenAI/Google/Microsoft,
  detected from npm scope / repo owner, jade "✓ official" tag on board + detail); coverage raised (all
  ranked capabilities exported, not top-400).
- **Categories** (next): assign each capability a category (browser, database, search, devops, design,
  docs, data, comms, …). Do it *right* — LLM-classify like the expertise-eval (a keyword hack undercuts
  the "better curated" claim). Then a catalog IA: category browse + within-category ranking + facets.
- **Skills, not just MCP:** ingest agent-skills (Claude/Anthropic official skills, and the best
  community ones — e.g. **impeccable** for design). New crawlers per source; unify skills + servers under
  one capability model with a `kind`. Include **all** official skills from model companies, visually tagged.
- **Coverage to parity+:** crawl the remaining registries/awesome-lists/npm-search so listing count
  meets or beats Agensi/mcp.so/Smithery — then win on depth (expertise, retention) they don't have.
- **Real-usage crawl:** deepen beyond config-adoption + npm — GitHub dependents, awesome-list inclusion,
  first-party docs — as additional evidence columns.

These need the same small **backend** (D1/Postgres + Functions) that alerts/API/billing need — one
investment unlocks catalog persistence, faceting, crypto payments, and Pro.

---

## On-chain trust (later — the neutral crypto play, not a payment rail)

Per the competitive analysis: **don't become the payment rail** (that sells what we score, breaking
neutrality — see `COMPETITIVE.md`). Become the **reputation oracle the rails read**: publish tashan's
Trust/Expertise as portable, verifiable **ERC-8004** reputation that x402/AEP2/escrow contracts query
*before* releasing funds. Picks-and-shovels trust layer. Monetize via protocol/enterprise **API access**
(Data tier), never a transaction cut. The 8-layer stack (escrow, ZK, insurance) is *their* layer to build;
ours is Discovery + Reputation + Verification (layers 1, 6, 7 — which tashan already occupies).

Weakest link to watch: alerts and API need state/compute the current static site doesn't have
— that's the trigger to add a small backend (Cloudflare D1 + Functions, or Supabase), which
was already the planned prod DB path.
