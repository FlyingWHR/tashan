# Awl Conventional Commits

> Conventional commit format rules for Awl — commit types (feat/fix/perf/revert for changelog; docs/style/refactor/test/build/ci/chore for internal), scope detection from changed-file paths, header format (max 100 chars, imperative mood, no trailing period), body and footer conventions, Linear ticket footer extraction from branch names, and the Awl-specific rule against adding Co-authored-by: Claude attribution to plain commits. Use this skill whenever Claude is about to run git commit, being asked to write or fix a commit message, invoking /awl-dev:commit, or reviewing commit messages in a PR. Make sure to use this skill whenever a commit is about to be created, even if the user didn't explicitly ask for format guidance — writing commits in the wrong format breaks changelog generation.

## Facts
- Page: https://tashan.sh/capability/skill-threading-needles-awl-conventional-commits
- tashan id: skill:Threading-Needles/awl-conventional-commits
- Source: https://github.com/Threading-Needles/awl
- Type: skill
- Category: data
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
cp -r awl-conventional-commits ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
