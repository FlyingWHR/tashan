# Writ

> Hybrid RAG rule retrieval and workflow enforcement for Claude Code. A five-stage pipeline (BM25 + vector + graph traversal + two-pass ranking) retrieves the right coding rules for each task in under 1ms from a Neo4j knowledge graph,. 726x context reduction vs loading a full rulebook at 10K rules. A mode and gate state machine enforces workflow discipline at the tool-call boundary: - writes are blocked until plans and tests are approved. - Ships with 276 rules across 12 domains (Security, Clean

## Facts
- Page: https://tashan.sh/capability/plugin-infinri-writ-writ
- tashan id: plugin:infinri/writ/writ
- Source: https://github.com/infinri/Writ
- Type: plugin
- Category: productivity
- tashan score: 57.0 / 100
- Adoption: 36.0
- Upkeep: 63.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: deep
- GitHub stars: 163
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install writ@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
