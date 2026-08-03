# Kakao Setup

> Set up KakaoTalk integration prerequisites for /logblog:kakao-post on macOS. Installs kakaocli via Homebrew, walks through Xcode + Full Disk Access requirements, derives the KAKAOCLIKEY (SQLCipher DB decryption key) via auto-auth or SHA-512 brute-force fallback, persists the key to the user's shell rc file, optionally installs the kakaotalk-chat-analyzer wrapper, and verifies the full chain. Use before the first /logblog:kakao-post run on a new machine, or when KAKAOCLIKEY is missing or stale.

## Facts
- Page: https://tashan.sh/capability/skill-ice-ice-bear-kakao-setup
- tashan id: skill:ice-ice-bear/kakao-setup
- Source: https://github.com/ice-ice-bear/log-blog
- Type: skill
- Category: other
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
cp -r kakao-setup ~/.claude/skills/
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
