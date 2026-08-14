# Product feature audit — what is claimed, what is delivered, on which surface

Audited 31 Jul 2026, from the copy and the code rather than from intent.

> **Status: resolved the same day — see "Resolved" at the end.** The findings below are kept in the
> past tense as the record of what was wrong and why, because the shape of this defect is the one
> most likely to come back: copy is edited far more often than plumbing, and nothing errors when a
> bullet point outruns the code.

## The finding in one line

**Pro sold five things and delivered two, and the website — where people buy — differentiated
nothing at all.** `capability.js` never checked whether the reader held a licence, so a paying,
signed-in customer saw byte-for-byte what a stranger saw on every page of tashan.sh.

## What the pricing page sells

| # | Pro claim (verbatim from `web/pricing.html`) | Delivered? | Where |
|---|---|---|---|
| 1 | "The advisory itself — which CVE or GHSA, its severity, the affected range, and the version that fixes it. Not '2 known advisories'." | **NO** | nowhere |
| 2 | "What the install script actually runs, and the full permission list with the dependency that pulled each one in." | **NO** | nowhere |
| 3 | "The replacement, named. Not 'this is deprecated' — switch to this one, it scores 65." | yes | `tashan doctor` only |
| 4 | "Every score since we started measuring." | yes | `tashan doctor --trend` → `/api/history` |
| 5 | (implied by the "unlock detail" links on every capability page) | **NO** | the link goes to `/pricing.html` and nothing behind it changes |

Claims 1 and 2 have **no implementation anywhere**: no endpoint serves them, no CLI path prints
them, `capability.js` makes no gated fetch. Until the previous commit they were also readable by
anyone in `/data/capabilities.json`, which made the same curl both the leak and the only way to
obtain what Pro advertises.

The FAQ on that same page is already honest — *"What am I paying for today? Named replacements for
anything dead in your config, and the full score history."* — so the page contradicts itself: the
feature list sells five things and the FAQ admits to two.

## Differentiation by surface

| Surface | Free sees | Pro sees | Differentiated? |
|---|---|---|---|
| `/` the board | score, evidence, freshness, finding flags | identical | **no** |
| `/capability/*` dossier | every finding named, "unlock detail" links | identical | **no** |
| `/category/*`, `/task/*`, `/browse` | ranked tables | identical | **no** |
| `/badge/*.svg` | score | identical | **no** |
| `llms.txt`, subregistry | top 40, scores | identical | **no** (deliberate — that is distribution) |
| **MCP server** (`find_capability`, `check_capability`, `audit_config`) | finding counts | identical | **no** |
| **CLI `doctor`** | finding exists, "N alternatives measured better" | **the replacement names** | **yes** |
| **CLI `doctor --trend`** | — | **the score series** | **yes** |
| `/api/history` | 403 | the series | **yes** (but only `--trend` calls it) |

Two of nine surfaces differentiated, and both were the CLI. **The entire web product was
undifferentiated**, including the page that carries the buy button and the page a customer lands on
after paying.

## Why this is worse than a missing feature

1. **The unlock link is a promise with nothing behind it.** A customer clicks "unlock detail",
   pays $6, returns to the same page, and sees the same "unlock detail" link. There is no state in
   which that link resolves.
2. **The MCP server is the stated distribution strategy** ("we want agents, hosts and IDEs calling
   them — that *is* the distribution") and it has no paid tier at all. The agent is the primary
   consumer per `PROJECT.md`, and the agent can never buy anything.
3. **`/api/account` already sets a session cookie that `keyFrom()` reads.** The gate plumbing to
   differentiate the web exists and is tested; nothing consumes it except `/api/history`.

## What is genuinely free, and must stay free

This is not a list of things to gate. The firewall in `PROJECT.md` §12 and the pricing page both
commit to it, and the audit confirms the code honours it:

- every tashan score, and its components
- every expertise grade
- **the existence of every security finding** — how many advisories, at what severity, that an
  install script exists, that a permission surface exists
- `doctor`'s verdicts on a config
- the agent endpoints, badges and the subregistry

`tests/test_consistency.py` fails if the free signal is ever removed, and `tests/test_firewall.py`
fails if a score ever reads a commerce column.

## The three ways out (as considered at the time)

Stated plainly because this is a business decision, not an engineering one. **A was chosen.**

**A. Build the delivery path** (~40 lines, reuses `_license.js` unchanged): a gated
`/api/security?id=` returning `sec_advisories`, the install command and the full permission list;
`capability.js` fetches it when signed in and swaps each "unlock detail" for the real value; the CLI
prints it in `doctor` and `info`. This makes claims 1, 2 and 5 true and differentiates the web.

**B. Stop selling what is not built.** Cut claims 1 and 2 from the pricing page and remove the
"unlock detail" links, leaving Pro as replacements + history — which is what the FAQ already says.
Honest immediately, and smaller. But it leaves the web undifferentiated and the security audit,
described in `CLAUDE.md` as "the core paid feature", earning nothing.

**C. Change what Pro is.** Keep every finding free forever and sell the thing the CLI already does
well — continuous monitoring of *your* config, alerts when something you run degrades. That is
`watch-your-stack`, already marked "not built yet" on the pricing page.

A and B are not exclusive: B today (so the page stops overclaiming), A next.

## Resolved — option A, built 31 Jul 2026

| | before | after |
|---|---|---|
| Pro features sold | 5 | 5 |
| Pro features delivered | 2 | **5** |
| surfaces that differentiate | 2 of 9 (both CLI) | **4 of 9** (CLI ×2, web dossier, API) |

- `functions/api/security.js` — **now FREE and ungated** (it returned only current state, which the
  public export already carries; see docs/X402.md). Returns the
  advisory list, the install command and the full permission list. 10 tests, every negative path
  first: no licence, invalid licence, provider down, unconfigured deployment — a paywall that fails
  open would give away the one thing $6 buys while still charging for it.
- `pipeline/push_security.py` — 255 capabilities with paid detail across 62 KV shards, same bucket
  arithmetic as `push_history.py` so the two paid paths cannot drift. Runs nightly via `run.py`, and
  SKIPS loudly without credentials rather than failing the measurement.
- `web/js/capability.js` — asks for the detail after the free page is painted, and replaces each
  "unlock detail" in place. **This is the first time any web surface has differentiated for a paying
  customer.** The browser session cookie set by `/api/account` is the credential, so being signed in
  is enough.
- `cli/tashan.mjs` — `doctor` prints the advisory id and fixed version, the install command and the
  full permission list under the finding they explain, on the surface whose free output advertises
  exactly that.

`tests/test_promises.py` fails the build if a claim on the pricing page loses its delivery path, and
also fails if the free floor is ever reduced.

### Still not differentiated, deliberately

The **MCP server** and the **subregistry** remain entirely free — that is the distribution strategy
in `PROJECT.md`, not an oversight. The board, hubs and badges stay identical for everyone because
the score and every finding's existence are free forever.


---

## Follow-up: is "every score since we started measuring" worth $6? — 31 Jul 2026

Asked directly, and the data says **not today**, for three stacked reasons.

**1. There is almost no comparable history.** `trend()` correctly refuses to compare across scorer
versions, and only **2 days** sit under the current one. It needs 3, so a paying customer runs
`doctor --trend` and is told "not enough comparable history yet". Honest, and worth nothing.

> **Update, 8 Aug 2026 — one of those two missing days was never missing.** The daily workflow
> commits `data/history` on a red suite and withholds the database, so the DB fell behind the shards
> and nothing reconciled them: the shards held twelve days while `signal_history` held ten. `trend()`
> and the exported `retention` read the DB, so both were understating the series against evidence
> sitting in the same repository. `snapshot_history.restore()` now runs first on every pipeline run
> and put 37,943 rows back — **s5 has 4 comparable days, not 2, and `trend()` answers today.**
>
> Four days are still genuinely gone (07-26, 07-31, 08-02, 08-07): the pipeline step had no
> `continue-on-error`, so a crash in any of the five source stages that run before the snapshot
> failed the job and skipped the commit. Fixed, and `tests/test_history_integrity.py` now fails if
> anyone removes the guard. **The conclusion below still stands** — the series answering is not the
> same as the series being worth $6, and the advisory detail is still the stronger claim.

**2. The window before it was contaminated, and the guard missed it.** Between 28 and 29 July the
scale was stretched while both days were still labelled `s1`:

| score on 28 Jul | n | median change overnight |
|---|---|---|
| 10–19 | 111 | −1.0 |
| 30–39 | 1,253 | −1.0 |
| 50–59 | 511 | +0.0 |
| 70–79 | 17 | +6.0 |
| 80–89 | 7 | +7.0 |

supabase went 85 → 99 and firecrawl 75 → 93 overnight. A recalibration moves whole bands in order;
real churn does not sort itself by score. 29 → 30 July shows a band spread of **0.0**, which proves
29 and 30 are the same scale and the version bump was simply recorded a day late — so the points were
relabelled `s2`, on that evidence. `tests/test_scorer_version.py` could not catch this: it
fingerprints `compute_scores()` source text, so it is blind to a recalibration arriving through data
or a changed input, and it cannot fire at all if the suite is not run between the change and the
commit. `tests/test_history_integrity.py` now checks the OUTPUT, where the damage appears.

**3. Even clean, a score series is weakly actionable.** "supabase went 85 → 86" is not a decision.
Compare it to the security detail, which is: *this advisory, fixed in 1.2.0, upgrade*. Trend is a
real **moat** — a day not recorded is gone for everyone, including us — but a moat is a barrier to
competitors, not a reason for a customer to pay this month.

### What to do

- **Now:** stop leading with it. The pricing page already carries `trend needs ~30 days · clock
  restarted 30 Jul`; that honesty is right but it is selling an IOU. The advisory detail and the
  named replacement both work today and are what the $6 should rest on.
- **~30 days:** revisit. With a clean `s2` window the series becomes chartable and the claim becomes
  true rather than promissory.
- **The version it should become:** not "here is a chart of a number", but *"something in YOUR stack
  moved"* — the watch/alerts feature already marked `not built yet`. The series is the input to that
  product, not the product. Nobody wants a time series; they want to be told when to care.
