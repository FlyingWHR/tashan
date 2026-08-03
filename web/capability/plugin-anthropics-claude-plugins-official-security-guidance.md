# Security Guidance

> Optional external dependency (official Anthropic). Hooks-based in-session security review: per-edit pattern match, end-of-turn diff review, commit review. Pipeline runs without it; the security phase still does full OWASP.

## Facts
- Page: https://tashan.sh/capability/plugin-anthropics-claude-plugins-official-security-guidance
- tashan id: plugin:anthropics/claude-plugins-official/security-guidance
- Source: https://github.com/anthropics/claude-plugins-official
- Type: plugin
- Category: security
- tashan score: 46.0 / 100
- Adoption: 11.0
- Upkeep: 100.0
- Freshness: not measured
- Evidence coverage: 62% of the inputs this score can use
- Health: not measured
- Instruction depth: not yet graded
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add AratKruglik/claude-sdlc
/plugin install security-guidance@sdlc-marketplace
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
