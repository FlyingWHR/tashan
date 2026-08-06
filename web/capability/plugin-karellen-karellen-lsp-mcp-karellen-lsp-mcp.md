# Karellen Lsp

> LSP-backed code intelligence for Claude Code via MCP and native LSP. Navigate definitions, references, call hierarchies, type hierarchies, hover documentation, symbols, and diagnostics across C/C++ (clangd), Java/Kotlin (jdtls), and any language with a custom LSP server. Two interfaces, one shared daemon: - Native LSP proxy (karellen-lsp): Transparent code intelligence — no permission prompts, no manual registration. Auto-detects languages and routes to backend LSP servers. - MCP interf

## Facts
- Page: https://tashan.sh/capability/plugin-karellen-karellen-lsp-mcp-karellen-lsp-mcp
- tashan id: plugin:karellen/karellen-lsp-mcp/karellen-lsp-mcp
- Source: https://github.com/karellen/karellen-lsp-mcp
- Type: plugin
- Category: security
- tashan score: 30.0 / 100
- Adoption: 7.0
- Upkeep: 66.0
- Freshness: 65.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install karellen-lsp-mcp@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
