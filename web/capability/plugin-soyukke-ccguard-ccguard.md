# Ccguard

> Security guard hook for Claude Code. Evaluates every tool call (Bash, Edit, Write, Read, MCP) against 864 pattern-matching rules to block dangerous commands, data exfiltration, and supply chain attacks. Zero external dependencies, written in Zig. Supports three decision levels: allow, deny (hard block), and ask (user confirmation prompt). Protects against reverse shells, pipe-to-interpreter execution, credential leakage, cloud metadata access, environment variable injection, and more.

## Facts
- Page: https://tashan.sh/capability/plugin-soyukke-ccguard-ccguard
- tashan id: plugin:soyukke/ccguard/ccguard
- Source: https://github.com/soyukke/ccguard
- Type: plugin
- Category: security
- tashan score: 33.0 / 100
- Adoption: 7.0
- Upkeep: 59.0
- Freshness: 88.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install ccguard@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
