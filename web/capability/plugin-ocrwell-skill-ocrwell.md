# Ocrwell

> Teaches Claude Code the OCRWell document OCR API so it generates correct integration code without having to be fed documentation. The agent learns the /v1 endpoints, the two-step upload flow (create upload → PUT to presigned URL → create document), asynchronous job polling with backoff, both structured-extraction schema formats (template and JSON Schema), the full error catalogue, rate-limit headers, and HMAC-SHA256 webhook signature verification. It also knows the quiet gotchas, like treating a

## Facts
- Page: https://tashan.sh/capability/plugin-ocrwell-skill-ocrwell
- tashan id: plugin:ocrwell/skill/ocrwell
- Source: https://github.com/ocrwell/skill
- Type: plugin
- Category: comms
- tashan score: 27.0 / 100
- Adoption: 7.0
- Upkeep: 50.0
- Freshness: 68.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install ocrwell@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
