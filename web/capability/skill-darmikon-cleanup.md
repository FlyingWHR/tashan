# Cleanup

> Delete stale local git branches — ones whose remote was deleted after a merged or squashed PR (upstream "[gone]"), ones already merged into the default branch — and prune stale remote-tracking refs. Use when the user asks to clean up branches, remove old/dead/merged branches, "prune gone branches", tidy up their local repo, or says their branch list is a mess. Always previews and asks before deleting; never touches the current or default branch. Invoke with /cleanup.

## Facts
- Page: https://tashan.sh/capability/skill-darmikon-cleanup
- tashan id: skill:Darmikon/cleanup
- Source: https://github.com/Darmikon/skills
- Type: skill
- Category: devtools
- tashan score: 40.0 / 100
- Adoption: 14.0
- Upkeep: 62.0
- Freshness: 95.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r cleanup ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
