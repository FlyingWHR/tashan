# Verify

> - Verify a forge-built plugin before shipping: smoke matrix, fresh pass^k trials, holdout tranche, trigger evals on default AND crowded targets, token budget check, and triage of sampled failures. Use after a forge build loop has gone green (.forge/state.json phase smoke or verify) and before /plugin-forge:ship.

## Facts
- Page: https://tashan.sh/capability/skill-aznatkoiny-verify
- tashan id: skill:Aznatkoiny/verify
- Source: https://github.com/Aznatkoiny/claude-dev-toolkit
- Type: skill
- Category: cloud
- tashan score: 47.0 / 100
- Adoption: 14.0
- Upkeep: 82.0
- Freshness: 100.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r verify ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
