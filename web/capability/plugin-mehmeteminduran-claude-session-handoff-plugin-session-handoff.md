# Session Handoff

> A Claude Code plugin that lets you hand off an in-flight task from one AI tool to another — Claude Code → Codex, Codex → Cursor, Cursor → a fresh Claude session — without losing decisions, dead-ends, or "what to do next." Sessions are named, so multiple parallel threads of work can coexist in the same repo. Ships: /handoff [session] — write the current session's state into HANDOFF.<session.md /resume [session] — read that file, reconcile with git status, and execute the next concrete step A P

## Facts
- Page: https://tashan.sh/capability/plugin-mehmeteminduran-claude-session-handoff-plugin-session-handoff
- tashan id: plugin:mehmeteminduran/claude-session-handoff-plugin/session-handoff
- Source: https://github.com/mehmeteminduran/claude-session-handoff-plugin
- Type: plugin
- Category: devtools
- tashan score: 29.0 / 100
- Adoption: 7.0
- Upkeep: 53.0
- Freshness: 76.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install session-handoff@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
