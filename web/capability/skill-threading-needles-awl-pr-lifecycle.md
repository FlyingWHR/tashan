# Awl Pr Lifecycle

> Pull request lifecycle for Awl — branch naming, the commit → create-pr → describe → babysit → merge flow, Linear status transitions at each phase, PR description conventions, and the safety rules around rebasing, CI, and squash-merging. Use this skill whenever Claude is working on a feature branch (anything matching [A-Z]+-[0-9]+-), running git commands that will produce a PR, creating/describing/reviewing/merging a pull request, or when a GitHub PR URL shows up in the conversation. Make sure to use this skill whenever the user is about to run /awl-dev:commit, /awl-dev:create-pr, /awl-dev:describe-pr, /awl-dev:babysit-pr, or /awl-dev:merge-pr, even if they don't explicitly ask for PR guidance.

## Facts
- Page: https://tashan.sh/capability/skill-threading-needles-awl-pr-lifecycle
- tashan id: skill:Threading-Needles/awl-pr-lifecycle
- Source: https://github.com/Threading-Needles/awl
- Type: skill
- Category: other
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
cp -r awl-pr-lifecycle ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
