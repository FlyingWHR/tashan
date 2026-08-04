# Gate And Ship

> Quality gates then ship — chains /prepare-delivery and /ship in one command. Runs the full pre-ship pipeline (deslop, simplify, agnix, enhance, multi-agent review, delivery validation, docs sync) and only proceeds to commit/push/PR/merge/deploy if every gate passes. If a gate fails, returns to the implementation phase with concrete fix instructions instead of shipping broken code. Designed for the "I'm done; ship it" workflow where you don't want to think about which gates to run — they all

## Facts
- Page: https://tashan.sh/capability/plugin-agent-sh-gate-and-ship-gate-and-ship
- tashan id: plugin:agent-sh/gate-and-ship/gate-and-ship
- Source: https://github.com/agent-sh/gate-and-ship
- Type: plugin
- Category: devtools
- tashan score: 28.0 / 100
- Adoption: 13.0
- Upkeep: 47.0
- Freshness: 62.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install gate-and-ship@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
