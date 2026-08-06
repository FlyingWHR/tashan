# Unblocked Context Query Issues

> Structured, filtered issue retrieval via contextqueryissues. Use this instead of contextsearchissues when you need a precise filtered list — scoped by project and/or person — rather than semantic relevance matching. TRIGGER when: the user asks "what bugs are open in PROJECT", "what issues is Alice working on", "list in-progress tickets for the payments team", "issues I filed last month"; you need a definitive list rather than a ranked set of relevant items; you already know the project key or person's name and want to enumerate issues under that filter. DO NOT TRIGGER when: the question is conceptual ("is there an issue about X") or you don't have a project/person anchor — use context-search-issues for semantic matching instead.

## Facts
- Page: https://tashan.sh/capability/skill-unblocked-unblocked-context-query-issues
- tashan id: skill:unblocked/unblocked-context-query-issues
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
cp -r unblocked-context-query-issues ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
