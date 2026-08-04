# Markdown Html Orchestrator

> Use when a user wants to convert any markdown file in their Claude project into a single-file, lightly-interactive HTML — long-form documents (specs, plans, RFCs, reports, explainers), code reviews with diffs and severity-tagged annotations, or slide decks. Triggers on "convert this markdown to HTML", "make this an HTML file", "turn this into an interactive document", "render this report as HTML", "PR writeup as HTML", "slides from this markdown". Forks context to route to one of three converter sub-skills (md-document, md-review, md-slides) based on a deterministic doctype classifier, after the user has run the design-system onboarding once. Refuses if input is under 100 lines (per Shihipar — markdown still wins below the threshold) or design-system isn't onboarded. Distinct from Anthropic's official Playground plugin (which is interactive prompt-tuning controls with sliders/knobs/prompt-copy-back) and from marketing/landing/ (which is a landing-page generator).

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-markdown-html-orchestrator
- tashan id: skill:alirezarezvani/markdown-html-orchestrator
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
cp -r markdown-html-orchestrator ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
