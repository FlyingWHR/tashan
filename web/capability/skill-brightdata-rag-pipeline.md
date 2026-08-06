# RAG Pipeline

> | Build a RAG (retrieval-augmented generation) pipeline or a custom search engine on top of Bright Data's Discover API — using intent-ranked web results + parsed page content as the retrieval/ingestion layer for an LLM or vector store. Use when the user wants to "build a RAG pipeline", "add web search to my LLM/agent", "ground my model in live web data", "build a search engine over the web", "ingest web content into a vector DB / knowledge base", or "give my chatbot retrieval". Covers both live retrieval (Discover at query time as a web-grounded retriever) and ingestion (Discover → chunk → embed → vector store → retrieve). Built on the discover-api skill. For a one-off written report use live-research; for raw markdown of specific known URLs use scrape.

## Facts
- Page: https://tashan.sh/capability/skill-brightdata-rag-pipeline
- tashan id: skill:brightdata/rag-pipeline
- Source: https://github.com/brightdata/skills
- Type: skill
- Category: search
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: 93.0
- Freshness: 86.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- License: MIT
- Official: no

## Install

```sh
cp -r rag-pipeline ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
