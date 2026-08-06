# Compose

> The mumei orchestrator. For new features, presents a vehicle picker — spec (full SDD workflow: clarification → requirements → design → tasks each auto-reviewed up to 3 iterations → single user approval → Wave-by-Wave implementation → 4-stage review) or plan (Claude Code plan-mode wrapper: hand off to plan mode, capture via hook, run /mumei:peruse at the end). Resumes existing features automatically by detecting which vehicle''s state.json exists. Triggers when the user invokes /mumei:compose <feature or naturally asks to "plan", "spec", "design", or "implement" a feature with mumei. Always renders body content (User Story prose, AC bodies after EARS keywords, Assumptions, Open Questions, design narratives, task descriptions, Wave goals/verifies) in the user''s conversation language; English section headings, EARS keywords, REQ trace IDs, and [CONFIRMED]/[ASSUMPTION] annotations remain literal.

## Facts
- Page: https://tashan.sh/capability/skill-hir4ta-compose
- tashan id: skill:hir4ta/compose
- Source: https://github.com/hir4ta/mumei
- Type: skill
- Category: devtools
- tashan score: 51.0 / 100
- Adoption: 14.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r compose ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
