# Aport Guardrails

> Security guardrails for Claude Code. Intercepts every tool call via PreToolUse hook and evaluates it against your Open Agent Passport (OAP) policy before execution. Blocks unauthorized commands, dangerous file operations, and policy violations. All evaluation runs locally by default - zero network calls, works offline. Open-source (Apache 2.0). Includes three skills: - /aport-guardrails:claude-code — Set up guardrails and create a passport - /aport-guardrails:status — Check guardrail status and

## Facts
- Page: https://tashan.sh/capability/plugin-aporthq-aport-agent-guardrails-aport-guardrails
- tashan id: plugin:aporthq/aport-agent-guardrails/aport-guardrails
- Source: https://github.com/aporthq/aport-agent-guardrails
- Type: plugin
- Category: security
- tashan score: 48.0 / 100
- Adoption: 25.0
- Upkeep: 62.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 25
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install aport-guardrails@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
