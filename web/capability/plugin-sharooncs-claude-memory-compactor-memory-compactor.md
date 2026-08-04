# Memory Compactor

> Automatically monitors MEMORY.md size and warns Claude to compact it when it exceeds a configurable line threshold. Installs a PostToolUse hook on Write/Edit to memory directories, preventing auto-memory index overflow (only first 200 lines are loaded).

## Facts
- Page: https://tashan.sh/capability/plugin-sharooncs-claude-memory-compactor-memory-compactor
- tashan id: plugin:sharooncs/claude-memory-compactor/memory-compactor
- Source: https://github.com/sharooncs/claude-memory-compactor
- Type: plugin
- Category: security
- tashan score: 24.0 / 100
- Adoption: 7.0
- Upkeep: 46.0
- Freshness: 61.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install memory-compactor@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
