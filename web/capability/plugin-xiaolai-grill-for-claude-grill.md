# Grill

> Grill runs six specialized agents (recon, architecture, error handling, security, testing, edge cases) in parallel against a codebase, then synthesizes their findings into one report with severity tags, file:line evidence, proposed changes, effort estimates, and explicit tradeoffs. Five review styles let you tune intensity from quick scan to Paranoid Mode. Eight optional add-on pressure tests target specific failure modes (concurrency, observability, dependency hygiene, etc.). Zero-findings is r

## Facts
- Page: https://tashan.sh/capability/plugin-xiaolai-grill-for-claude-grill
- tashan id: plugin:xiaolai/grill-for-claude/grill
- Source: https://github.com/xiaolai/grill-for-claude
- Type: plugin
- Category: devtools
- tashan score: 36.0 / 100
- Adoption: 17.0
- Upkeep: 54.0
- Freshness: 78.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 5
- License: ISC
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install grill@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
