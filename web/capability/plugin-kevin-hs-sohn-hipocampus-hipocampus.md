# Hipocampus

> Persistent memory that survives across sessions. Hipocampus gives your agent a 3-tier memory system (hot/warm/cold) with a self-compressing 5-level compaction tree. Every session, the agent auto-loads a ~3K token topic index (ROOT.md) so it knows what it knows — then retrieves specific details on demand via tree traversal or hybrid search (BM25 + vector via qmd). All memory writes happen through subagents to keep your main session clean. Zero dependencies, zero infrastructure — just markdown fil

## Facts
- Page: https://tashan.sh/capability/plugin-kevin-hs-sohn-hipocampus-hipocampus
- tashan id: plugin:kevin-hs-sohn/hipocampus/hipocampus
- Source: https://github.com/kevin-hs-sohn/hipocampus
- Type: plugin
- Category: productivity
- tashan score: 49.0 / 100
- Adoption: 36.0
- Upkeep: 56.0
- Freshness: 81.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 160
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install hipocampus@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
