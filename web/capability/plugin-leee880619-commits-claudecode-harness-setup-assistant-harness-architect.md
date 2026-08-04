# Harness Architect

> harness-architect is a meta-tool that scans any target project and builds an end-to-end Claude Code harness — CLAUDE.md, settings, rules, agents, playbooks, hooks, and MCP — through a 9-phase orchestrated workflow. The plugin enforces a strict Agent-Playbook separation (WHO / HOW): agents define identity and hand off methodology to sub-agent-only playbooks, preventing the main session from bypassing guardrails. Every phase is reviewed by an independent red-team advisor that produces BLOCK / ASK

## Facts
- Page: https://tashan.sh/capability/plugin-leee880619-commits-claudecode-harness-setup-assistant-harness-architect
- tashan id: plugin:leee880619-commits/claudecode-harness-setup-assistant/harness-architect
- Source: https://github.com/leee880619-commits/ClaudeCode-Harness-Setup-Assistant
- Type: plugin
- Category: security
- tashan score: 39.0 / 100
- Adoption: 13.0
- Upkeep: 61.0
- Freshness: 92.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install harness-architect@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
