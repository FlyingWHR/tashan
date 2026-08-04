# Md Document

> Converts long-form markdown (specs, RFCs, reports, plans, explainers) into a single-file, lightly-interactive HTML document with sticky TOC, scrollspy, search filter, code-copy buttons, and design-system-driven brand tokens. Triggers when the markdown-html-orchestrator classifies an input as DOCUMENT, or when invoked directly via /cs:md-document. Reads the design-system config via configloader.py and inlines the user's 12 derived CSS custom properties; refuses to render if onboarding hasn't run. Single-file output — Google Fonts + Prism.js CDN are the only externals; no framework runtime, no build step. Use after orchestrator routing or after design-system onboarding is confirmed.

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-md-document
- tashan id: skill:alirezarezvani/md-document
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
cp -r md-document ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
