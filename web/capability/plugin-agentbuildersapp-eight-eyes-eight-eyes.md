# Eight Eyes

> Multi-agent code review with 8 hook-enforced roles. Each role targets a different failure surface — the skeptic reviews blind without the implementer's narrative, the security auditor can only run approved scan commands, the test writer cannot touch source code, and the implementer cannot run Bash. Scope boundaries are enforced through deterministic Python hooks at the PreToolUse layer, not through prompt instructions. The 8 roles: implementer (scoped writes, no Bash), test-writer (test directo

## Facts
- Page: https://tashan.sh/capability/plugin-agentbuildersapp-eight-eyes-eight-eyes
- tashan id: plugin:agentbuildersapp/eight-eyes/eight-eyes
- Source: https://github.com/AgentBuildersApp/eight-eyes
- Type: plugin
- Category: productivity
- tashan score: 33.0 / 100
- Adoption: 13.0
- Upkeep: 65.0
- Freshness: 64.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install eight-eyes@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
