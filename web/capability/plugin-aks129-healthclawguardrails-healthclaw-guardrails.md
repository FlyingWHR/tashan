# Healthclaw Guardrails

> HealthClaw Guardrails is the security layer between AI agents and clinical FHIR data. Every agent read passes through PHI redaction (names truncated to initials, DOBs to year, identifiers masked). Every write requires an HMAC-signed step-up token with a 5-minute TTL. Clinical writes (Condition, MedicationRequest, DiagnosticReport) return HTTP 428 until a human confirms. Every access lands in an append-only audit trail scoped by tenant. Supports FHIR R4 US Core v9 (stable) and FHIR R6 v6.0.0-bal

## Facts
- Page: https://tashan.sh/capability/plugin-aks129-healthclawguardrails-healthclaw-guardrails
- tashan id: plugin:aks129/healthclawguardrails/healthclaw-guardrails
- Source: https://github.com/aks129/HealthClawGuardrails
- Type: plugin
- Category: security
- tashan score: 61.0 / 100
- Adoption: 26.0
- Upkeep: 99.0
- Freshness: 97.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: solid
- GitHub stars: 27
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install healthclaw-guardrails@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
