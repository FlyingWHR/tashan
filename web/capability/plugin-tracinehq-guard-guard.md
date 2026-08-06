# Guard

> PreToolUse hooks for Claude Code that deny dangerous shell, git, and credential commands before they run: rm -rf / shapes, git push --force, python -c / node -e eval, pipe-to-shell, live credentials (gh auth token, aws sts get-session-token, op read), git -c core.hooksPath=… injection, silent commit reuse (git commit -C HEAD~1, --reuse-message). Each deny names the rule and prints a one-line override (guard allowlist allow-command …); decisions stream to a JSONL log the opt

## Facts
- Page: https://tashan.sh/capability/plugin-tracinehq-guard-guard
- tashan id: plugin:tracinehq/guard/guard
- Source: https://github.com/TracineHQ/guard
- Type: plugin
- Category: security
- tashan score: 41.0 / 100
- Adoption: 7.0
- Upkeep: 94.0
- Freshness: 87.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install guard@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
