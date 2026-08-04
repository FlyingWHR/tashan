# Graphify Setup

> Install and wire up Graphify — an open-source knowledge-graph tool for Claude Code. Registers a /graphify slash command and a PreToolUse hook that consults a local graph before file-search tool calls, dramatically reducing token cost on large codebases, docs, and mixed-media corpora. Handles code (25 languages via tree-sitter), Markdown, PDFs, diagrams, images, audio/video.

## Facts
- Page: https://tashan.sh/capability/skill-a2ngerer-graphify-setup
- tashan id: skill:a2ngerer/graphify-setup
- Source: https://github.com/a2ngerer/claude_onboarding_agent
- Type: skill
- Category: security
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: not measured
- Freshness: not measured
- Evidence coverage: not measured
- Health: not measured
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r graphify-setup ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
