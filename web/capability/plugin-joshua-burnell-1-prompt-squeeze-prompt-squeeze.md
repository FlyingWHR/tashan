# Prompt Squeeze

> prompt-squeeze builds prompt-cost discipline into Claude Code via three surfaces: /squeeze skill that compresses a verbose prompt into a token-efficient equivalent and renders a side-by-side markdown comparison plus a cited receipt (dollars saved, Wh saved, CO₂e at US-grid average). UserPromptSubmit hook that meters every prompt, nudges Claude when ≥25% compressible, and (in interactive mode) blocks prompts above a configurable token limit while showing a 2-column ASCII diff so the user can re

## Facts
- Page: https://tashan.sh/capability/plugin-joshua-burnell-1-prompt-squeeze-prompt-squeeze
- tashan id: plugin:joshua-burnell-1/prompt-squeeze/prompt-squeeze
- Source: https://github.com/joshua-burnell-1/prompt-squeeze
- Type: plugin
- Category: security
- tashan score: 30.0 / 100
- Adoption: 11.0
- Upkeep: 51.0
- Freshness: 71.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install prompt-squeeze@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
