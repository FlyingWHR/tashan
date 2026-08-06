# Unblocked Context Query Prs

> Structured, filtered PR retrieval via contextqueryprs. Use this instead of contextsearchprs when you need a precise filtered list — scoped by project/repo and/or person — rather than semantic relevance matching. TRIGGER when: the user asks "what PRs did Alice open last week", "list merged PRs in payments-service this month", "PRs I'm waiting on review for", "what did the team ship yesterday"; you need a definitive list rather than a ranked set; you already know the repo name or person and want to enumerate PRs under that filter. DO NOT TRIGGER when: the question is conceptual ("why was this introduced", "what PR added feature X") — use context-search-prs for semantic matching instead.

## Facts
- Page: https://tashan.sh/capability/skill-unblocked-unblocked-context-query-prs
- tashan id: skill:unblocked/unblocked-context-query-prs
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
cp -r unblocked-context-query-prs ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
