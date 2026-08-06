# Codixing

> Code retrieval engine that gives Claude structural understanding of your codebase. Before modifying code, Codixing tells Claude what will break, predicting impact across the dependency graph, finding affected tests, and tracing callers through the call hierarchy. Unlike text search, Codixing builds an AST-aware index with BM25 + semantic hybrid retrieval, dependency graphs with PageRank ranking, and trigram-accelerated grep; all running locally with zero cloud dependencies.

## Facts
- Page: https://tashan.sh/capability/plugin-ferax564-codixing-codixing
- tashan id: plugin:ferax564/codixing/codixing
- Source: https://github.com/ferax564/codixing
- Type: plugin
- Category: docs
- tashan score: 49.0 / 100
- Adoption: 13.0
- Upkeep: 98.0
- Freshness: 95.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install codixing@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
