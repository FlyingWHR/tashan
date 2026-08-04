# Nah

> nah is a local safety guard for Claude Code. It runs before tool use and classifies actions by what they actually do, so safe operations can proceed, ambiguous operations ask for confirmation, and clearly dangerous operations are blocked. It protects Bash commands, file reads and writes, edits, searches, notebook edits, and MCP tools using deterministic local rules with no package install or network call required by default.

## Facts
- Page: https://tashan.sh/capability/plugin-manuelschipper-nah-nah
- tashan id: plugin:manuelschipper/nah/nah
- Source: https://github.com/manuelschipper/nah
- Type: plugin
- Category: security
- tashan score: 71.0 / 100
- Adoption: 42.0
- Upkeep: 98.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: deep
- GitHub stars: 457
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install nah@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
