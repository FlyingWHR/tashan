# Patristic

> Search and cite the Russian Orthodox patristic corpus (azbyka.ru) from any MCP-capable agent. Indexes ~2,100 works by 86 Church Fathers and ascetic writers (726K paragraphs, 1.98M bge-m3 embedding windows) in a Postgres + pgvector backend. Ships: - HTTP MCP server with 6 tools: readpassage, lexicalsearch, semanticsearch, listauthors, listworks, expandconcept (Church-Slavonic / archaic synonym expansion). - "teo-search" subagent — restricted to search tools, returns candidate citations wit

## Facts
- Page: https://tashan.sh/capability/plugin-logospatrum-patristic-plugin-patristic
- tashan id: plugin:logospatrum/patristic-plugin/patristic
- Source: https://github.com/logospatrum/patristic-plugin
- Type: plugin
- Category: productivity
- tashan score: 29.0 / 100
- Adoption: 7.0
- Upkeep: 53.0
- Freshness: 75.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install patristic@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
