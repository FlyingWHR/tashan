# Claude Anti Mem

> Claude gets things wrong in patterns. It invents library methods by analogy. It wraps a one-liner in argparse and logging. It assumes Snowflake when you said "dbt". Each mistake is usually obvious in hindsight, but Claude repeats the shape of the mistake across sessions because it has no record of them. claude-anti-mem fixes that with two skills working as a pair. anti-mem-collector writes: when you correct Claude, it logs the failure pattern to ~/.claude-anti-mem/anti-mem.md with a concrete Che

## Facts
- Page: https://tashan.sh/capability/plugin-markiv25-claude-antimem-claude-anti-mem
- tashan id: plugin:markiv25/claude-antimem/claude-anti-mem
- Source: https://github.com/markiv25/claude-antimem
- Type: plugin
- Category: devtools
- tashan score: 33.0 / 100
- Adoption: 11.0
- Upkeep: 67.0
- Freshness: 68.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-anti-mem@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
