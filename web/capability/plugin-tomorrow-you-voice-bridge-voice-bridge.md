# Voice Bridge

> Give Claude Code a voice with multi-engine text-to-speech. Speaks responses aloud using 5 TTS engines (edge-tts, ElevenLabs, Kokoro, macOS say, espeak-ng). Free by default. edge-tts uses Microsoft Neural voices with no API key. Includes a Stop hook for automatic speech, a /speak skill for on-demand use, and an MCP server with speak, setengine, getstatus, and listvoices tools. Text is automatically filtered to remove code blocks, API keys, file paths, and markdown before speaking.

## Facts
- Page: https://tashan.sh/capability/plugin-tomorrow-you-voice-bridge-voice-bridge
- tashan id: plugin:tomorrow-you/voice-bridge/voice-bridge
- Source: https://github.com/Tomorrow-You/voice-bridge
- Type: plugin
- Category: productivity
- tashan score: 27.0 / 100
- Adoption: 7.0
- Upkeep: 50.0
- Freshness: 70.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 0
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install voice-bridge@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
