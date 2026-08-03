# Agent Team

> 13 specialized AI agents collaborating via SQLite. 44 MCP tools. One-command install.

## Facts
- Page: https://tashan.sh/capability/pkg-agent-team-mcp
- tashan id: pkg:agent-team-mcp
- Source: https://github.com/RichardLemmon/AgentTeam
- npm: https://www.npmjs.com/package/agent-team-mcp
- Type: npm
- Category: devtools
- tashan score: 35.0 / 100
- Adoption: 22.0
- Upkeep: 51.0
- Freshness: 63.0
- Evidence coverage: 100% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- npm downloads: 39/week
- Official: no

## Install

```sh
claude mcp add agent-team -- npx -y agent-team-mcp
```

## Security audit
- Known advisories: 0
- Install-time script: `node -e "const fs=require('fs'),p=require('path'),d=p.join(require('os').homedir(),'.claude','skills','agent-team');try{fs.mkdirSync(d,{recursive:true});fs.copyFileSync(p.join(__dirname,'dist','SKILL.md'),p.join(d,'SKILL.md'));console.log('AgentTeam /team skill installed to ~/.claude/skills/agent-te`
- Build provenance: not attested
- Declared permission surface: database

Permissions are read from DECLARED dependencies only. Nothing is executed, so an empty result means "nothing declared", never "nothing possible".

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
