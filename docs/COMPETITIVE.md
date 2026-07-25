# Competitive Analysis — tashan vs Agensi (and the marketplace field)

*Written 2026-07-23. Grounds on prior landscape/sentiment research in
`../../skills-marketplace-research/` and fresh web research (URLs cited inline).*

> **Note on the brief:** the prior research studied the *marketplace landscape* and
> Polar, not Agensi specifically — `grep -i agensi` over that repo returns nothing. So
> everything on Agensi below is fresh. Where a fact is self-reported or unverifiable, it
> is flagged as such rather than asserted.

---

## TL;DR

Agensi ([agensi.io](https://www.agensi.io/)) is a **curated store that sells AI-agent
skills** — SKILL.md skills (and some MCP servers) that install across 20+ agents, gated by
an automated security scan plus human review, with creators keeping ~70% of each sale
(Amsterdam-based, founder Samuel Rose, Antler-backed, launched ~April 2026, ~2,200 skills).
It is a *transaction* business. tashan is a *measurement* business. **tashan's single
defensible advantage is structural, not featural: it does not sell the inventory it
scores, so it can be a neutral rating authority — and Agensi, whose revenue is a 30% cut
of the very listings it would grade, structurally cannot follow it there without
cannibalizing itself.** A store rating its own shelf is Amazon's star ratings; an
instrument that rates the whole field on public evidence it doesn't monetize is Consumer
Reports. Agensi can bolt a "downloads" column on in a weekend; it cannot become credibly
disinterested about skills it profits from. That, plus compounding longitudinal evidence
(retention/churn from git history) Agensi has no window into, is the wedge. The top risk is
not Agensi — it is **platform risk** (Anthropic already ships a security-scanned "Verified"
directory) and tashan's **absent revenue model**.

---

## Agensi profile

**What it is.** A curated marketplace ("the skill store for AI agents") for SKILL.md skills
and MCP servers. Tagline: *"Give your AI agent superpowers. Stop building skills from
scratch."* Skills are delivered as SKILL.md files that "install in 30 seconds" across a
long list of agents — Claude Code, Cursor, Codex CLI, GitHub Copilot, Gemini CLI, Cline,
Windsurf, Aider, Zed, Amazon Q, and ~20 more.
Sources: [homepage](https://www.agensi.io/), [skills browse](https://www.agensi.io/skills).

**Business model — this is the core of what they are.** Agensi *sells* skills and takes a
cut. Creators earn **70% of every sale via Stripe** (i.e. a **30% platform take rate**);
skills are priced **$5–$50 one-time**, free listings allowed as reputation builders; a
**$9/month MCP subscription** was mentioned at launch; buyers get a refund policy and can
post "requests" (bounties) for creators to build against.
Source: [Sell Your Skills guide](https://www.agensi.io/learn/agent-skills-marketplace-sell-your-skills).
*(Discrepancy flagged: one search snippet and an older learn-page said "80%"; the dedicated
monetization guide and the landscape article both say 70/30. Treat 70% as current.)*

**Data model / what they measure — they curate and list; they do not measure.** The listing
view shows only **name, price, one-line description, and category**. There are **no download
counts, no install counts, no star ratings, no user reviews, no quality/eval scores, and no
evidence-based ranking** visible. Default sort is unspecified (appears category/recency).
Trust is asserted through process, not output: an **automated 8-point security scan** (file
structure, dangerous commands, secrets, env-var harvesting, network access, obfuscation,
prompt-injection screening) **+ a human review before a skill goes live**, plus
**identity-verified creators** and "Premium" labels.
Sources: [skills browse](https://www.agensi.io/skills),
[landscape article](https://www.agensi.io/learn/ai-agent-marketplace-landscape-2026).
In their own words they are *"a curated marketplace… quality over quantity, running
automated security scans"* — **curation, explicitly not measurement.** The same article
claims Agensi is *"the only platform that covers both SKILL.md skills and MCP servers."*

**Coverage.** **2,214 skills** listed (header "All Skills (2214)"), across eight categories
(Frontend & Design, Testing & QA, DevOps & Deployment, Code Review, Documentation,
Productivity, Data Engineering, API Development). This is *curated inventory that creators
chose to submit and sell* — not a census of the field.
Source: [skills browse](https://www.agensi.io/skills).

**Who's behind it / funding / timing.** Founder & CEO **Samuel Rose**; based **Amsterdam,
Netherlands**; **backed by Antler** (early-stage/accelerator — **amount undisclosed**;
Antler typically writes pre-seed checks ~$100–300K). **Launched ~April 2026** (Show HN dated
Apr 21 2026). Self-reported traction (July 2026): **2,000+ skills, ~3,000 registered users,
~50,000 monthly visitors, 200+ creators, "entirely organic, no paid ads."**
Sources: [press release (Newsfile/Manila Times)](https://www.manilatimes.net/2026/07/09/tmt-newswire/plentisoft/agensi-crosses-2000-skills-three-months-after-launching-its-ai-agent-marketplace/2381374),
[HN Show HN](https://hn.algolia.com/api/v1/search?query=agensi).
**Caveat:** traction figures come from a **paid newswire release** (Plentisoft/Newsfile),
not audited or earned media — treat as directional, not verified.

**Sentiment.** **Thin and low-signal.** The **Show HN got 1 point and 0 comments**
(Apr 21 2026) — effectively no organic HN discussion; a follow-up post got 2 points, 0
comments. No substantive Reddit/HN threads surfaced. [Trustpilot](https://www.trustpilot.com/review/agensi.io)
carries a few positive reviews ("easy to use," "like the scanning feature," "solved my
losing-time-searching-GitHub problem") but the page **403'd to direct fetch**, the reviews
read as early and possibly creator/seller-seeded, and **no critical reviews were
retrievable** — so this is weak evidence, not validation. Net: Agensi has a PR flywheel and
some organic traffic, but **no visible community mindshare yet**.

---

## Head-to-head

| Dimension | **tashan** | **Agensi** |
|---|---|---|
| **What it is** | Instrument — scores the field | Store — sells the inventory |
| **What it measures** | Trust = maintenance + freshness **gated by real adoption**; roadmap: retention/churn, expertise eval, security, cost | **Nothing measured.** Security-scan pass/fail + human curation only |
| **Data source** | Official MCP registry (coverage) + npm signals (downloads, cadence, maintainers, deprecation) + **mined public GitHub configs** (real adoption) + git history (retention) | Creator submissions (opt-in inventory); a security scanner |
| **Ranking method** | Transparent computed score from public evidence; **never pay-to-rank** | Curation + categories; **no evidence-based ranking** disclosed |
| **Trust / incentive model** | **Structurally disinterested** — does not sell what it rates (Consumer Reports / Michelin / Bloomberg) | **Structurally conflicted** — earns 30% of sales of the listings it curates; harsh honesty cannibalizes revenue |
| **Coverage** | Whole field (~2,000 from registry today; census, incl. things nobody submitted) | ~2,200 **curated, for-sale** skills (only opted-in supply) |
| **Monetization** | **None stated** (this is a risk) | **Shipped** — 30% take, Stripe payouts, $9/mo sub |
| **Moat / defensibility** | Compounding longitudinal evidence + neutral brand + incentive alignment | Two-sided liquidity, curation ops, creator relationships |
| **Target user** | The **evaluator** deciding what to trust/adopt (buyer-side, org, skeptic) | The **buyer** who wants a ready skill now + the **creator** who wants to get paid |
| **Status** | Data engine built; pre/early-launch instrument | Live marketplace with transactions, ~50k monthly visitors |

---

## Where Agensi is genuinely strong (no strawman)

1. **It has a business model and it ships revenue to creators.** The single most-cited unmet
   need in the prior research was **creator monetization** (demand high, delivery zero).
   Agensi *delivers it* — 70% Stripe payouts, one-time pricing, bounties. tashan has **no
   stated way to make money**. Agensi is a company; tashan is, today, an instrument.
2. **It's a running two-sided marketplace with liquidity.** ~200 creators, ~2,200 listings,
   ~3,000 users, ~50k monthly visitors, organic. Two-sided cold-start is the hardest thing
   in this space and they've cleared the first hump. That is distribution tashan doesn't have.
3. **Funded and promoting.** Antler-backed with a working PR flywheel (multiple syndicated
   releases). They can out-shout a quiet instrument in buyers' minds.
4. **A clean, shipped trust story for the mass buyer.** 8-point security scan + human review
   + identity-verified creators + refunds is a *concrete, today* answer to the #1 pain
   (trust/security). It may be "good enough" for most buyers who just want a safe file fast.
5. **Broader surface unit.** Covers **both** SKILL.md skills and MCP servers, and installs
   across 20+ agents — tashan is MCP-first today (skills on the roadmap).
6. **Simplicity.** "Install in 30 seconds" is a sharper consumer promise than "read the
   methodology and interpret a Trust score."

Take these seriously: Agensi is winning on **distribution, monetization, and time-to-value**
right now. tashan is not competing on any of those.

---

## Where tashan wins — and which parts are actually a moat

Be ruthless about the difference between a *nice-to-have difference* and a *moat a funded
competitor can't trivially copy.*

**Not a moat (copyable in a weekend):** showing download counts, npm cadence, star counts, a
"popularity" sort, even a basic freshness badge. Agensi could add any of these fast. If
tashan's story is "we show a number Agensi doesn't," that story is dead the day Agensi
ships a `downloads` column.

**The actual moat is three things Agensi cannot copy without ceasing to be Agensi:**

1. **Incentive neutrality (the load-bearing wedge).** tashan's authority comes from *not
   selling the thing it grades.* Agensi's revenue **is** a 30% cut of the listings it
   curates. The moment Agensi publishes an honest, evidence-based score, it is grading its
   own shelf — and a low score kills a sale it profits from. This is the Amazon-stars vs
   Consumer-Reports distinction, and it is **a business-model conflict, not a feature gap.**
   A well-funded competitor can copy a feature; it cannot copy disinterest while running a
   store. This is the one thing here that a weekend (or a Series A) can't buy.

2. **Coverage of the whole field on public evidence — including what nobody sells.** Agensi
   only knows its **opt-in, for-sale inventory** (~2,200 submitted skills). tashan measures
   the **entire field** from the official registry + public GitHub configs — including the
   free, the abandoned, the popular-but-unlisted, and the thin wrappers no creator would
   submit to a store. The evaluator's real question is "of *everything* out there, what
   should I trust?" — a store can't answer that about inventory it doesn't carry.

3. **Compounding longitudinal evidence — retention/churn from git history.** "Added then
   removed" is the most honest review there is, and it can only be *accumulated over time*
   from public commit history across the whole ecosystem. Agensi has **no window into this**
   — it sees a purchase, not whether the buyer ripped the skill out a week later. This data
   compounds: every month of history widens the gap and can't be back-filled by a competitor
   who starts later. The roadmap **LLM expertise-eval** (reading each SKILL.md/README to
   grade real expertise vs. thin wrapper vs. AI-slop) is *directionally* defensible too, but
   be honest: **anyone with an LLM budget can run an eval** — its defensibility is the
   *methodology + the longitudinal corpus it's applied to*, not the act of prompting a model.

**Sharpest one-line wedge:** *"GitHub evaluates code; stores sell listings; nobody neutrally
measures whether a capability is trusted or actually kept — because the people with the data
are the people selling the thing."*

---

## Risks to tashan (the honest list)

1. **Platform risk (bigger than Agensi).** Anthropic already runs an **Official plugin
   directory with an automated security screen + a human-reviewed "Anthropic Verified"
   badge** (prior research, `sources/01-landscape.md`). Anthropic owns the SKILL.md standard,
   the client, *and* the usage telemetry tashan can only infer from public proxies. If
   Anthropic (or GitHub, or npm) surfaces native evidence-based quality signals, tashan's
   core is absorbed by a party with better data and built-in distribution. **This is the
   existential risk, not Agensi.**
2. **No revenue model.** "Trust as an output, never pay-to-rank" is a *brand*, and a
   principled one — but principled neutrality is also *why you can't easily monetize the
   inventory*. If the answer to "who pays?" is unclear, tashan is a **cost center** —
   and continuous measurement/eval is expensive (the prior research flagged auditing as
   "the moat *and* the cost center"). Neutrality forecloses the obvious revenue (taking a
   cut of sales) — that tension must be resolved deliberately (data/API subscriptions,
   enterprise "what should we trust" reports, sponsorship-free by design).
3. **Measurement may not matter to most users.** Evidence-based scoring is a *connoisseur's*
   product (Bloomberg terminal = niche and expensive). The median buyer may be fully served
   by Agensi's "curated + security-scanned + refundable + 30 seconds." If trust-via-curation
   is "good enough," tashan wins the skeptics and orgs but not the market.
4. **A funded competitor can muddy the water.** Agensi can ship a shallow "popularity" or
   "verified quality" signal, *call it* measurement, and — with its distribution and PR —
   make buyers think the categories are the same. Shallow-but-visible can beat
   deep-but-quiet in a two-sided market where the other side already has liquidity.
5. **Erosion of the evidence source itself.** tashan mines **public** GitHub configs and
   npm. The more the ecosystem monetizes through **closed** stores (Agensi's paid skills are
   *not* public repos), the less public evidence exists to measure. Success of the store
   model literally shrinks tashan's raw material. Worth watching, and worth a plan
   (partner for private telemetry, or lean on the registry + retention signals that stay public).

---

## Recommended positioning (homepage-ready)

Stake the neutrality + whole-field measurement wedge. Three options, sharpest first:

> **"We don't sell capabilities. We grade them."**
> Every store ranks what it profits from. tashan scores the whole MCP field on public
> evidence you can audit — maintenance, freshness, real adoption — and the most honest
> review there is: who added it, then removed it. Trust you can't buy.

> **"The instrument, not the store."**
> Directories list. Stores sell. tashan measures — the entire field, on public evidence,
> never pay-to-rank.

> **"GitHub evaluates code. Nobody evaluates expertise. We do."**
> Not another marketplace. A trust score for every AI capability, computed from evidence
> anyone can check — so you adopt what actually works, not what's for sale.

**Do not** compete on catalog size, monetization, or install speed — Agensi wins those
today. **Compete on the one axis a store can never own: disinterested, whole-field,
evidence-based trust.**

---

## Sources
- Agensi homepage — https://www.agensi.io/
- Agensi skills browse (coverage/metadata) — https://www.agensi.io/skills
- Agensi "Sell Your Skills" (70% rev-share, pricing) — https://www.agensi.io/learn/agent-skills-marketplace-sell-your-skills
- Agensi landscape article (self-positioning, curation-not-measurement) — https://www.agensi.io/learn/ai-agent-marketplace-landscape-2026
- Press release (founder, Antler, traction) — https://www.manilatimes.net/2026/07/09/tmt-newswire/plentisoft/agensi-crosses-2000-skills-three-months-after-launching-its-ai-agent-marketplace/2381374
- HN Show HN (1 point, 0 comments) — https://hn.algolia.com/api/v1/search?query=agensi
- Trustpilot (thin/seeded, 403 on fetch) — https://www.trustpilot.com/review/agensi.io
- Prior landscape/sentiment research — `../../skills-marketplace-research/sources/01-landscape.md`, `02-sentiment.md`, `REPORT.md`

**Unverified / flagged:** Antler funding amount (undisclosed); all traction numbers
(self-reported via paid newswire); 70% vs 80% rev-share (using 70% per dedicated page);
Trustpilot review authenticity (unretrievable, likely seeded).
