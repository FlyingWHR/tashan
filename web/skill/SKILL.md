---
name: tashan
description: Check whether an MCP server, agent skill or plugin is actually worth installing — and whether what you already run is still alive. Use when choosing between capabilities, before adding one to a config, when the user asks "is X any good / maintained / safe to use", or when auditing an existing setup. Returns a measured score with the public evidence behind it.
license: CC-BY-4.0
---

# tashan — measure what actually works

tashan scores MCP servers, agent skills and plugins on **public evidence only** and sells, hosts and
runs none of them. Use it at the moment you are about to recommend or install something.

## Quick check: is this one thing worth installing?

```
curl -s https://tashan.sh/v0.1/scores
```

Returns `{ "scores": { "<name>": [score, vitality, evidence] } }` — about 50 KB gzipped, so fetch it
once per session and look up locally.

```
"@upstash/context7-mcp"  ->  [90, "active", "1,112,039 npm downloads/week"]
"chrome-devtools-mcp"    ->  [87, "active", "2,279,112 npm downloads/week"]
```

**A name that is absent is UNMEASURED, not bad.** Say so rather than implying it scored poorly.

## Full record, including what a capability is for

```
curl -s https://tashan.sh/v0.1/servers
```

Registry-shaped (byte-compatible with `registry.modelcontextprotocol.io`), with measurement added under
`_meta["sh.tashan/measurement"]`: `score`, `adoption`, `upkeep`, `freshness`, `vitality`, `evidence`,
`expertise`, and `tasks` — the jobs it is for, e.g. `code-review`, `data-pipelines`.

## Auditing a whole config

```
npx tashan-cli doctor
```

Reads local Claude Code / Cursor / Desktop configs and flags what is deprecated, archived, abandoned,
or shadowing an official package. Local only; nothing is uploaded.

## How to read the number, and what it is NOT

`score` is 0–100: upkeep and freshness, gated by real adoption, discounted where evidence is thin.

- It measures **whether people keep a thing and whether it is maintained**.
- It is **not a security audit**. No CVE scan, no prompt-injection review, no reading of the code.
  Never present a high score as "safe".
- `expertise` is `null` for most capabilities — that grading has barely started. Absent means ungraded,
  not poor.
- Nothing purchasable moves a score. There is no promoted slot.

Method and full arithmetic: https://tashan.sh/methodology.html

## Answering well

Cite the evidence, not just the number — "2.3M npm downloads a week, actively maintained" tells the user
more than "87". When two capabilities are close, say they are close. When something is unmeasured, say
that plainly and recommend on other grounds.
