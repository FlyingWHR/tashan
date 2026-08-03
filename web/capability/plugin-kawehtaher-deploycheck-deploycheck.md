# Deploycheck

> DeployCheck gives Claude visibility into your deployment pipeline. Ask "is staging ready to ship?" and Claude will ping your health endpoints, check CI pipeline status, compare Docker image tags between environments, and show you what commits would go out. It aggregates everything into a clear go/no-go recommendation. Supports GitHub Actions and GitLab CI, configured with a simple YAML file in your project root.

## Facts
- Page: https://tashan.sh/capability/plugin-kawehtaher-deploycheck-deploycheck
- tashan id: plugin:kawehtaher/deploycheck/deploycheck
- Source: https://github.com/kawehtaher/deploycheck
- Type: plugin
- Category: devtools
- tashan score: 28.0 / 100
- Adoption: 11.0
- Upkeep: 49.0
- Freshness: 66.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install deploycheck@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
