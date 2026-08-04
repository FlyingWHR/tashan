# Karellen Rr

> Claude Code plugin for rr reverse debugging via MCP. Automatically configures the karellen-rr-mcp MCP server and includes a crash detection hook that suggests rr when a command exits with a signal (SIGSEGV, SIGABRT, etc.) or sanitizer output is detected, a debugging skill with the full record-replay-analyze workflow, and an rr-investigator agent for autonomous crash investigation through reverse execution. Requires Linux x86-64 with rr, gdb, and pip install karellen-rr-mcp.

## Facts
- Page: https://tashan.sh/capability/plugin-karellen-karellen-rr-mcp-karellen-rr-mcp
- tashan id: plugin:karellen/karellen-rr-mcp/karellen-rr-mcp
- Source: https://github.com/karellen/karellen-rr-mcp
- Type: plugin
- Category: security
- tashan score: 36.0 / 100
- Adoption: 15.0
- Upkeep: 68.0
- Freshness: 69.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install karellen-rr-mcp@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
