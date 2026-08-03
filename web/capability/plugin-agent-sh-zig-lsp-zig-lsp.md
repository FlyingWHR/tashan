# Zig Lsp

> Zig language server for Claude Code via ZLS — automatic post-edit diagnostics, jump-to-definition, find-references, hover. Maps .zig and .zon to language zig; enables enablebuildonsave so post-edit diagnostics surface real type errors (not just parser errors). 30s startup timeout, restart-on-crash with cap of 3. Requires zls on PATH (ZVM, prebuilt zigtools.org, or build from source) with matching zig version. Verified end-to-end on Claude Code 2.1.119.

## Facts
- Page: https://tashan.sh/capability/plugin-agent-sh-zig-lsp-zig-lsp
- tashan id: plugin:agent-sh/zig-lsp/zig-lsp
- Source: https://github.com/agent-sh/zig-lsp
- Type: plugin
- Category: devtools
- tashan score: 30.0 / 100
- Adoption: 7.0
- Upkeep: 55.0
- Freshness: 79.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install zig-lsp@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
