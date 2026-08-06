# Codex Dispatch

> Codex Dispatch is an agent skill for Claude Code that ensures every Codex MCP dispatch is correct. It enforces the right cwd (target repo, not workspace), sets approval-policy: "never" so Codex never blocks on prompts, picks the right sandbox mode for the task, and requires prompts to be fully self-contained. Covers code review, plan execution, and general repo tasks.

## Facts
- Page: https://tashan.sh/capability/plugin-jcardama-codex-dispatch-codex-dispatch
- tashan id: plugin:jcardama/codex-dispatch/codex-dispatch
- Source: https://github.com/jcardama/codex-dispatch
- Type: plugin
- Category: security
- tashan score: 24.0 / 100
- Adoption: 7.0
- Upkeep: 46.0
- Freshness: 60.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install codex-dispatch@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
