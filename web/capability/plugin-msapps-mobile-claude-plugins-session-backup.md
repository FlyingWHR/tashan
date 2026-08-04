# Session Backup

> Zero-config daily backups of Claude session data, skills, and configs to cloud storage. Works for both Cowork and Claude Code — just run /backup-now and it auto-detects your environment, generates a unique instance ID, and backs up everything. Each user gets a collision-safe namespace so multiple users never overwrite each other's backups. Includes /backup-setup for customizing schedule, folders, and retention policy, and /backup-status to check when the last backup ran. Supports Google Drive ou

## Facts
- Page: https://tashan.sh/capability/plugin-msapps-mobile-claude-plugins-session-backup
- tashan id: plugin:msapps-mobile/claude-plugins/session-backup
- Source: https://github.com/MSApps-Mobile/claude-plugins
- Type: plugin
- Category: files
- tashan score: 39.0 / 100
- Adoption: 7.0
- Upkeep: 92.0
- Freshness: 82.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install session-backup@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
