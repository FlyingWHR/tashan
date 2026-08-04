# Loki

> MCP server for querying Grafana Loki logs. Enables LLMs to execute LogQL queries, discover labels and their values, explore log series by selectors, and retrieve index statistics — all via the Model Context Protocol. Supports basic auth, bearer token, and multi-tenant (X-Scope-OrgID) authentication.

## Facts
- Page: https://tashan.sh/capability/plugin-lexfrei-mcp-loki-loki
- tashan id: plugin:lexfrei/mcp-loki/loki
- Source: https://github.com/lexfrei/mcp-loki
- Type: plugin
- Category: comms
- tashan score: 47.0 / 100
- Adoption: 15.0
- Upkeep: 81.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- License: BSD-3-Clause
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install loki@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
