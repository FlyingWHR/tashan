# Ty Python Lsp

> Wires up Astral's ty, an extremely fast Python type checker, as an LSP server for Claude Code's built-in LSP tool. On .py / .pyi / .pyw files Claude can use hover (inferred types and docstrings), go-to-definition, go-to-implementation, find-references, document and workspace symbol search, and call hierarchy. Configuration is auto-detected from pyproject.toml; no extra LSP settings required. Requires ty on PATH (uv tool install ty or pip install ty).

## Facts
- Page: https://tashan.sh/capability/plugin-andres-ortizl-ty-lsp-claude-code-plugin-ty-python-lsp
- tashan id: plugin:andres-ortizl/ty-lsp-claude-code-plugin/ty-python-lsp
- Source: https://github.com/andres-ortizl/ty-lsp-claude-code-plugin
- Type: plugin
- Category: devtools
- tashan score: 28.0 / 100
- Adoption: 7.0
- Upkeep: 51.0
- Freshness: 71.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install ty-python-lsp@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
