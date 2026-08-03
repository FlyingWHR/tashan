# Deeplake Hivemind

> Cloud-backed persistent memory for Claude Code powered by Deeplake. Automatically captures all session activity: user prompts, assistant responses, and tool calls into a shared Deeplake table. Makes conversation history searchable across sessions, users, and agents in the same workspace. Intercepts file operations on ~/.deeplake/memory/ through a virtual filesystem backed by Deeplake cloud SQL, supporting cat, ls, grep, jq, and 80+ shell builtins without requiring a FUSE mount.

## Facts
- Page: https://tashan.sh/capability/plugin-activeloopai-deeplake-claude-code-plugins-deeplake-hivemind
- tashan id: plugin:activeloopai/deeplake-claude-code-plugins/deeplake-hivemind
- Source: https://github.com/activeloopai/deeplake-claude-code-plugins
- Type: plugin
- Category: productivity
- tashan score: 74.0 / 100
- Adoption: 48.0
- Upkeep: 98.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: thin
- GitHub stars: 1,512
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install deeplake-hivemind@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
