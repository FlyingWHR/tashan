# The expertise rubric, calibrated

The five bands alone are not enough. Six graders applied them to 836 READMEs and returned "deep"
anywhere from **1.5% to 22.9%** of the time — same rubric, same corpus, wildly different scales. A
grade that depends on which batch a capability landed in is not a measurement, and this one gets
sold.

The fix is not a quota. Forcing a distribution would invent grades just as surely as inflating them.
The fix is **conjunctive criteria**: state what a band *requires*, so the judgement is "does this
have X, Y and Z" rather than "does this feel deep". Vibes vary between graders; checklists do not.

## The bands

| verdict | score | requires |
|---|---|---|
| **deep** | 80-100 | **ALL FOUR**: per-tool or per-feature documentation · at least two worked examples with real arguments or output · setup and auth covered · at least one stated limitation, caveat or "does not do X". Missing any one → `solid` at most. |
| **solid** | 60-79 | Clear prose, at least one worked example, honest about scope. A real product with real docs that simply does not reach all four `deep` criteria. |
| **thin** | 35-59 | Reference-only, or install instructions with no worked example, or a wall of badges and client-config blocks where tool docs should be. It may work perfectly; it is under-documented. |
| **wrapper** | 20-44 | The artifact is a shim: it self-describes as a bridge/proxy/glue over another service, and the value lives elsewhere. Documentation quality does not rescue this — a well-documented shim is still a shim. |
| **slop** | 0-25 | AI-generated filler, self-contradictory claims, or evidently non-functional (the service is announced as shut down, endpoints dead). |

## Rules that override the bands

These exist because they are the cases where graders disagreed most.

1. **If the README never names this capability, cap at `thin` (42).** 79 of 836 staged capabilities
   ship a README byte-identical to another's, and 23 are never mentioned in the only document they
   have — eleven `nigeria-*` servers on one family README, seven more on an org README. A grader
   reading that text sees competent documentation *about something else*. The capability is
   undocumented and must not borrow credit. Note it as "documented only by a shared repo README".

2. **Length is not depth.** A 12,000-character README with no worked example is `thin`. A 900-character
   one that documents three tools with real arguments and states a limitation is `solid`.

3. **A stated limitation raises confidence; marketing lowers it.** "This does not handle X" is
   evidence of real use. Superlatives, emoji headers and benchmark claims with no method are not.

4. **Internal contradictions cap at `thin`.** Several READMEs claim different tool counts in the same
   file (41 vs 34, 22 vs 43, 18 vs 26). Whatever else is true, the document is not maintained.

5. **`deep` should be uncommon and you should be able to say which four criteria it met.** If you
   cannot name all four, it is `solid`.

## Sanity check, not a target

Expect roughly: `solid` 40-55%, `thin` 25-45%, with `wrapper` and `slop` in the low single digits.
If your batch lands far outside that, re-read your `deep` and `solid` calls against rule 5 — but
**do not adjust grades to hit these numbers.** A batch of genuinely good packages should come out
good. The range is a prompt to re-check reasoning, never a quota to fill.

**A correction to my own guide.** The first calibrated run carried "`deep` under 10%". Six graders
came in between 14.3% and 22.1%, every one of them re-checked against rule 5, demoted borderline
calls, and declined to grade toward the number — which is exactly the instructed behaviour. They were
right and the guide was wrong: the staged corpus is ordered by tashan score, so it is the **top ~14%
of the field**, where vendor-maintained documentation is common. Under 10% is the expectation for the
whole corpus, not for its best slice. Re-derive this figure when the tail is graded rather than
carrying it forward.

One grader proposed a mechanical tightening worth keeping on file: require criterion (b) to show
**actual output**, not merely "real arguments or output". That would move roughly a third of current
`deep` calls to `solid` and is objective enough to stay comparable between graders.

## Input caveat, now fixed

The first pass graded READMEs truncated at 4,000 characters, and every one of the six graders
independently reported that it was under-scoring long documents — the tool reference, troubleshooting
and safety sections that separate `solid` from `deep` mostly live past 4 KB. `fetch_readmes.py`
now stores 14,000. Grades produced under the old cap are kept in
`data/readmes/pass1_uncalibrated/` as evidence, and are not merged.
