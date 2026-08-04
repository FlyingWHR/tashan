# Claude Video Vision

> A perception layer that gives Claude Code the ability to watch and understand videos. Extracts frames via ffmpeg and processes audio through multiple configurable backends (Gemini API, local Whisper, or OpenAI Whisper API). Claude receives the frames as images plus an audio transcription with timestamps and reasons about them together. Includes an interactive setup wizard, adaptive extraction (fps, resolution, and time ranges automatically adjust to the user's question), and auto-download of Whi

## Facts
- Page: https://tashan.sh/capability/plugin-jordanrendric-claude-video-vision-claude-video-vision
- tashan id: plugin:jordanrendric/claude-video-vision/claude-video-vision
- Source: https://github.com/jordanrendric/claude-video-vision
- Type: plugin
- Category: productivity
- tashan score: 71.0 / 100
- Adoption: 46.0
- Upkeep: 95.0
- Freshness: 89.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: deep
- GitHub stars: 1,044
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-video-vision@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
