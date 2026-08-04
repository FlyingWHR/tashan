# Dependency Evaluator

> Evaluate npm and Python packages before adding them as dependencies. Automatically gathers package metadata, analyzes source complexity, checks security and maintenance health, and produces a structured USE / EXTRACT / BUILD verdict. Auto-triggers when your agent is about to install a new package, or run on-demand with /evaluating-dependencies <package [function]. Catches supply chain red flags like .pth injection, typosquatting, and stale maintainership.

## Facts
- Page: https://tashan.sh/capability/plugin-apart-tech-plugins-dependency-evaluator
- tashan id: plugin:apart-tech/plugins/dependency-evaluator
- Source: https://github.com/apart-tech/plugins
- Type: plugin
- Category: security
- tashan score: 25.0 / 100
- Adoption: 7.0
- Upkeep: 47.0
- Freshness: 63.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install dependency-evaluator@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
