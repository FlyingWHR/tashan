# Rehydrate

> rehydrate is a knowledge-based backup and restore plugin for Mac developers. Instead of copying every byte, it captures only what's truly local — dotfiles, SSH keys, gitignored .env files, sessions, locally-authored projects — and records the rest (apps, packages, git repos) as small inventory files that a future LLM replays on the target machine. The plugin ships two slash commands, /rehydrate:backup and /rehydrate:restore, plus snapshot diff and reachability-based garbage collection. Every bac

## Facts
- Page: https://tashan.sh/capability/plugin-eranshir-rehydrate-rehydrate
- tashan id: plugin:eranshir/rehydrate/rehydrate
- Source: https://github.com/eranshir/rehydrate
- Type: plugin
- Category: productivity
- tashan score: 34.0 / 100
- Adoption: 13.0
- Upkeep: 55.0
- Freshness: 79.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 2
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install rehydrate@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
