# Java Plugin

> Plain Java backend stack provider (priority=100). Detects any Maven or Gradle project (pom.xml / build.gradle / build.gradle.kts). Adds java-architect agent (Sonnet/medium) for plain Java libraries, CLI tools, and micro-services without a recognized web framework. Falls back gracefully when spring-boot-plugin (priority 150) matches instead. Reuses java-foundation skills.

## Facts
- Page: https://tashan.sh/capability/plugin-aratkruglik-claude-sdlc-java-plugin
- tashan id: plugin:aratkruglik/claude-sdlc/java-plugin
- Source: https://github.com/AratKruglik/claude-sdlc
- Type: plugin
- Category: devtools
- tashan score: 36.0 / 100
- Adoption: 7.0
- Upkeep: 63.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add AratKruglik/claude-sdlc
/plugin install java-plugin@sdlc-marketplace
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
