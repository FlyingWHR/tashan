# Docker Image Scan

> Build a container image from a Dockerfile, scan it for security vulnerabilities with Trivy, and auto-clean up. Uses Docker or Podman. No local Trivy install needed - runs Trivy as a container.

## Facts
- Page: https://tashan.sh/capability/plugin-igor-koricanac-claude-image-scan-docker-image-scan
- tashan id: plugin:igor-koricanac/claude-image-scan/docker-image-scan
- Source: https://github.com/igor-koricanac/claude-image-scan
- Type: plugin
- Category: security
- tashan score: 31.0 / 100
- Adoption: 7.0
- Upkeep: 55.0
- Freshness: 80.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install docker-image-scan@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
