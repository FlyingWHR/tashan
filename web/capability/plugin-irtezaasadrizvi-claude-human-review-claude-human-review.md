# Claude Human Review

> claude-human-review adds a human approval gate at the end of every Claude Code turn that edits files. When Claude tries to stop, the plugin pauses it and has Claude do two things before the turn ends. First, drop a one-line doc comment on any class, function, or non-obvious config block it created or materially changed, using the right style per language (JSDoc for TS/JS, docstrings for Python, // for Go, and so on). Second, write a short plain-English review of what changed and why, flagging ri

## Facts
- Page: https://tashan.sh/capability/plugin-irtezaasadrizvi-claude-human-review-claude-human-review
- tashan id: plugin:irtezaasadrizvi/claude-human-review/claude-human-review
- Source: https://github.com/IrtezaAsadRizvi/claude-human-review
- Type: plugin
- Category: productivity
- tashan score: 35.0 / 100
- Adoption: 22.0
- Upkeep: 50.0
- Freshness: 70.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 14
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-human-review@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
