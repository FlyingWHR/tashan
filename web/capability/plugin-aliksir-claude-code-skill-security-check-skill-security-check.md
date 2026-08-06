# Skill Security Check

> Security audit plugin that scans Claude Code skills, hooks, and MCP configurations for threats. Detects 37 attack patterns including prompt injection, data exfiltration, supply chain attacks (ToxicSkills/ClawHavoc), credential theft, reverse shells, backdoor persistence, API endpoint hijacking, Unicode homoglyph attacks, and context window poisoning. Includes runtime hooks for Bash command validation and MCP response inspection.

## Facts
- Page: https://tashan.sh/capability/plugin-aliksir-claude-code-skill-security-check-skill-security-check
- tashan id: plugin:aliksir/claude-code-skill-security-check/skill-security-check
- Source: https://github.com/aliksir/claude-code-skill-security-check
- Type: plugin
- Category: security
- tashan score: 38.0 / 100
- Adoption: 15.0
- Upkeep: 58.0
- Freshness: 87.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install skill-security-check@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
