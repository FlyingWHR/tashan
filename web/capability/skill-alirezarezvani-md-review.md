# Md Review

> Converts a markdown PR writeup or code review (one with diff fenced blocks and severity-tagged [!BLOCKER]/[!MAJOR]/[!MINOR]/[!NIT] callouts) into a single-file 2-column HTML review — unified-diff on the left, severity-tagged annotation cards on the right, top jump-nav listing every finding, mandatory named reviewer footer. Triggers when the markdown-html-orchestrator classifies an input as REVIEW, or when invoked directly via /cs:md-review. Refuses without explicit --reviewer (a code review must name a human), refuses if no diff hunks present (route to md-document instead), and refuses to encode severity in color only (every badge ships color + icon + aria-label per WCAG 1.4.1). Use after orchestrator routing.

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-md-review
- tashan id: skill:alirezarezvani/md-review
- Source: https://github.com/alirezarezvani/claude-skills
- Type: skill
- Category: devtools
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 97.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r md-review ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
