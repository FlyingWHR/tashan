# Slack API

> Discover, navigate, and call Slack Web API methods (the family.method endpoints at slack.com/api like chat.postMessage, conversations.history, users.info, views.open). Use this skill whenever the developer asks which Slack API method does something, needs a method's required OAuth scopes or token type, wants to call or test a Web API method, is handling cursor pagination (nextcursor), hitting rate limits (tier/ratelimited/Retry-After), or debugging API errors like missingscope, invalidauth, or channelnotfound. Also trigger when they paste a slack.com/api/ URL or a docs.slack.dev/reference/methods link, or ask how to list/fetch/post/update Slack resources via the API. This skill covers the Web API method layer: finding the right method, reading its contract (scopes, arguments, errors), and calling it over raw HTTP with curl or through a Slack SDK.

## Facts
- Page: https://tashan.sh/capability/skill-slackapi-slack-api
- tashan id: skill:slackapi/slack-api
- Source: https://github.com/slackapi/slack-mcp-plugin
- Type: skill
- Category: comms
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 98.0
- Freshness: 95.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r slack-api ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
