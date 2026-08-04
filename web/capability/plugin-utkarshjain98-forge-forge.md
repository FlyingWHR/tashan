# Forge · UtkarshJain98

> Description: Adversarial code hardening for Claude Code. Forge spawns two agents — a Builder and a Breaker — that iterate against each other until the code is unbreakable. The Builder implements a feature, the Breaker writes adversarial tests to prove bugs, and the Builder must fix the implementation without deleting or weakening the tests. The loop continues until the Breaker can't produce a failing test. The result is battle-tested code with a permanent adversarial test suite. Key features:

## Facts
- Page: https://tashan.sh/capability/plugin-utkarshjain98-forge-forge
- tashan id: plugin:utkarshjain98/forge/forge
- Source: https://github.com/UtkarshJain98/forge
- Type: plugin
- Category: devtools
- tashan score: 29.0 / 100
- Adoption: 11.0
- Upkeep: 50.0
- Freshness: 70.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install forge@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
