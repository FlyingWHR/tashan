# Claude Project Context Manager

> A skill and agent plugin that reads your project's architecture documentation — README.md, architecture.md, and related files — and enforces those documented conventions on every code change Claude makes. Includes a /project-context skill for on-demand rule extraction, an architecture-reviewer subagent that performs deep read-only compliance analysis with structured PASS/WARN/FAIL reports, and a SessionStart hook that automatically loads project context when Claude launches. Ensures file plac...

## Facts
- Page: https://tashan.sh/capability/plugin-its-animay-claude-project-context-manager-claude-project-context-manager
- tashan id: plugin:its-animay/claude-project-context-manager/claude-project-context-manager
- Source: https://github.com/its-animay/claude-project-context-manager
- Type: plugin
- Category: security
- tashan score: 25.0 / 100
- Adoption: 15.0
- Upkeep: 43.0
- Freshness: 53.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-project-context-manager@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
