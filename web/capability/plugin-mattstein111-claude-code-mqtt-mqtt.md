# Mqtt

> MQTT channel plugin for Claude Code. Bridges MQTT messages into Claude Code sessions via the MCP channel protocol, enabling cross-session messaging, Home Assistant integration, and IoT device control. Features a three-tier gating model (admit/watch/mute) to prevent context window flooding, per-session persistent configuration, request/reply with correlation IDs, and health monitoring via retained messages.

## Facts
- Page: https://tashan.sh/capability/plugin-mattstein111-claude-code-mqtt-mqtt
- tashan id: plugin:mattstein111/claude-code-mqtt/mqtt
- Source: https://github.com/mattstein111/claude-code-mqtt
- Type: plugin
- Category: productivity
- tashan score: 42.0 / 100
- Adoption: 7.0
- Upkeep: 95.0
- Freshness: 89.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install mqtt@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
