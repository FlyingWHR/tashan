# How AI was used in this project

Required disclosure for ETHOnline 2026, and worth writing carefully: this is a measurement product,
so the line between "a model helped build it" and "a model made the numbers up" is the whole
credibility of the thing. Both halves are below.

## 1. AI as the implementation tool

**Claude Code (Claude Opus) wrote most of the code in this repository, under human direction.** That
is not a disclaimer, it is checkable: every such commit carries a `Co-Authored-By` trailer naming the
model, so the proportion is a `git log` query rather than an estimate.

```sh
git log --format='%(trailers:key=Co-Authored-By,valueonly)' | grep -ci claude   # 321
git rev-list --count HEAD                                                      # 399
```

**321 of 399 commits** (80%), and **13 of the 13** commits inside the hackathon window. The
remaining 78 are early scaffolding, brand and copy work, and merges.

What stayed human: the product decisions, and every decision where being wrong is expensive. Some
are recorded in the commits themselves, which is where this repo keeps its reasoning —

- **What not to merge.** 2,030 identities exist as more than one kind (npm package, plugin, skill) and
  460 carry disagreeing scores (`47abe203`). Merging them changes which URL owns a capability and
  which score survives. The decision taken was to *measure and baseline* the divergence and leave the
  merge to a human, explicitly because "it should not be made against a deadline."
- **What the score may read.** Payment can never move a rank. That is not a policy sentence, it is
  `tests/test_firewall.py`, which asserts the scorer reads only public-signal columns.
- **What may be published.** Unknown inputs stay `null` and are rendered as "not measured", never as
  zero. Security findings are deliberately *not* inputs to the score, because "well maintained" and
  "nothing known is wrong" are different claims.
- **When to stop.** `pipeline/scorer.lock` freezes the scoring rules through 2026-11-01, and
  `tests/test_scorer_version.py` refuses a scoring change inside that window unless a human writes
  down a reason in `TASHAN_SCORER_BREAK_GLASS`.

## 2. Planning and spec artifacts (all in the repo)

Nothing here was planned in a chat window that reviewers cannot see:

| file | what it is |
|---|---|
| `PROJECT.md` | the thesis, positioning, moat and roadmap — the spec |
| `CLAUDE.md` | the operational map, and the invariants that were learned the hard way (each one is there because it broke) |
| `docs/` | 33 documents: architecture, competitive landscape, monetization, payments (`X402.md`), scale, audits, next steps |
| `docs/GRADING-RUBRIC.md` | the published rubric the expertise grader is held to |
| `docs/HACKATHON.md` | this entry's state, written to be picked up cold |
| `brand/BRAND.md` | the design system |
| commit messages | the reasoning for every change, including what was ruled out and what is still open |

## 3. AI inside the product — and the fence around it

Two of the published signals are graded by a model, and both are labelled as such on the site:

- **Expertise** (`pipeline/grade_expertise.py`, `pipeline/grade_evidence.py`,
  `pipeline/merge_expertise.py`) — how well a capability documents itself, graded against
  `docs/GRADING-RUBRIC.md` and published as `deep / solid / thin`. The rubric is conjunctive because
  the bands alone produced "deep" at anywhere from 1.5% to 22.9% across six graders on the same
  corpus: a model's judgement is only usable when the criteria are narrow enough to be reproducible.
  `pipeline/doc_signals.py` withholds a grade entirely when a capability's only document is about
  something else — 79 of 836 READMEs are byte-for-byte shared with another capability and 23 never
  name the thing they document. A grade must not borrow credit from someone else's document.
- **Categories** (`pipeline/classify_prep.py`, `pipeline/merge_categories.py`) into a 15-category
  taxonomy, with a naive-Bayes classifier (`pipeline/classify.py`, no LLM) covering the tail at a
  measured 62.9% held-out accuracy. `tests/test_classify.py` fails on a dead class, so the
  categoriser cannot quietly stop using one.

**Everything else is arithmetic on public evidence.** Adoption, maintenance, freshness, the Trust
score, advisories, install scripts, permission surface, provenance, retention — all derived from the
MCP registry, npm, GitHub, OSV.dev and on-chain USDC transfers. **No model is asked to produce a
number that is published as a measurement**, and no model output can change a rank.

## 4. What AI was not used for

- **The demo video** carries a human voice. The rules reject AI voiceover, and so does this file.
- **No fabricated evidence.** No generated reviews, no invented download counts, no filled-in gaps.
  An absence is published as an absence; that is what `/requests.html` and the coverage tiers are for.
