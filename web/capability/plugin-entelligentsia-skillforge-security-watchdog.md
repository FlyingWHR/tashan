# Security Watchdog

> Automatic security scanner for Claude Code plugins — detects new or updated extensions at session start and scans them for prompt injection, malicious hook scripts, and data exfiltration. The Problem LLM extension ecosystems are a novel attack surface. Traditional security tooling does not cover two threats unique to AI extensions: - Host attacks — hook scripts run shell commands automatically on session start, with full user privileges - Mind attacks — skill and command files ar

## Facts
- Page: https://tashan.sh/capability/plugin-entelligentsia-skillforge-security-watchdog
- tashan id: plugin:entelligentsia/skillforge/security-watchdog
- Source: https://github.com/Entelligentsia/skillforge
- Type: plugin
- Category: security
- tashan score: 39.0 / 100
- Adoption: 11.0
- Upkeep: 63.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install security-watchdog@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
