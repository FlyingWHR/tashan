# Quality Locked

> When --quality-locked is active, loop review/revise at each Quality Gate until findings reach a clean bar (no Critical, no Major, only cosmetic Minor) or the iteration cap (10) is reached. Uses a deterministic Python checker for classification and decision logic; agent runs the actual review and revision steps.

## Facts
- Page: https://tashan.sh/capability/skill-xoai-quality-locked
- tashan id: skill:xoai/quality-locked
- Source: https://github.com/xoai/sage
- Type: skill
- Category: security
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 79.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r quality-locked ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
