# Sonarqube

> Integrate SonarQube code quality and security analysis into Claude Code: this includes namespaced slash commands, a guided skill to setup the SonarQube CLI, and a startup check for the CLI and wiring. MCP server registration and secrets-scanning hooks are installed on your machine by the SonarQube CLI as part of the setup.

## Facts
- Page: https://tashan.sh/capability/plugin-sonarsource-sonarqube-agent-plugins-sonarqube
- tashan id: plugin:sonarsource/sonarqube-agent-plugins/sonarqube
- Source: https://github.com/SonarSource/sonarqube-agent-plugins
- Type: plugin
- Category: productivity
- tashan score: 69.0 / 100
- Adoption: 37.0
- Upkeep: 97.0
- Freshness: 94.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 98
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install sonarqube@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
