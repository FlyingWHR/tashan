# Inbox Triage

> Runs a full inbox triage using the knowledge base created by the 'inbox-setup' skill. Light-intake by design (most invocations skip questions and run with KB-default preferences); asks at most 2 grill-me override questions when invocation is outside normal cadence or includes category-skip intent. Searches recent emails, classifies them via the user's taxonomy, researches new senders, generates recommendations, drafts replies (NEVER sends), delivers a report in the user's preferred format, and updates the knowledge base with learnings. Designed to run on a recurring schedule (1-3x daily) or on demand. Use when the user wants their inbox processed, in any variation (e.g., 'triage my inbox', 'inbox triage', 'check my email', 'run email triage', 'process my inbox', 'what's new in my email', 'handle my email', 'email triage'). Requires the inbox-setup skill to have been run first.

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-inbox-triage
- tashan id: skill:alirezarezvani/inbox-triage
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
cp -r inbox-triage ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
