# Preserve Session

> Preserves Claude Code session history across project directory renames, moves, and copies by assigning each project a path-independent UUID and maintaining a global registry mapping UUID to current path. Addresses a long-standing pain point: --resume and --continue silently lose session history when paths change. Closes anthropics/claude-code5768; also tracked in 38089, 28745, 26766, 27883. Commands: /preserve-session:fix recovers sessions after rename/move (with copy detection and automa

## Facts
- Page: https://tashan.sh/capability/plugin-wonbywondev-claude-plugins-preserve-session
- tashan id: plugin:wonbywondev/claude-plugins/preserve-session
- Source: https://github.com/wonbywondev/claude-plugins
- Type: plugin
- Category: productivity
- tashan score: 48.0 / 100
- Adoption: 11.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install preserve-session@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
