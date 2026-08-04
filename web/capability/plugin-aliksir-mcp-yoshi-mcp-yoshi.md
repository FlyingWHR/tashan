# Yoshi

> Real-time security filter for MCP tool communications. Works as a Claude Code hook to inspect all data sent to and received from MCP servers. Detects prompt injection, API key leakage, tool poisoning, ASCII smuggling, SSRF, Base64-encoded payloads, and Rug Pull attacks. Provides PASS/WARN/BLOCK decisions with per-server configuration, allowlisting, and logging. Zero dependencies, ~60ms latency.

## Facts
- Page: https://tashan.sh/capability/plugin-aliksir-mcp-yoshi-mcp-yoshi
- tashan id: plugin:aliksir/mcp-yoshi/mcp-yoshi
- Source: https://github.com/aliksir/mcp-yoshi
- Type: plugin
- Category: security
- tashan score: 35.0 / 100
- Adoption: 11.0
- Upkeep: 58.0
- Freshness: 86.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install mcp-yoshi@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
