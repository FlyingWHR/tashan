# Cost Guard

> Real-time USD cost enforcement for Claude Code. Halts runaway agentic loops mid-step before they burn through your budget. The plugin enforces real-time USD cost limits in Claude Code. It uses hooks to read the session's the moment any cap is crossed — between tool batches, between turns, or at prompt-submit time. The result: a single greedy turn cannot spiral into a $30+ spend, sessions cannot silently accumulate cost over hours, and runaway burn rates are stopped before they hurt. Five confi

## Facts
- Page: https://tashan.sh/capability/plugin-oggeh-dev-claude-cost-guard-cost-guard
- tashan id: plugin:oggeh-dev/claude-cost-guard/cost-guard
- Source: https://github.com/oggeh-dev/claude-cost-guard
- Type: plugin
- Category: security
- tashan score: 29.0 / 100
- Adoption: 11.0
- Upkeep: 50.0
- Freshness: 70.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install cost-guard@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
