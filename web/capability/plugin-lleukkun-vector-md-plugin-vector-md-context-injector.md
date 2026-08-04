# Vector Md Context Injector

> Vector-md-plugin provides hooks to automatically inject sub-tree scoped context files upon reading a file from said sub-tree. The injections are deduplicated per agent context. The skill file and CLAUDE.md loading hook provide guidance towards maintaining these files as a natural part of the work Claude Code does. The idea is that these vector.md files form a knowledge graph that's automatically available to claude as needed.

## Facts
- Page: https://tashan.sh/capability/plugin-lleukkun-vector-md-plugin-vector-md-context-injector
- tashan id: plugin:lleukkun/vector-md-plugin/vector-md-context-injector
- Source: https://github.com/lleukkun/vector-md-plugin
- Type: plugin
- Category: security
- tashan score: 25.0 / 100
- Adoption: 7.0
- Upkeep: 47.0
- Freshness: 62.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install vector-md-context-injector@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
