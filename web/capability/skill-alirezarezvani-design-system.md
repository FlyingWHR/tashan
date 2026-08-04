# Design System

> Captures the user's brand identity once via a 10-question onboarding wizard (primary/accent HEX + heading + body Google Fonts + design style editorial/technical/minimal/playful + default output directory + syntax theme + TOC behavior + optional logo/company), validates body-text and link contrast against WCAG 2.2 AA, derives 12 CSS custom properties in HSL space, and stores the result for every markdown-html converter to consume. Use before any markdown-html conversion. Triggers on first-run onboarding ("set up the brand", "configure markdown-html", "run onboarding"), on explicit reset ("reset the design system", "re-onboard"), and is checked by every converter via configloader.py before rendering. Refuses to save if body-text contrast fails AA 4.5:1 or the output dir isn't writable. Precedence: project (./.markdown-html/) global (~/.config/markdown-html/) built-in defaults; MARKDOWNHTMLNOCONFIG=1 bypasses.

## Facts
- Page: https://tashan.sh/capability/skill-alirezarezvani-design-system
- tashan id: skill:alirezarezvani/design-system
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
cp -r design-system ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
