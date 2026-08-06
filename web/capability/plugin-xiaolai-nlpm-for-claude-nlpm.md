# Nlpm

> NLPM lints, scores, fixes, and trend-tracks the natural-language artifacts that make up a Claude Code plugin — skills, agents, commands, rules, hooks, manifests — against a 50-rule rubric on a 100-point scale. Ships focused agents (scanner, scorer, checker, fixer, tester, security-scanner, vague-scanner, vocab-drift-scanner) and a standalone Python validator (bin/nlpm-check) that runs in pre-commit hooks and CI without Claude Code installed, plus a shields.io "Validated by NLPM" badge.

## Facts
- Page: https://tashan.sh/capability/plugin-xiaolai-nlpm-for-claude-nlpm
- tashan id: plugin:xiaolai/nlpm-for-claude/nlpm
- Source: https://github.com/xiaolai/nlpm-for-claude
- Type: plugin
- Category: security
- tashan score: 67.0 / 100
- Adoption: 33.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 95
- License: ISC
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install nlpm@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
