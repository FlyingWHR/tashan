# tashan — monetization strategy: creator sales, thin cut, and the "rendering" service

> **Ask (founder, late-night):** enable creators to sell; give the creator as large a share as possible;
> tashan takes a *very thin* cut. Also: "do we consider a service like **rendering**?" — evaluate it.
>
> **This doc evaluates that comprehensively and recommends a path. It does not build a store — the pivot
> below needs a founder decision first, because it touches the one thing the whole project is built on.**

---

## 0. DECISION (confirmed by founder): tashan is a store. The thesis is reframed.

The old thesis made the moat *not transacting* ("we don't sell what we score"). **Decision: tashan becomes a
store.** The thesis is reframed — and the reframe is *stronger*, because it turns the one thing that made a
store untrustworthy into tashan's differentiator.

### The reframe
**tashan is the measured marketplace — the only store where the ranking can't be bought.** Every other store's
ranking is pay-to-play (sponsored slots, promoted listings, a cut that rewards moving inventory). tashan sells
capabilities too, but its **ranking is evidence, not spend**, and it stays that way because of *how* tashan
takes its cut.

### The structural mechanism (this is what makes it honest, not spin): a thin, FLAT, outcome-independent cut
- Agensi **structurally cannot** publish honest scores: its **30% cut means honesty costs real margin** —
  trashing a listing cannibalizes its own revenue, so it doesn't.
- tashan takes a **thin, flat fee — identical whether a capability scores 9 or 1**. Publishing "this is slop"
  costs tashan ~nothing. **The flat thin cut is the structural enabler of neutral ranking *inside* a store.**
  Thinness here is not optics; it removes the incentive to favor what sells. A *percentage* cut would
  re-introduce that incentive — hence **flat, never %** is non-negotiable (§3).

### The reframed firewall (shifts, doesn't disappear)
> **You can never pay to *rank*. The cut is thin and flat — the same for a 9 or a 1 — so we can afford to rank
> on evidence and tell you the truth about what we sell. Free and paid capabilities rank side-by-side. No
> sponsored slots, no promoted placement, ever. Creators keep more, because we make our money on the rails,
> not a toll on your grade.**

### Why this is a better position than the purist one
- It's a **store people can actually transact on** (revenue: transaction fee + the rendering/delivery service).
- It keeps the **un-buyable evidence ranking** as the trust anchor — the thing no other store can credibly offer.
- **Creator-favorable economics** (keep ≥90%) become a growth weapon vs Agensi's 70%, *and* a neutrality signal
  (we're not extracting, so we're not incentivized to inflate).
- Moat one-liner (reframed): *"A competitor can open a store in a weekend; it can't add an un-buyable ranking —
  because its economics won't let it tell the truth about its own shelves."*

---

## 1. Three monetization models, evaluated

| | **M1 · Marketplace** (tashan is seller-of-record, thin cut of each sale) | **M2 · Referral** (tashan points to the creator's own sale, takes a referral fee) | **M3 · Neutral service** ("rendering"/delivery + Pro/API) |
|---|---|---|---|
| **Neutrality fit** | ⚠️ Low — direct sale-cut incentive; needs a hard firewall to survive | 🟡 Medium — no inventory held, but a per-sale referral fee still ties $ to sales | ✅ High — charges for a *utility*, not for the score/sale; matches the existing firewall verbatim |
| **Creator share** | ~90–95% (our positioning weapon vs Agensi's 70%) | ~100% minus a small referral fee | 100% of their sale (we don't touch it); we charge the *service* separately |
| **Revenue quality** | Transaction margin (scales with GMV) | Thin referral margin | Recurring/usage (SaaS-grade, high-margin, un-tainting) |
| **Build cost** | High — payments, payouts, refunds, fraud, tax, merchant-of-record, disputes | Low — outbound links + attribution | Medium — the backend we already roadmapped (D1 + Functions) |
| **Moat** | Weak — Agensi already does this better and earlier | Weak — anyone can link | **Strong** — neutral, cross-ecosystem delivery no *store* can credibly run |
| **What it makes tashan** | A store (Agensi with a thinner cut) — abandons the wedge | A directory with affiliate links | **The neutral instrument + the neutral utility layer** — the thesis, intact |

**Read:** M1 is the ask taken literally, and it is the weakest strategic position — it converts tashan's unique
asset (disinterest) into a commodity (a cheaper storefront) and walks onto Agensi's home turf where they lead on
supply, SEO, and 3 months of head start. M3 is the founder's own "rendering" instinct, and it is the strongest —
it monetizes the thing a store *can't* be trusted to run, and it's already sanctioned by the firewall.

---

## 2. Deep-dive: the "rendering" / delivery service (recommended core)

**Interpretation.** "Rendering" ≈ **serving a capability to an agent on demand** — the neutral infrastructure that
turns a scored listing into a running tool: resolve → verify → install/stream → keep it current. This is exactly
Agensi Pro's "skills load on demand via MCP," **but neutral across the whole field instead of one store's SKUs.**

### 2.1 What it is (the product)
A single **tashan MCP endpoint** (and CLI) an agent connects to once, that can install / stream / update **any**
capability tashan tracks — MCP servers *and* skills — with tashan's measured layer wrapped around it:

- **Curated on-demand loading** — only capabilities above a Trust bar load into the agent's context (the Agensi
  Pro flood problem, solved: theirs loads "the full catalog"; ours loads *what passes the bar*, saving the
  context window the HN crowd complains about).
- **Verified delivery** — every served artifact is checksum/version-pinned and security-checked; "you ran exactly
  what we scored." A store can't credibly promise this about goods it profits from; a neutral utility can.
- **Always-latest** — like subscription skills, but as a *delivery guarantee*, not a sales model.
- **One install, N clients** — solves the real pain (the same server needs five different config snippets):
  tashan renders the right install for Claude Code / Cursor / Claude Desktop / Codex / Gemini CLI.

### 2.2 Why it's neutral (survives the firewall)
You pay for **compute + delivery + freshness + verification** — a utility. You do **not** pay to change a score,
buy a rank, or list. A free capability and a paid one are delivered identically and scored identically. Revenue is
**decoupled from the score**: tashan earns the same whether the thing it serves is great or mediocre — it's paid
for *serving*, not for *outcome*. This is the firewall's "depth, access, and tooling," verbatim.

### 2.3 Technical shape (fits the existing roadmap — no rewrite)
- **Cloudflare Workers/Functions + D1** (the roadmapped backend; D1 = SQLite, our pipeline schema ports as-is).
- The Worker is an **MCP server** that proxies/streams the underlying capability and pins versions; a small
  **usage-metering** table in D1 (`renders(cap_id, account, at, bytes)`); the static site stays static.
- The install-rendering (per-client snippets) is **already computed** in `build.py` — this productizes it.
- ~2–4 weeks for an MVP endpoint; the hard parts are metering + auth, not the delivery.

### 2.4 Pricing & moat
- **Pro $6/mo** already exists — bundle rendering into it (unlimited curated on-demand loads + always-latest +
  one-connection multi-client). Usage/**API tier** on top for teams/agents (per-render or per-seat).
- **Moat:** a *neutral, cross-ecosystem, verified* delivery layer is something no single store can be trusted to
  operate (they'd favor their own SKUs). It compounds with the score data (curation) and the badge/backlink loop.
  It is the on-thesis version of Agensi's strongest new move.

### 2.5 Risks
- **Liability/hosting** of third-party code you didn't write (proxy/pin, don't rehost; ToS + security-scan gate).
- **Upstream trust** — you're now in the execution path; a bad upstream reflects on you (mitigate with the
  verification/pinning that is *also the selling point*).
- **Anthropic platform risk** — they ship "Verified" delivery too; stay neutral & cross-ecosystem (their edge is
  Claude-only), and lead on *measurement*, which they don't do.

---

## 3. If we still enable creator *sales* — the only way it survives neutrality

The founder may want a storefront regardless (creator-favorable economics are a real wedge vs Agensi's 70%). It can
coexist with the instrument **only** behind an absolute firewall. Non-negotiable invariants:

1. **The scoring engine is blind to sale status.** It never reads price, GMV, or "for sale on tashan." A capability's
   Trust/expertise/rank is byte-identical whether it's free, sold elsewhere, or sold on tashan. (Enforce in code:
   the scorer's input row literally cannot contain commerce fields.)
2. **No promoted placement, ever.** No "sponsored," no pay-to-rank, no boost. The board is evidence-sorted only.
3. **Revenue ≠ score.** tashan's take is a **flat, sale-agnostic** processing/service fee (or $0 + the rendering
   service is the business), *not* a percentage that makes tashan richer when a scored item sells more. A flat
   per-transaction fee (e.g. "$0.30 + Stripe cost, creator keeps the rest") is far more defensible than "we take 5%."
4. **Creator is seller-of-record where possible** (Stripe Connect direct-charge / referral), so tashan isn't the
   merchant grading its own inventory — it's the rails.
5. **Public disclosure.** State the firewall on the storefront the way the methodology states the scoring one. The
   disclosure *is* the product ("we make the same money whether this sells or not").
6. **Creator share as a weapon:** "Creators keep **≥90%** — the highest of any marketplace, because we don't make
   our money on your sale, we make it on the tooling." That line only rings true if #3 holds.

**Honest caution:** even with all six, a storefront dilutes the "we sell *nothing* we score" story that is the
cleanest version of the moat. M3 (service) keeps that story pristine. If you want sales, do them via **referral
(M2)** first — it's the lowest-tension way to test creator demand without becoming a merchant.

---

## 4. Recommendation (phased) — store confirmed

**tashan is a store.** Two revenue lines, both behind the §3 firewall:

1. **The marketplace (M1).** Creators sell; buyers buy; tashan takes a **thin, FLAT** transaction fee — creators
   keep **≥90%** (the headline number, vs Agensi's 70%). Seller-of-record = the creator via **Stripe Connect
   direct-charge**, so tashan is the rails, not the merchant grading its own goods. **Flat, never %** — this is
   the load-bearing invariant that keeps honest ranking affordable (§0).
2. **The rendering / delivery service (M3).** Bundle into **Pro** + a usage/API tier: one MCP endpoint that
   installs/streams/keeps-current any capability, curated by the Trust bar, verified. High-margin, on-brand
   ("the rails"), and the answer to Agensi's subscription/MCP move.

**Build order:** (a) **reframe the narrative site-wide** (this turn — done for the key surfaces); (b) stand up
the **backend** (Cloudflare D1 + Functions — the roadmap item; schema ports as-is) for accounts, listings, and
metering; (c) **Stripe Connect** checkout with the flat fee + creator payouts; (d) the **rendering endpoint**.
Steps (c)/(d) need founder setup (Stripe account, legal entity, ToS, tax) — not built unattended.

**Never** let commerce touch the scorer: the scoring engine's input row literally cannot contain price / GMV /
for-sale fields. Ship the firewall as a public, checkable guarantee — same standing as the methodology page.

**One-line positioning:** *The measured marketplace. Buy what works — the ranking is evidence, not spend — and
creators keep more, because we make our money on the rails, not a toll on your grade.*

---

## 5. What needs the founder (the decision on waking)
- **Approve M3 (rendering service) as the monetization core?** (Recommended — on-thesis, needs the D1/Functions backend.)
- **Sales model:** referral-first (M2, recommended) vs hosted store (M1)? And **flat fee vs %** (flat strongly recommended)?
- **Creator share number** to advertise (≥90%? 100%-minus-flat?).
- Confirm the six firewall invariants are acceptable as public commitments.

Nothing here is built yet — this is the evaluation you asked for. The concrete, thesis-safe improvements shipped
overnight are in `docs/OVERNIGHT.md`.
