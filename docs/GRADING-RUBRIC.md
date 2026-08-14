# The expertise rubric, calibrated

Bands alone are not enough. Six graders applied them to 836 READMEs and returned "deep" anywhere from
**1.5% to 22.9%** of the time — same rubric, same corpus, wildly different scales. A grade that
depends on which batch a capability landed in is not a measurement, and this one gets sold.

*(That experiment ran against five bands. `wrapper` and `slop` have since been removed — see below —
so the scale is now the three in the table. The variance it measured was on `deep`, which is
unchanged, so the finding stands.)*

The fix is not a quota. Forcing a distribution would invent grades just as surely as inflating them.
The fix is **conjunctive criteria**: state what a band *requires*, so the judgement is "does this
have X, Y and Z" rather than "does this feel deep". Vibes vary between graders; checklists do not.

## The bands

| verdict | score | requires |
|---|---|---|
| **deep** | 80-100 | **ALL FOUR**: per-tool or per-feature documentation · at least two worked examples with real arguments or output · setup and auth covered · at least one stated limitation, caveat or "does not do X". Missing any one → `solid` at most. |
| **solid** | 60-79 | Clear prose, at least one worked example, honest about scope. A real product with real docs that simply does not reach all four `deep` criteria. |
| **thin** | 35-59 | Reference-only, or install instructions with no worked example, or a wall of badges and client-config blocks where tool docs should be. It may work perfectly; it is under-documented. |

**`wrapper` and `slop` were removed from this table.** They were answering different questions while
sharing an ordinal scale with this one. `wrapper` describes what the artifact *is* — putting it below
`thin` asserted that a well-documented shim is worse-*documented* than a badly-documented original,
which is a value judgment dressed as a measurement. It is now a separate fact, `shim`, recorded with
the author's own sentence as its evidence; set it only when they say so, never from your reading of
the architecture. `slop` claimed "AI-generated filler", which reading a README cannot establish, and
both rows that carried it turned out to be ordinary findings — one announced shutdown, one badge
count disagreeing with a heading. State those as facts in the note and grade the documentation on its
own terms.

## Rules that override the bands

These exist because they are the cases where graders disagreed most.

1. **If the README never names this capability, DO NOT GRADE IT — return no verdict.** 79 of 836 staged capabilities
   ship a README byte-identical to another's, and 23 are never mentioned in the only document they
   have — eleven `nigeria-*` servers on one family README, seven more on an org README. A grader
   reading that text sees competent documentation *about something else*. This used to cap at `thin`,
   so a grade could not borrow **credit** from another project's document — but `thin` is a criticism,
   not a neutral floor, so it borrowed **blame** instead. 87 published negative verdicts turned out to
   rest on exactly this, Anthropic's own filesystem server among them. The export now states the fact
   — "shares its documentation with 3 other capabilities" — and no verdict is published at all.

2. **Length is not depth.** A 12,000-character README with no worked example is `thin`. A 900-character
   one that documents three tools with real arguments and states a limitation is `solid`.

3. **A stated limitation raises confidence; marketing lowers it.** "This does not handle X" is
   evidence of real use. Superlatives, emoji headers and benchmark claims with no method are not.

4. **Internal contradictions cap at `thin`.** Several READMEs claim different tool counts in the same
   file (41 vs 34, 22 vs 43, 18 vs 26). Whatever else is true, the document is not maintained.

5. **`deep` should be uncommon and you should be able to say which four criteria it met.** If you
   cannot name all four, it is `solid`.

## Sanity check, not a target

Expect roughly: `solid` 40-55%, `thin` 25-45%, `deep` the remainder.
If your batch lands far outside that, re-read your `deep` and `solid` calls against rule 5 — but
**do not adjust grades to hit these numbers.** A batch of genuinely good packages should come out
good. The range is a prompt to re-check reasoning, never a quota to fill.

**A correction to my own guide.** The first calibrated run carried "`deep` under 10%". Six graders
came in between 14.3% and 24.3%, every one of them re-checked against rule 5, demoted borderline
calls, and declined to grade toward the number — which is exactly the instructed behaviour. They were
right and the guide was wrong: the staged corpus is ordered by tashan score, so it is the **top ~14%
of the field**, where vendor-maintained documentation is common. Under 10% is the expectation for the
whole corpus, not for its best slice. Re-derive this figure when the tail is graded rather than
carrying it forward.

One grader proposed a mechanical tightening worth keeping on file: require criterion (b) to show
**actual output**, not merely "real arguments or output". That would move roughly a third of current
`deep` calls to `solid` and is objective enough to stay comparable between graders.

## Measured cross-grader agreement

The point of the calibration is comparability, so here is what it actually bought, per grader,
on 836 READMEs split six ways:

| grader | n | deep | solid | thin |
|---|---|---|---|---|
| batches 00-06 | 140 | 14.3% | 44.3% | 41.4% |
| batches 07-13 | 140 | 20.7% | 56.4% | 20.7% |
| batches 14-20 | 140 | 17.9% | 57.1% | 19.3% |
| batches 21-27 | 140 | 24.3% | 53.6% | 19.3% |
| batches 28-34 | 140 | 22.1% | 35.7% | 35.7% |
| batches 35-41 | 136 | 19.9% | 54.4% | 24.3% |

**Spread on `deep`: 10.0pp, down from 21.4pp uncalibrated.** Halved, not eliminated. Two graders
independently reported tightening a criterion mid-run — requiring arguments or constraints in
per-tool docs, and requiring worked examples to be *invocations* rather than install blocks — which
is where most of the remaining 10 points live. Fold those into the criteria above before the next
pass and the spread should close further.

## Input caveat: read the whole document, and the ones it points at

The first pass graded READMEs truncated at 4,000 characters, and every one of the six graders
independently reported that it was under-scoring long documents — the tool reference, troubleshooting
and safety sections that separate `solid` from `deep` mostly live past 4 KB. `fetch_readmes.py`
now stores 14,000. Grades produced under the old cap are kept in
`data/readmes/pass1_uncalibrated/` as evidence, and are not merged.

**14,000 was not enough either.** Grading the top 100 by demand on 8 Aug 2026, **36 of the 57
candidates hit the cap exactly** — the manifest held a prefix, not a document. The bias runs one
way: a long, thorough README gets judged on its opening, and the sections that earn the top band are
the ones that get cut. `grade_evidence.py --follow` re-reads the file in full from the repo before
grading, and the effect is not marginal — firecrawl-mcp went from 0 documented tools to 28, appium
from 0 to 30, figma-console from 0 to 70.

**Documentation one click away is still its documentation.** chrome-devtools-mcp documents no tools
in its README because they live in `docs/tool-reference.md`; read that and it is a clean `deep` with
47 tools. Splitting a large reference out of the README is better practice, not worse. `--follow`
fetches the in-repo `.md` files a README hands off to. Where the hand-off is to an external docs
site we cannot read, criterion (a) is **unverified, not unmet** — that forecloses `deep`, which
requires all four confirmed, and lowers nothing.

## The evidence extractor

`pipeline/grade_evidence.py` pulls the four criteria out of a document mechanically and prints the
line that produced each one. It **does not assign a grade** — a tool that returned a verdict would
just be a seventh grader with the same variance and less accountability. It exists so the remaining
judgement is over a fixed set of facts rather than an impression.

Everything it refuses to do is there because it did the opposite first and was caught:

| It will not | Because |
|---|---|
| Score an absent document | `xmcp` staged 23 bytes reading `packages/xmcp/README.md` — the fetcher captured a pointer. Graded mechanically that is a confident `thin`, which publishes our own fetch bug on someone else's product page. Under 400 bytes is **ungradeable**. |
| Grade a document about something else | `@azure/mcp`'s README is titled *"Microsoft MCP Servers"*, a catalogue of twenty siblings. It passes `build.py`'s borrowed-doc gate — it names itself, its bytes are unique — and grading it rates Microsoft's index page. The extractor reports the H1 so a grader can see the subject drift. |
| Treat a missing check as a failed one | Tool docs behind a link we did not open are `UNKNOWN`. An unread page is not evidence for a grade **or** against one. |
| Cap a band on a rule that keeps misfiring | Rule 4 (contradictory tool counts) capped at `thin` until it was run on the queue, where **both** of its two hits were false — hostinger lists each sub-server's inventory, figma-console tabulates 9/101/114 across three modes. It now flags for the grader and decides nothing. |

Two matchers needed real tuning, and both failures are instructive. Criterion (d) first missed
Notion's *"We may sunset this local MCP server repository… not actively monitored"* by hunting for
the literal word "limitation"; widening it to bare `doesn't`/`can't`/`beta` then broke it far worse,
because in 60 KB of prose something always says "doesn't" — (d) became free and `deep` jumped to 23
of 57 on document length alone. A limitation must now be **asserted** ("does not support X", a
`## Limitations` section), not an incidental negation. Criterion (a) had the mirror problem: loosened
to accept prose-y headings, it accepted anything lowercase and reported *"42 tools documented (ci.yml,
publish.yml, security.yml…)"*. A tool name is an identifier; a filename is a file.

---

## Skills are NOT graded by this rubric, and the reason is measured

14,309 skills carry their own `SKILL.md` in `capability_text.doc_body` — already ingested, no
network fetch needed — and every one of them is ungraded. That looks like an obvious backlog: pure
compute, the purest possible application of a documentation rubric, and it would lift ~2,775 thin
skill pages out of `noindex`.

It was measured before it was done. Applying the four criteria above to 150 randomly sampled skills
with a real `SKILL.md` (600–40,000 chars):

| criterion | skills |
|---|---:|
| (a) per-tool docs | **10.7%** |
| (b) two worked examples | 53.3% |
| (c) setup / auth | 56.0% |
| (d) a stated limitation | 41.3% |
| **all four → `deep`** | **2.7%** |

Recently graded server batches land `deep` at roughly 16–20%. Skills would land at 2.7% — a six-fold
gap produced almost entirely by criterion (a), because **a skill has no tools**. It is a folder of
instructions for a model, not a server exposing an interface. Criterion (a) is not measuring that
skills are badly documented; it is measuring that the question does not apply.

Grading them anyway would put the same three words — `deep`, `solid`, `thin` — on two populations
where they mean different things, and a reader comparing a skill's `thin` to a server's `thin` would
be misled by our own label. That is the failure this rubric exists to prevent.

**What a skill rubric would need.** (b), (c) and (d) transfer as-is, at rates comparable to servers.
The replacement for (a) is the thing a `SKILL.md` uniquely has to get right: **does it say when it
should activate, and when it should not?** That is a skill's equivalent of per-tool documentation —
the contract between the author and the model loading it — and it is checkable in the same
conjunctive way. It also has to be a separate verdict vocabulary, or a separate field, so no surface
can compare the two scales.

Not built. Written down so the backlog is a decision waiting on a rubric, rather than a chore
somebody completes with the wrong instrument.
