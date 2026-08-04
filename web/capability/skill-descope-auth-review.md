# Auth Review

> Static security review for authentication and authorization vulnerabilities. Use when the user invokes /auth-review, asks to audit auth, find identity breaches, review access control, hunt for IDOR/BOLA, or check authorization. Framework- and vendor-agnostic. Enumerates every route/endpoint, builds an authorization matrix, applies a vulnerability catalog, and writes a triage report ready to turn into issues or PRs.

## Facts
- Page: https://tashan.sh/capability/skill-descope-auth-review
- tashan id: skill:descope/auth-review
- Source: https://github.com/descope/skills
- Type: skill
- Category: other
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
cp -r auth-review ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
