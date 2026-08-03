# Stetkeep

> stetkeep stops Claude from refactoring code that's intentionally the way it is. Two pillars: 1) XML-structured behavior protocols (BRAIN/CRAFT/PERF, ~1.8K tokens each) encode routing, refactor discipline, and measurement-first performance rules using the XML tagging pattern Anthropic's prompting guide recommends for reliable parsing. 2) A 16-entry false-positive catalog of patterns Claude commonly mis-flags as anti-patterns: 1000-line constants files (not God Files, just data tables), V8-optim

## Facts
- Page: https://tashan.sh/capability/plugin-chanjoongx-stetkeep-stetkeep
- tashan id: plugin:chanjoongx/stetkeep/stetkeep
- Source: https://github.com/chanjoongx/stetkeep
- Type: plugin
- Category: devtools
- tashan score: 27.0 / 100
- Adoption: 7.0
- Upkeep: 50.0
- Freshness: 68.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install stetkeep@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
