# Cc Suite

> cc-suite turns three CLI tools (Claude Code, OpenAI Codex CLI, Google Gemini CLI) into one shared brain. Project context is written once in AGENTS.md; CLAUDE.md and GEMINI.md just @AGENTS.md to import it. Skills live in .claude/skills/ and .agents/skills/ symlinks to it, so the same skill works in all three CLIs. Hooks defined for Claude Code are mirrored into Codex's hook system. MCP servers in .mcp.json are visible to all three. The Claude↔Codex delegation lane is bidirectional: from Cla

## Facts
- Page: https://tashan.sh/capability/plugin-xiaolai-cc-suite-cc-suite
- tashan id: plugin:xiaolai/cc-suite/cc-suite
- Source: https://github.com/xiaolai/cc-suite
- Type: plugin
- Category: productivity
- tashan score: 50.0 / 100
- Adoption: 26.0
- Upkeep: 63.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 29
- License: ISC
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install cc-suite@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
