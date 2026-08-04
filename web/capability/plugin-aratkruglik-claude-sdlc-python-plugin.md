# Python Plugin

> Plain Python backend stack provider (priority=100). Detects any Python project via pyproject.toml/requirements.txt/setup.py/Pipfile. Adds python-architect agent (Sonnet/medium) for libraries, CLI tools, scripts, data pipelines, and microservices without a recognized web framework. Falls back gracefully when django-plugin/fastapi-plugin/flask-plugin (priority 150) match instead. Adds python-app-conventions skill. Reuses python-foundation skills.

## Facts
- Page: https://tashan.sh/capability/plugin-aratkruglik-claude-sdlc-python-plugin
- tashan id: plugin:aratkruglik/claude-sdlc/python-plugin
- Source: https://github.com/AratKruglik/claude-sdlc
- Type: plugin
- Category: devtools
- tashan score: 36.0 / 100
- Adoption: 7.0
- Upkeep: 63.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add AratKruglik/claude-sdlc
/plugin install python-plugin@sdlc-marketplace
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
