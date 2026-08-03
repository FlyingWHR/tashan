# Trail

> Trail wraps any command (trail run -- <cmd) or Docker container and captures its stdout/stderr into per-session JSONL files on local disk. The bundled MCP server exposes listsessions and getlogs so Claude Code can filter by level, regex, time window, or line range — server-side, without burning context window. Includes a debug-with-trail skill that walks Claude through a 4-phase debug flow: read existing logs first, add marked instrumentation only when needed, and a mandatory cleanup step ve

## Facts
- Page: https://tashan.sh/capability/plugin-pratham-mishra04-trail-trail
- tashan id: plugin:pratham-mishra04/trail/trail
- Source: https://github.com/Pratham-Mishra04/trail
- Type: plugin
- Category: productivity
- tashan score: 39.0 / 100
- Adoption: 19.0
- Upkeep: 56.0
- Freshness: 82.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 8
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install trail@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
