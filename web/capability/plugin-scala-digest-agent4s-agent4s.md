# Agent4s

> Scala code intelligence for AI coding agents. 35 commands — search, jump-to-definition, find references, call-graph, dead code detection, semantic rename, bug-hunt with taint analysis, scaffolding — all without a build server or compilation. Cold index 2.7s, warm 349ms on 18k files. Bug-hunt scans 45 vulnerability patterns (SQL injection, XSS, SSRF, hardcoded secrets, weak crypto, concurrency bugs) with cross-file taint analysis. SemanticDB integration for type-aware mode when compiled artifacts

## Facts
- Page: https://tashan.sh/capability/plugin-scala-digest-agent4s-agent4s
- tashan id: plugin:scala-digest/agent4s/agent4s
- Source: https://github.com/scala-digest/agent4s
- Type: plugin
- Category: security
- tashan score: 38.0 / 100
- Adoption: 22.0
- Upkeep: 65.0
- Freshness: 64.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 13
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install agent4s@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
