# Onecli

> Connect AI agents to external APIs with zero credential management. The OneCLI gateway transparently proxies all HTTPS traffic and injects stored credentials (OAuth tokens, API keys, AWS signatures) into outbound requests. Supports 40+ services including GitHub, Gmail, Google Calendar, Jira, AWS, Stripe, Datadog, and more. Policy rules enforce block, rate limit, and manual approval at the gateway level.

## Facts
- Page: https://tashan.sh/capability/plugin-onecli-onecli-plugin-onecli
- tashan id: plugin:onecli/onecli-plugin/onecli
- Source: https://github.com/onecli/onecli-plugin
- Type: plugin
- Category: security
- tashan score: 37.0 / 100
- Adoption: 11.0
- Upkeep: 60.0
- Freshness: 90.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: Apache-2.0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install onecli@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
