# Repo Intel

> Unified static analysis for AI agents — git history, AST symbols, project metadata, doc-code sync, and (optionally) LLM-augmented file descriptors plus a 3-depth narrative summary, via a cached, incrementally-updatable Rust binary. Scan a repo once, cache the result, then query it repeatedly. The heavy lifting runs in agent-analyzer (Rust) — this plugin provides the JavaScript interface, the skill layer that other plugins consume, and the orchestrati

## Facts
- Page: https://tashan.sh/capability/plugin-agent-sh-repo-intel-repo-intel
- tashan id: plugin:agent-sh/repo-intel/repo-intel
- Source: https://github.com/agent-sh/repo-intel
- Type: plugin
- Category: security
- tashan score: 41.0 / 100
- Adoption: 15.0
- Upkeep: 62.0
- Freshness: 95.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 3
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install repo-intel@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
