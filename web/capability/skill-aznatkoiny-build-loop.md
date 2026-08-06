# Build Loop · Aznatkoiny

> Launch the isolated build-until-green loop for a forge project. Run when .forge/state.json shows phase=armed, after /plugin-forge:arm-evals. Walks the preconditions checklist (trust dialog, hooks enabled, MCP OAuth preflight for live servers, worktree base ref, permissions.allow for a long unattended run), then starts bin/forge-build in background Bash: a git worktree seeded with the frozen suite plus a headless /goal session that iterates until forge-eval prints the FORGEEVAL scoreboard line with RESULT=PASS without touching evals/. Tails progress, applies the StopFailure resume-not-respawn recipe on ratelimit/overloaded, and on PASS hands off to /plugin-forge:verify. Use forge-build --no-goal when hooks are disabled.

## Facts
- Page: https://tashan.sh/capability/skill-aznatkoiny-build-loop
- tashan id: skill:Aznatkoiny/build-loop
- Source: https://github.com/Aznatkoiny/claude-dev-toolkit
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
cp -r build-loop ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
