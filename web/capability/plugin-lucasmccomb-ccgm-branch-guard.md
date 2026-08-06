# Branch Guard

> Hard PreToolUse gate that blocks Edit/Write/NotebookEdit and mutating git commands (commit, add, stage, apply) while HEAD is on the repo's default branch. Fires before the first edit so no work is ever produced on main. Bypass-proof (exit 2); ALLOWMAINCOMMIT=1 escape hatch; exempts in-progress rebase/merge/cherry-pick, unborn HEAD, and direct-to-main allowlisted repos.

## Facts
- Page: https://tashan.sh/capability/plugin-lucasmccomb-ccgm-branch-guard
- tashan id: plugin:lucasmccomb/ccgm/branch-guard
- Source: https://github.com/lucasmccomb/ccgm
- Type: plugin
- Category: devtools
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
/plugin install branch-guard@ccgm
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
