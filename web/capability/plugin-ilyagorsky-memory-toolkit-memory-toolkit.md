# Memory Toolkit

> Session memory lifecycle for Claude Code. Structured handoffs between sessions, workstreams to switch context without losing it, background watcher (Haiku) that captures decisions and corrections in real time, docs pipeline that routes session findings into .claude/rules/, model recommendations per task, and PreCompact hook to survive context compaction. Works alongside CLAUDE.md and auto-memory — no daemon, no vector DB, no external dependencies. MIT licensed.

## Facts
- Page: https://tashan.sh/capability/plugin-ilyagorsky-memory-toolkit-memory-toolkit
- tashan id: plugin:ilyagorsky/memory-toolkit/memory-toolkit
- Source: https://github.com/IlyaGorsky/memory-toolkit
- Type: plugin
- Category: productivity
- tashan score: 35.0 / 100
- Adoption: 22.0
- Upkeep: 50.0
- Freshness: 68.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 13
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install memory-toolkit@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
