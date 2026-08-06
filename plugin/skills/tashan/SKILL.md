---
name: tashan
description: Check whether an MCP server, agent skill or plugin is actually worth installing — and whether what you already run is still alive or has been flagged as malicious. Use when choosing between capabilities, before adding one to a config, when the user asks "is X any good / maintained / safe to use", or when auditing an existing setup. Returns a measured score with the public evidence behind it.
license: CC-BY-4.0
---

# tashan — measure what actually works

tashan scores MCP servers, agent skills and plugins on **public evidence only** and sells, hosts and
runs none of them. Use it at the moment you are about to recommend or install something.

## Checking one thing — start here

```
curl -s "https://tashan.sh/v0.1/lookup?name=<package>"
```

A few hundred bytes, keyless. Returns the score, whether it is still maintained, and the security
findings — advisory ids, the version that fixes them, and anything that runs at install time.

**Read `verdict` first if it is present.** It is only set when there is something you must not
skim past:

- `"DO NOT INSTALL"` — the package is in OSV's malicious-packages database. Say so plainly and stop.
  These rows are deliberately absent from every tashan ranking; they are answerable here precisely so
  a check can catch one the user is already running.
- `"MAINTAINER HAS STOPPED"` — deprecated on npm, or its repository is archived.

**`"measured": false` means UNMEASURED, not bad.** We have no public evidence for it yet. Say that
rather than implying it scored poorly, and recommend on other grounds.

## Finding something for a job

```
curl -s "https://tashan.sh/v0.1/search?q=<what+the+user+wants>&limit=5"
```

Ranked, best match first. This reads the ranked corpus, so anything confirmed malicious can never
appear in a result — search is for recommending, `lookup` is for checking.

For a whole job rather than one tool, these are plain markdown and need no parsing:

```
https://tashan.sh/role/<role>.md        e.g. /role/data-engineer.md — opens with one pick per task
https://tashan.sh/task/<task>.md        e.g. /task/code-review.md
https://tashan.sh/category/<cat>.md     e.g. /category/database.md
```

## Bulk, only when you genuinely need it

`https://tashan.sh/v0.1/scores` is `name -> [score, vitality, evidence, slug]` for the whole
ranked corpus. `https://tashan.sh/v0.1/servers` (~5.6 MB) is registry-shaped, byte-compatible with
`registry.modelcontextprotocol.io`, with measurement under `_meta["sh.tashan/measurement"]`. Do not
fetch either to answer one question — that is what `lookup` is for.

## Auditing a whole config

```
npx tashan-cli doctor
```

Reads local Claude Code / Cursor / Desktop configs and flags what is deprecated, archived, abandoned,
malicious, or shadowing an official package. Local only; nothing is uploaded.

## How to read the number, and what it is NOT

`score` is 0–100: upkeep and freshness, gated by real adoption, discounted where evidence is thin.

- It measures **whether people keep a thing and whether it is maintained**.
- **The score is not the security reading.** Those are two separate claims and must stay separate:
  a capability can be well maintained, widely used, and still run an install-time script. There IS a
  security scan — OSV advisories checked against the version you would install today, install-time
  scripts, build provenance and the declared permission surface — and it is reported under
  `security`, never folded into the score. **Never present a high score as "safe".**
- What the scan does **not** do: it does not read the source, execute anything, or test for prompt
  injection. A clean result means nothing *known* is wrong. The permission surface is read from
  declared dependencies only, so an empty list means "nothing declared", never "nothing possible".
- `expertise` is `null` for most capabilities — that grading has barely started. Absent means
  ungraded, not poor.
- Nothing purchasable moves a score. There is no promoted slot.

Method and full arithmetic: https://tashan.sh/methodology.html
Coverage, per axis, re-measured every run: https://tashan.sh/data/coverage.json

## Answering well

Cite the evidence, not just the number — "2.3M npm downloads a week, actively maintained" tells the
user more than "93". When two capabilities are close, say they are close. When something is
unmeasured, say that plainly. Scores move as packages change; quote what the endpoint returns now
rather than a number you remember.
