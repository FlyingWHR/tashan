# What to use for agent development

> Building the agent itself — tools, memory, orchestration, handoffs.

Source: https://tashan.sh/task/agent-development.html
Ranked by fit for the task, then how well it documents itself, then the tashan score
  (upkeep and freshness, gated by real adoption). Public evidence only — nothing paid can
  change a rank. Method: https://tashan.sh/methodology.html

## Ranked

| # | Capability | tashan score | Adoption evidence | Activity |
|---|---|---|---|---|
| 1 | [Loki Mode](https://tashan.sh/capability/pkg-loki-mode.html) | 75 | 17k/wk | active |
| 2 | [Agent Afk](https://tashan.sh/capability/pkg-agent-afk.html) | 73 | 9k/wk | active |
| 3 | [Adcp Client](https://tashan.sh/capability/plugin-adcontextprotocol-adcp-client-adcp-client.html) | 47 | 18 ★ | active |
| 4 | [Inkbox](https://tashan.sh/capability/plugin-inkbox-ai-inkbox-inkbox.html) | 47 | 33 ★ | active |
| 5 | [Statsclaw](https://tashan.sh/capability/plugin-statsclaw-statsclaw-statsclaw.html) | 43 | 87 ★ | active |
| 6 | [Claude Relay](https://tashan.sh/capability/plugin-innestic-claude-relay-claude-relay.html) | 41 | 62 ★ | active |
| 7 | [Twining](https://tashan.sh/capability/plugin-daveangulo-twining-mcp-twining.html) | 41 | 7 ★ | active |
| 8 | [Mistral](https://tashan.sh/capability/plugin-swih-mistral-mcp-mistral-mcp.html) | 38 | 14 ★ | active |
| 9 | [Artel](https://tashan.sh/capability/plugin-nicolasprimeau-artel-artel.html) | 36 | 7 ★ | active |
| 10 | [Praxis · xD4O](https://tashan.sh/capability/plugin-xd4o-praxis-praxis.html) | 35 | 27 ★ | active |
| 11 | [Eve](https://tashan.sh/capability/pkg-eve.html) | 86 | 2m/wk | active |
| 12 | [Handler](https://tashan.sh/capability/pkg-mcp-handler.html) | 85 | 2.1m/wk | active |
| 13 | [Use · mcp-use](https://tashan.sh/capability/pkg-mcp-use.html) | 83 | 46k/wk | active |
| 14 | [Ts Core](https://tashan.sh/capability/pkg-cyanheads-mcp-ts-core.html) | 73 | 17k/wk | active |
| 15 | [Mem0](https://tashan.sh/capability/plugin-mem0ai-mem0-mem0.html) | 70 | 62k ★ | active |
| 16 | [Atomic Agents](https://tashan.sh/capability/plugin-brainblend-ai-atomic-agents-atomic-agents.html) | 69 | 6k ★ | active |
| 17 | [Harness](https://tashan.sh/capability/plugin-revfactory-harness-harness.html) | 69 | 9k ★ | active |
| 18 | [Outputai](https://tashan.sh/capability/plugin-growthxai-output-outputai.html) | 61 | 426 ★ | active |
| 19 | [Create MCP Use App](https://tashan.sh/capability/pkg-create-mcp-use-app.html) | 57 | 132/wk | active |
| 20 | [Keryx · actionhero](https://tashan.sh/capability/pkg-keryx.html) | 56 | 648/wk | active |
| 21 | [Agentforce Adlc](https://tashan.sh/capability/plugin-salesforceairesearch-agentforce-adlc-agentforce-adlc.html) | 55 | 93 ★ | active |
| 22 | [Motus](https://tashan.sh/capability/plugin-lithos-ai-motus-motus.html) | 55 | 482 ★ | active |
| 23 | [Prjct CLI](https://tashan.sh/capability/pkg-prjct-cli.html) | 54 | 702/wk | active |
| 24 | [Claude Code Hermit](https://tashan.sh/capability/plugin-gtapps-claude-code-hermit-claude-code-hermit.html) | 52 | 68 ★ | active |
| 25 | [Clawcode](https://tashan.sh/capability/plugin-crisandrews-clawcode-clawcode.html) | 49 | 61 ★ | active |
| 26 | [Network AI](https://tashan.sh/capability/plugin-jovancoding-network-ai-network-ai.html) | 48 | 70 ★ | active |
| 27 | [Equilateral Agents Open Core](https://tashan.sh/capability/plugin-equilateral-ai-equilateral-agents-open-core-equilateral-agents-open-core.html) | 48 | 59 ★ | active |
| 28 | [Gangsta](https://tashan.sh/capability/plugin-kucherenko-gangsta-gangsta.html) | 47 | 67 ★ | active |
| 29 | [Claude Session Driver](https://tashan.sh/capability/plugin-obra-claude-session-driver-claude-session-driver.html) | 47 | 101 ★ | active |
| 30 | [Parser](https://tashan.sh/capability/pkg-mcp-parser.html) | 45 | 782/wk | active |
| 31 | [Forge](https://tashan.sh/capability/plugin-jdforsythe-forge-forge.html) | 43 | 149 ★ | active |
| 32 | [LLM Gateway](https://tashan.sh/capability/plugin-verivus-oss-llm-cli-gateway-llm-gateway.html) | 42 | 10 ★ | active |
| 33 | [Atelier Pipeline](https://tashan.sh/capability/plugin-robertsfeir-atelier-pipeline-atelier-pipeline.html) | 41 | 23 ★ | active |
| 34 | [Composio](https://tashan.sh/capability/plugin-composiohq-composio-plugin-cc-composio-mcp.html) | 41 | 7 ★ | active |
| 35 | [Agent Social](https://tashan.sh/capability/plugin-2389-research-mcp-socialmedia-mcp-agent-social.html) | 41 | 14 ★ | active |
| 36 | [Concordia Protocol](https://tashan.sh/capability/plugin-eriknewton-concordia-protocol-concordia-protocol.html) | 38 | 3 ★ | active |
| 37 | [Jetty](https://tashan.sh/capability/plugin-jettyio-jettyio-skills-jetty.html) | 38 | 3 ★ | active |
| 38 | [Mnemopay](https://tashan.sh/capability/plugin-mnemopay-mnemopay-sdk-mnemopay.html) | 38 | 6 ★ | active |
| 39 | [Claudelance Worker](https://tashan.sh/capability/plugin-yeheskieltame-claudelance-claudelance-worker.html) | 38 | 4 ★ | active |
| 40 | [Sema](https://tashan.sh/capability/plugin-emergent-wisdom-sema-sema.html) | 37 | 9 ★ | active |

Showing the top 40 of 554. The full ranked shelf is at https://tashan.sh/task/agent-development.html.

## What these numbers are not

- The tashan score measures upkeep, freshness and adoption. It is **not** a security
  verdict and **not** a measure of whether the capability works well.
- `not scored` means too little public evidence to rank, never that something is bad.
- The security audit is separate and free per capability, on each page above.
