# Claude API

> |- Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration. TRIGGER — read BEFORE opening the target file; don't skip because it "looks like a one-liner" — whenever: the prompt names Claude/Anthropic in any form (Claude, Anthropic, Fable, Opus, Sonnet, Haiku, anthropic, @anthropic-ai, claude-, us.anthropic., [1m]); the user asks about an LLM (pricing/model choice/limits/caching) — never answer from memory; OR the task is LLM-shaped with provider unstated (agent/MCP/tool-definition/multi-agent/RAG/LLM-judge/computer-use; generate/summarize/extract/classify/rewrite/converse over NL; debugging refusals/cutoffs/streaming/tool-calls/tokens). SKIP only when another provider is being worked on (overrides all triggers): OpenAI/GPT/Gemini/Llama/Mistral/Cohere/Ollama named in the query; OR grep -rE 'openai|langchainopenai|google.generativeai|genai|mistralai|cohere|ollama' over the project hits (run this grep FIRST if no provider named — don't Read the file).

## Facts
- Page: https://tashan.sh/capability/skill-anthropics-claude-api
- tashan id: skill:anthropics/claude-api
- Source: https://github.com/anthropics/skills
- Type: skill
- Category: ai
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 98.0
- Freshness: 96.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- Official: yes

## Install

```sh
cp -r claude-api ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
