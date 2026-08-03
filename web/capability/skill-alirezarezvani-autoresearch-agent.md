# Autoresearch Agent

> Autonomous experiment loop that optimizes any file by a measurable metric. Inspired by Karpathy's autoresearch. The agent edits a target file, runs a fixed evaluation, keeps improvements (git commit), discards failures (git reset), and loops indefinitely. Use when: user wants to optimize code speed, reduce bundle/image size, improve test pass rate, optimize prompts, improve content quality (headlines, copy, CTR), or run any measurable improvement loop. Requires: a target file, an evaluation command that outputs a metric, and a git repo.

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-autoresearch-agent
- tashan id: skill:alirezarezvani/autoresearch-agent
- Source: https://github.com/alirezarezvani/claude-skills
- Type: skill
- Category: productivity
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 97.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r autoresearch-agent ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
