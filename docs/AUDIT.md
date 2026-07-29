# Hard audit — 2026-07-29

Written to be useful, not encouraging. Evidence from the live database and repo, not from the plan.

> **Update, same day: §1 is fixed.** See the "Fixed" block at the end of §1 for the measured result and
> what it cost. Everything else below stands as written.

**Verdict up front: this is a strong data asset, a credible position, and not yet a business.** The
engineering is genuinely ahead of most of the field. Revenue infrastructure is at zero, the headline
number does not discriminate, and there is no evidence any user wants this yet because nobody has ever
seen it.

---

## 1. The score does not discriminate — the most serious product defect

| percentile | tashan score |
|---|---|
| p10 | 17 |
| p25 | 20 |
| **p50** | **27** |
| p75 | 32 |
| p90 | 39 |
| p99 | 56 |
| max | 90 |

**Half of all 6,200 scored capabilities sit inside a 12-point band. 98% score below 50. Four things in
the entire corpus score 80+.**

A 0–100 scale where almost everything lands between 20 and 32 carries almost no information. "tashan
score 27" and "tashan score 31" are indistinguishable to a user, and both read as *bad* on a 100-point
scale even when the capability is fine. The single most important number in the product currently fails
at its one job: separating things.

Cause is known and self-inflicted. Lowering `GATE_FLOOR` 0.6 → 0.3 was right in direction — the old band
was 60–100 because 60 was free — but it overshot, and the coverage discount compounds it: most rows are
missing an axis, so nearly everything is multiplied down twice. The commit at the time said "scores
compress downward, that is the fix, not a regression." That was half right. Compression toward honesty
is correct; compression into a 12-point band is not.

**Fix, in order:** report the score as a *percentile or grade band* alongside the raw number, or
re-spread the scale so the middle of the field sits near 50. Do this before deploy — a public number is
much harder to re-baseline afterwards, and every badge already in the wild would shift.

### Fixed — 2026-07-29

Diagnosis above was half right. The gate is the compressor, but not because `GATE_FLOOR` overshot: the
real cause is that **a capability with no adoption evidence has `gate == 0.30`, capping it at raw 27/100
however well kept it is — and 38% of the corpus (2,361 of 6,200) has neither a download count nor a star
count.** More than a third of the index was structurally incapable of exceeding 27. Raising the floor
would fix the range and re-break the ranking the floor sweep exists to protect, so the two jobs were
separated instead:

1. **Adoption anchors are now absolute, not the corpus max** (`DL_FULL` / `STAR_FULL` / `REACH_FULL`).
   Log-normalising against the largest row put the median at the bottom of the scale, and meant one new
   2M-download package silently restated every badge already minted. Worth doing, but on its own it moved
   p50 by 2 points — it fixes the top of the range and badge stability, not the band.
2. **A fixed, strictly order-preserving calibration** (`_calibrate`, knee at raw 50 → 68) stretches the
   dense lower field onto the published scale. Because it is monotone it *cannot* reorder two
   capabilities, so no inversion killed by an earlier sweep can come back — asserted in
   `tests/test_score.py`, and every candidate in the sweep was checked for zero inversions.

| percentile | before | after |
|---|---|---|
| p25 | 20 | **28** |
| p50 | 27 | **39** |
| p75 | 32 | **46** |
| p90 | 39 | **58** |
| p99 | 56 | **76** |
| IQR width | 12 | **18** |
| scoring below 50 | 98% | **81%** |
| scoring 80+ | 4 | **39** |

Deliberately *not* taken all the way to the audit's "median near 50": half this corpus has no usage
evidence at all, and a median of 50 would claim we think half of it is proven. Spread stops at 30 points
(p90−p25) for the same reason — past that the map manufactures distinctions the evidence does not
support. **The remaining flatness is an evidence problem, not an arithmetic one** — it is §4 and §5 of
this document, and it is fixed by grading expertise and measuring more axes, not by tuning the curve.

Two side effects worth recording. `capability.js`'s verdict thresholds (80 / 62) were written for the
old 60–100 band and had gone nearly dead — under the old scale essentially every capability page read
"Weigh the evidence". They now fire as designed (8.3% "Worth a look", 0.7% "A safe default") and needed
no edit. And the `trust` → `tashan_score` column rename had left three scripts querying a column that no
longer exists — `gen_badges.py` (crashing the site build), `fetch_readmes.py` and `classify_prep.py`
(both silently broken, and both feed the expertise work §4 calls the highest-leverage thing here).

## 2. Monetization: zero infrastructure, and the free tier promises what does not exist

`/pricing.html` sells "$6/mo Pro" with alerts, unlimited compare, full history, full API, on-demand
expertise grading and export.

- **Payment: none.** The CTA is `mailto:hello@tashan.sh`. No Stripe, no auth, no accounts, no entitlement.
- **Every Pro feature is unbuilt.** The only serverless function in the repo is the analytics collector.
- **Worse, the FREE tier also promises unbuilt features** — "watch up to 3 capabilities · alerts on
  deprecation & drops", "compare 2 at a time", "API/CLI 60 requests/day". A visitor who tries any of
  these finds nothing. That is not a roadmap problem, it is a credibility problem on a site whose entire
  pitch is that it does not overstate.

Every one of those features needs the same thing: **a backend with accounts and persistence.** That is
the single blocking investment, and it is correctly identified in `PROJECT.md` as "the next unlock."

**The harder truth about $6/mo:** the firewall (nobody pays to change a score) is right and
non-negotiable, but it means consumer subscription is the *only* clean revenue, and $6/mo against
developer tooling churn is a hard business. Realistic alternatives that do not touch the firewall:
- **Data/API licensing to platforms** — the people who need scores at scale are IDEs, agent hosts and
  registries, not individual developers. One host integrating `/v0.1/scores` is worth more than a
  thousand $6 subscriptions and costs nothing extra to serve.
- **Procurement/compliance** — "is this MCP server safe to allow in our org" is a budgeted enterprise
  question. It needs the security eval that is currently unbuilt.
Both are B2B and neither requires selling a listing.

## 3. The moat is real but it is six days old

`signal_history` — the un-backfillable retention series, correctly called the compounding asset — holds
**6 distinct days** (2026-07-23 → 07-29, 25,930 rows). The DB is now tracked in git, which fixes the
"lives only on one machine" risk flagged earlier.

Six days is not yet a moat; it is a promise with a good start. Its value is strictly a function of
elapsed time, which means **the daily pipeline running uninterrupted is the highest-value low-effort
activity in the project** and a gap in it is permanently unrecoverable. `.github/workflows/daily.yml`
exists; it must actually be running.

## 4. Expertise: the stated wedge, effectively unstarted

**24 of 6,200 scored capabilities are expertise-graded (0.4%).**

Every competitive doc names this as the largest open position — 333k skills, none carrying a published
quality measurement — and it is the one signal that survives Anthropic shipping install telemetry
(which would outclass our adoption signal overnight for plugins). It is also the only thing here that a
competitor cannot replicate by adding a column: it requires judgment about the work.

The task-tagging effort just proved the mechanism works at scale — parallel graders took task coverage
from 6.7% to 33% in two rounds with measured inter-rater agreement of 0.787. **That exact machinery
should be pointed at expertise next.** It is the highest-leverage unbuilt thing in the project.

## 5. Adoption evidence is thinner than the board implies

Of 6,200 scored capabilities: **23% have real usage data** (npm weekly downloads). 63% rest on GitHub
stars — which this project's own thesis calls hype and discounts to 0.8×, correctly. The rest lean on
config/marketplace reach.

This is handled honestly in the arithmetic (coverage discount, evidence shown per row, only 6 rows have
no adoption signal at all and they score ~20). But the marketing claim "measured from real public
configs" is doing more work than the data supports for most of the board. The config corpus is the
genuinely unique asset and it is the smallest one.

## 6. What is genuinely strong

- **Correctness discipline is unusual.** Several scoring inversions were found and fixed with measured
  sweeps rather than opinion; rejected approaches are kept in-tree with their numbers so they are not
  retried. `tests/test_firewall.py` asserts the neutrality claim in code.
- **The task axis is a real differentiator**, grounded in O*NET with occupation citations no competitor
  can produce, and validated by independent graders rather than asserted.
- **Agent distribution is now real** — `/v0.1/servers`, `/v0.1/scores`, an installable SKILL.md. A host
  already speaking registry API gets scores by changing a base URL.
- **Zero-dependency static stack** means near-zero running cost and nothing to operate.

## 7. Risk register

| Risk | Severity | State |
|---|---|---|
| Score does not discriminate (§1) | **High** | **Fixed 2026-07-29** — absolute anchors + order-preserving calibration; p50 27→39, IQR 12→18 |
| No payment/auth/backend (§2) | **High** | Unbuilt; blocks all revenue |
| Free tier advertises unbuilt features | **High** | Live on the site now |
| Anthropic ships install telemetry | Medium | Mitigated only by retention + expertise |
| Expertise unstarted (§4) | Medium | Mechanism proven, not pointed at it |
| Daily pipeline gap loses history permanently | Medium | Workflow exists; verify it runs |
| Not deployed — zero users, zero demand evidence | **High** | Blocked on `wrangler login` |

## 8. What I would do, in order

1. **Deploy.** Nothing here has ever met a user. Every judgement above is theory until it ships.
2. ~~**Fix the score distribution**~~ — done 2026-07-29, before deploy, as required.
3. **Cut the pricing page back to what exists.** Say "in development" honestly or remove the tier. A
   neutrality product cannot afford to overstate its own features.
4. **Point the grader fleet at expertise.** It is the defensible signal and the machinery is proven.
5. **Then** decide monetization, with usage data in hand rather than a guessed $6.
