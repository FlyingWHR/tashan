# Supertool

> Batch multiple file operations (read, grep, glob, ls, tail, head) into a single Bash round-trip. Instead of N separate Read/Grep/Glob tool calls — each re-paying the cached context prefix — one ./supertool call handles them all. Includes auto-promote (concrete glob becomes read, single-file grep includes full file), enforcement mode that blocks redundant built-in tools, and per-call logging with caller tracking. Python 3.6+, stdlib-only, 80 tests.

## Facts
- Page: https://tashan.sh/capability/plugin-digital-process-tools-claude-supertool-supertool
- tashan id: plugin:digital-process-tools/claude-supertool/supertool
- Source: https://github.com/Digital-Process-Tools/claude-supertool
- Type: plugin
- Category: security
- tashan score: 58.0 / 100
- Adoption: 22.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 14
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install supertool@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
