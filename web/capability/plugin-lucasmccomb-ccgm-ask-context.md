# Ask Context

> Hard PreToolUse gate on AskUserQuestion that blocks questions whose decision context is invisible to the user. Three deterministic gates: deictic references to unseen context ('with that context', 'see above'), identical re-asks after the user pushed back in free text, and mid-workstream questions asked with no visible text emitted this turn. Block messages teach the exact recovery (visible context brief, then a self-contained question). Fail-open on transcript errors; CCGMASKCONTEXTOFF=1 esc

## Facts
- Page: https://tashan.sh/capability/plugin-lucasmccomb-ccgm-ask-context
- tashan id: plugin:lucasmccomb/ccgm/ask-context
- Source: https://github.com/lucasmccomb/ccgm
- Type: plugin
- Category: security
- tashan score: 37.0 / 100
- Adoption: 7.0
- Upkeep: 64.0
- Freshness: 100.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add lucasmccomb/ccgm
/plugin install ask-context@ccgm
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
