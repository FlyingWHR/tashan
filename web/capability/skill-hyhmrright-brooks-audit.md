# Brooks Audit

> Architecture audit that maps module dependencies, checks layering integrity, and flags structural decay across a codebase, drawing on twelve classic engineering books. Triggers when: user asks to audit architecture, review folder/module structure, check for circular imports, understand how the codebase is organized, or asks "does this follow clean architecture?" or "why does everything depend on everything?". Also triggers for onboarding requests: "explain this codebase to a new developer" or "give me a codebase tour" (use onboarding mode). Do NOT trigger for: PR-level code review (use brooks-review) or line-level refactoring questions — this skill analyzes structural/module-level concerns, not individual functions.

## Facts
- Page: https://tashan.sh/capability/skill-hyhmrright-brooks-audit
- tashan id: skill:hyhmrright/brooks-audit
- Source: https://github.com/hyhmrright/brooks-lint
- Type: skill
- Category: devtools
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: not measured
- Freshness: not measured
- Evidence coverage: not measured
- Health: not measured
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r brooks-audit ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
