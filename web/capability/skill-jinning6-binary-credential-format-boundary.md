# Binary Credential Format Boundary

> Audit and repair readers for fixed-length binary credentials and their text encodings without mutating raw bytes. Use when code loads Ed25519/X25519 keys, nonces, digests, MAC keys, signatures, tokens, or other opaque bytes from files or environment values; when .strip(), decoding, newline handling, or format auto-detection occurs before length/type validation; or when cryptographic tests fail intermittently for otherwise valid generated material.

## Facts
- Page: https://tashan.sh/capability/skill-jinning6-binary-credential-format-boundary
- tashan id: skill:JinNing6/binary-credential-format-boundary
- Source: https://github.com/JinNing6/Noosphere
- Type: skill
- Category: security
- tashan score: not scored (catalogued only — too little public evidence)
- Adoption: 9.0
- Upkeep: not measured
- Freshness: not measured
- Evidence coverage: not measured
- Health: not measured
- Instruction depth: not yet graded
- Official: no

## Install

```sh
cp -r binary-credential-format-boundary ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-05 by tashan (https://tashan.sh) from public evidence. Scorer s5.
