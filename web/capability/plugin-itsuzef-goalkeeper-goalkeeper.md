# Goalkeeper

> Durable, contract-driven goal execution for long-running autonomous tasks. After every checkpoint a subagent judge, fresh context, anti-placeholder, reviews the diff and progress log against an explicit Definition of Done, returning approve or a structured fix-list; after 5 rejections it pauses for human help. Linear chains compose role-specific contracts with judge-gated handoff between links.

## Facts
- Page: https://tashan.sh/capability/plugin-itsuzef-goalkeeper-goalkeeper
- tashan id: plugin:itsuzef/goalkeeper/goalkeeper
- Source: https://github.com/itsuzef/goalkeeper
- Type: plugin
- Category: devtools
- tashan score: 41.0 / 100
- Adoption: 21.0
- Upkeep: 57.0
- Freshness: 85.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 12
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install goalkeeper@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
