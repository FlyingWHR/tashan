# Casemgr Channel

> Pushes AI work items from CaseMgr — a shared workspace for you and your AI agent — into your running Claude Code session as channel events. When a CMMN workflow in CaseMgr produces a pending work item, the plugin forwards it via SSE so Claude can claim, execute, and complete it without any human prompt. Uses Bearer-token auth, real-time event delivery with polling fallback, and a /casemgr-channel:configure skill for setup. Claude handles the actual work via the existing casemgr MCP tools (cases,

## Facts
- Page: https://tashan.sh/capability/plugin-mstang-casemgr-channel-casemgr-channel
- tashan id: plugin:mstang/casemgr-channel/casemgr-channel
- Source: https://github.com/mstang/casemgr-channel
- Type: plugin
- Category: productivity
- tashan score: 27.0 / 100
- Adoption: 7.0
- Upkeep: 50.0
- Freshness: 70.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install casemgr-channel@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
