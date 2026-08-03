# Project Artifact

> Generate and publish a project status artifact — an opinionated, tabbed status page for a project too big for one update (overview & success criteria, the workstream sequence, next steps, plus background, plan, risks & open questions, and decisions/FAQ when they earn a tab) — published with the built-in Artifact tool to a default-private claude.ai page the user can share with teammates. Use when a piece of work spans several workstreams and you want a shareable overview kept current. Each artifact is backed by a small per-project config in the plugin data dir, so refreshing it re-gathers live state, redeploys the same URL, and reports only the delta. For software projects whose workstreams are PRs, also read swe.md (the X.Y PR-numbering convention; pulling PR state with gh/git; a per-PR detail block). Needs the built-in Artifact tool (claude.ai login). Not for single-PR changes or public docs.

## Facts
- Page: https://tashan.sh/capability/skill-anthropics-project-artifact
- tashan id: skill:anthropics/project-artifact
- Source: https://github.com/anthropics/claude-plugins-official
- Type: skill
- Category: productivity
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: Apache-2.0
- Official: yes

## Install

```sh
cp -r project-artifact ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
