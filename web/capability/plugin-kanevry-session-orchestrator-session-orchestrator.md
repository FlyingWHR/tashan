# Session Orchestrator

> Session-level orchestration for Claude Code - structures development work into 5 typed waves (Discovery → Core → Polish → Quality → Finalization) with parallel subagent execution, inter-wave quality gates, and verified close-out. Auto-detects GitLab or GitHub from your git remote for full VCS lifecycle support. Three commands replace manual session management: /session starts with project analysis, /go executes the wave plan, /close verifies and commits.

## Facts
- Page: https://tashan.sh/capability/plugin-kanevry-session-orchestrator-session-orchestrator
- tashan id: plugin:kanevry/session-orchestrator/session-orchestrator
- Source: https://github.com/Kanevry/session-orchestrator
- Type: plugin
- Category: productivity
- tashan score: 64.0 / 100
- Adoption: 29.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 48
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install session-orchestrator@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
