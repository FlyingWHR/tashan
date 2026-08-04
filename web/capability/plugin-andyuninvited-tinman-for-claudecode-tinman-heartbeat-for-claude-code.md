# Tinman Heartbeat For Claude Code

> Adds scheduled health monitoring to Claude Code. Define a HEARTBEAT.md checklist for your project and TinMan runs it through Claude on demand or on a timer. Claude analyzes your codebase against the checklist (uncommitted changes, failing tests, stale branches, disk space, whatever you care about) and reports what needs attention. Results are logged and can forward to Telegram via C3Poh. Three security presets control autonomy: sane (notify only, default), paranoid (read-only), and chaos (Claude

## Facts
- Page: https://tashan.sh/capability/plugin-andyuninvited-tinman-for-claudecode-tinman-heartbeat-for-claude-code
- tashan id: plugin:andyuninvited/tinman_for_claudecode/tinman-heartbeat-for-claude-code
- Source: https://github.com/andyuninvited/tinman_for_claudecode
- Type: plugin
- Category: productivity
- tashan score: 30.0 / 100
- Adoption: 11.0
- Upkeep: 64.0
- Freshness: 60.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install tinman-heartbeat-for-claude-code@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
