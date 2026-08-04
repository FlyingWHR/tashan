# Tramp

> TRAMP-like transparent remote execution for AI coding agents. Routes file and shell operations (bash, read, write, edit, glob, grep, ls) to remote targets via SSH or Docker. The agent stays local — tools execute remotely. Supports persistent SSH connections with native multiplexing, SFTP file I/O, bash and PowerShell shells, port forwarding, multi-target workflows, and network boundary context injection.

## Facts
- Page: https://tashan.sh/capability/plugin-marcfargas-tramp-tramp
- tashan id: plugin:marcfargas/tramp/tramp
- Source: https://github.com/marcfargas/tramp
- Type: plugin
- Category: security
- tashan score: 25.0 / 100
- Adoption: 7.0
- Upkeep: 47.0
- Freshness: 63.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: LGPL-3.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install tramp@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
