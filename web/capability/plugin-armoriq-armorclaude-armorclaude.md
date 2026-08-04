# Armorclaude

> Intent-based security enforcement for Claude Code. ArmorClaude makes Claude declare what it intends to do before doing it, then checks every tool call against that plan. Adds policy rules, intent drift detection, cryptographic proofs, and audit logging to the ArmorIQ platform. Works in both Claude Code CLI and Claude Desktop. Install with one curl command, optionally connect to ArmorIQ for signed JWT tokens and dashboard visibility.

## Facts
- Page: https://tashan.sh/capability/plugin-armoriq-armorclaude-armorclaude
- tashan id: plugin:armoriq/armorclaude/armorclaude
- Source: https://github.com/armoriq/armorClaude
- Type: plugin
- Category: security
- tashan score: 67.0 / 100
- Adoption: 33.0
- Upkeep: 98.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 44
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install armorclaude@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
