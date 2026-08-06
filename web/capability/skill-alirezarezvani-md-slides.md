# Md Slides

> Converts a markdown deck (slides separated by --- HR boundaries or by H1 headings, with optional <!-- notes: ... -- presenter notes blocks) into a single-file HTML presentation with arrow-key / space / PgDn / PgUp / Home / End / P / Esc keyboard navigation, presenter mode (split view with current slide + speaker notes + clock + next-slide preview), URL-hash deep linking, and @media print page-per-slide for PDF export. Triggers when the markdown-html-orchestrator classifies an input as SLIDES, or when invoked directly via /cs:md-slides. Reuses md-document's markdown parser for slide-body rendering and reads design-system tokens via configloader.py. Refuses if input has no clear slide boundaries, produces a 1-slide deck, or --strict-notes is on with < 50% notes coverage. Use after orchestrator routing.

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-md-slides
- tashan id: skill:alirezarezvani/md-slides
- Source: https://github.com/alirezarezvani/claude-skills
- Type: skill
- Category: design
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 97.0
- Freshness: 93.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r md-slides ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
