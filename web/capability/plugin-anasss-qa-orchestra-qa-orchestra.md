# QA Orchestra

> 10 specialized QA agents for Claude Code. Each agent answers a specific question about your PR: Does this diff implement the acceptance criteria? What test scenarios do I need? Which existing tests will break? and writes a structured Markdown report to qa-output/ that you can paste into GitHub, Jira, or Linear. Stack-agnostic: works with any web application (React, Angular, Vue, Rails, Django, Spring Boot, etc.). Agents include: functional-reviewer (diff vs AC analysis), test-scenario-designer,

## Facts
- Page: https://tashan.sh/capability/plugin-anasss-qa-orchestra-qa-orchestra
- tashan id: plugin:anasss/qa-orchestra/qa-orchestra
- Source: https://github.com/Anasss/qa-orchestra
- Type: plugin
- Category: devtools
- tashan score: 39.0 / 100
- Adoption: 21.0
- Upkeep: 67.0
- Freshness: 68.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 11
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install qa-orchestra@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
