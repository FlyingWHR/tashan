# Labeling rules for the task axis

Every hub page, the browse rail, and the claim that tashan files capabilities by *the work you're doing*
rest on these labels. A wrong tag is worse than a missing one: a missing tag means a capability is hard to
find, a wrong tag means the page lies about what it contains.

These rules exist because the first 108 hand labels were **audited and found inconsistent**. The rules are
written down so the same input gets the same answer on a different day, by a different grader.

---

## The question

For each capability, ask only: **what is the person doing when they reach for this?**

Not what it is built on, not what it touches, not which vendor made it. `mongodb` is
`database-access` — the job is querying, MongoDB is the technology.

## Rules

**R1 — At most 4 tags, and fewer is better.** A capability tagged with everything says nothing. If a
fifth genuinely applies, the capability is probably a bundle (see R4).

**R2 — Tag the primary job, not the incidental one.** A tag belongs only if someone would go looking for
this capability *while doing that job*. `chrome-devtools-mcp` records performance traces, so
`optimize-performance` is real. A Swift skill that mentions "deployment" once in passing is not
`deploy-a-release`.

**R3 — Empty is a valid and expected answer, but only for a real reason.** Roughly 10% of capabilities
serve no single job. Legitimate empties:
  - *version-note blurbs* — the description is a changelog ("v9.45.0 — add provider…"), not a purpose.
  - *test artifacts and scaffolding* — "verify a hook fires".
  - *marketplace boilerplate* — the description belongs to the repo, not the capability.

**Never** use empty because the taxonomy lacks a fit. That is a taxonomy bug: add the task instead. This
was found in audit — `kicad-happy` (PCB design), `cad` (CAD/robotics), `nvidia-skills` (vehicle routing)
and `liftlog-plan-builder` (training plans) were all recorded as "serves no job" when the truth was that
`hardware-design`, `cad-modeling`, `logistics-and-fulfilment` and `career-development` did not exist yet.

**R4 — The bundle rule.** Collections of many skills are the single biggest source of inconsistency, so
the test is explicit:

> Tag a bundle **only if its skills serve one coherent job family**, and then tag that job.
> If it spans unrelated jobs, return empty.

  - `pm-skills` — "27 product management skills, full product lifecycle" → **tag it.** One job family.
  - `dotnet-skills` — "27 skills covering Akka.NET, Aspire, testing, C#" → **tag it.** One job family.
  - `pm-claude-skills` — "90 skills across 14 professions" → **empty.** Spans everything.
  - `fullstack-dev-skills` — "66 skills: 12 languages, 10 backend frameworks, 6 frontend, infra, DevOps,
    security, testing" → **empty.** Spans everything.

The line is *coherence*, not count. A 90-skill bundle about one job gets tagged; a 6-skill bundle about
six jobs does not.

**R5 — Distribution is not creation.** Publishing, storing or transporting an artifact is a different job
from making it. Found in audit: `save-to-spotify` ("save spoken audio to Spotify, manage episodes and
shows") was tagged `audio-production`. It generates nothing.

**R6 — Infrastructure for agents is its own job.** Statuslines, config linters, safety guards, token
optimisers and permission tooling are real work for the people who live in a coding agent — that is
`agent-configuration`, not empty and not `process-automation`.

**R7 — When two tasks both fit, pick the more specific one.** `build-an-ecommerce-store` beats
`build-a-web-frontend` for a Shopify tool. Add the general one too only if the capability genuinely
serves both.

---

## Keeping this file honest

**This document is versioned with the taxonomy and drifted once already.** It was written against the
hand-built v1 slugs and not updated when the axis was rederived from O*NET, so it cited
`query-a-database`, `optimize-performance` and `optimize-operations` — none of which existed any more.
Six independent graders read it as gospel and each had to invent a workaround. If you change
`data/onet/mapping.json`, grep this file for the slugs you renamed before you ship.

## Validation, and its current limit

`--eval` reports **precision / recall / F1** against `data/tags/truth.json`, not accuracy — a capability
legitimately does several jobs, so "exactly right" is the wrong bar.

**The honest caveat: the truth set and the production labels currently share one author, so `--eval`
measures self-consistency, not correctness.** A single grader agreeing with themselves proves the rubric
is memorable, not that it is right. Breaking that circularity needed a second, independent grader over the same rows. Six of them have now
run against this rubric, and the agreement is itself the finding: they converged on the SAME seven gaps
(`database-access`, `recruiting-and-hiring`, `audio-production`, `document-production`,
`messaging-and-email`, `logistics-and-fulfilment`, `career-development`), all of which have since been
added. Independent convergence on a defect is stronger evidence than any single grader's confidence —
that is what this loop is for, and it is why R3 forbids using an empty label to paper over a missing task.
