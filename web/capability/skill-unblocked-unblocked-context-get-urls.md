# Unblocked Context Get Urls

> Direct URL content resolution via contextgeturls. Use this to fetch full content from one or more URLs the agent already has in hand — PRs, issues, docs, Slack messages, or arbitrary web pages that were surfaced by a prior search or provided by the user. TRIGGER when: you already have concrete URLs from a previous contextresearch / contextsearch result and want the full body, not just the title and URL; the user pasted one or more links and wants them summarized or analyzed; you need to resolve a Jira/Linear/PR/Slack link directly. DO NOT TRIGGER when: you need to search for content (use contextresearch or the contextsearch family); the URL is local (localhost, file://, private network) — those aren't reachable.

## Facts
- Page: https://tashan.sh/capability/skill-unblocked-unblocked-context-get-urls
- tashan id: skill:unblocked/unblocked-context-get-urls
- Source: https://github.com/unblocked/skills
- Type: skill
- Category: search
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 98.0
- Freshness: 95.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r unblocked-context-get-urls ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
