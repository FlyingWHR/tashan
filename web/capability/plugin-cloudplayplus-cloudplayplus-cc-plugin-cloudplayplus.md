# Cloudplayplus

> Channel plugin that bridges Claude Code to a running CloudPlayPlus Flutter app. Messages from remote CloudPlayPlus users are pushed into Claude Code as channel events, and Claude's replies are delivered back through the app. Unlike Telegram/Discord/iMessage channels, the MCP server runs inside the long-running CloudPlayPlus host app (over loopback HTTP), not as a Claude Code subprocess — so the app's existing user authentication gates every inbound message before it reaches the session.

## Facts
- Page: https://tashan.sh/capability/plugin-cloudplayplus-cloudplayplus-cc-plugin-cloudplayplus
- tashan id: plugin:cloudplayplus/cloudplayplus-cc-plugin/cloudplayplus
- Source: https://github.com/CloudPlayPlus/cloudplayplus-cc-plugin
- Type: plugin
- Category: comms
- tashan score: 26.0 / 100
- Adoption: 7.0
- Upkeep: 49.0
- Freshness: 67.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install cloudplayplus@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
