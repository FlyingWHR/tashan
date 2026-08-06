# Distributed Architect

> A reasoning framework that helps Claude analyze distributed system code changes for correctness before writing code. It provides an always-on boundary detector that recognizes when changes cross component boundaries (state mutations, data serialization, failure handling, new interactions), then loads targeted reasoning checklists on demand. Three slash commands cover the full development lifecycle: /dist-check for coding-time two-pass analysis, /dist-design for architecture trade-off eval...

## Facts
- Page: https://tashan.sh/capability/plugin-langerrr-distributed-architect-distributed-architect
- tashan id: plugin:langerrr/distributed-architect/distributed-architect
- Source: https://github.com/Langerrr/distributed-architect
- Type: plugin
- Category: devtools
- tashan score: 25.0 / 100
- Adoption: 11.0
- Upkeep: 45.0
- Freshness: 58.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install distributed-architect@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
