# Malchela

> MalChela is a Rust-based malware analysis toolkit for DFIR analysts and malware researchers. It exposes file triage, string extraction with IOC detection and MITRE ATT&CK mapping, YARA rule generation, hash lookup, VirusTotal and MalwareBazaar threat intel queries, and NSRL database checks — all accessible to Claude via MCP server integration.

## Facts
- Page: https://tashan.sh/capability/plugin-dwmetz-malchela-malchela
- tashan id: plugin:dwmetz/malchela/malchela
- Source: https://github.com/dwmetz/MalChela
- Type: plugin
- Category: security
- tashan score: 61.0 / 100
- Adoption: 34.0
- Upkeep: 80.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 114
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install malchela@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
