# Claude Snapshot

> claude-snapshot exports and imports portable snapshots of your entire Claude Code setup across machines. It captures settings.json, plugins, marketplace registrations, hooks, and global CLAUDE.md files into a single .tar.gz file with a manifest index. Absolute paths are normalized to $HOME for cross-machine portability. On apply, it backs up conflicting files as .bak and installs missing plugins automatically. Supports slim (config only, ~6KB) and full (with plugin caches for offline restore) ex

## Facts
- Page: https://tashan.sh/capability/plugin-adhenawer-claude-snapshot-claude-snapshot
- tashan id: plugin:adhenawer/claude-snapshot/claude-snapshot
- Source: https://github.com/adhenawer/claude-snapshot
- Type: plugin
- Category: productivity
- tashan score: 30.0 / 100
- Adoption: 13.0
- Upkeep: 50.0
- Freshness: 68.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-snapshot@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
