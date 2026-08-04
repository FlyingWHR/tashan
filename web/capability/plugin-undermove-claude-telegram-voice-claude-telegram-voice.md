# Claude Telegram Voice

> Voice message transcription for the Telegram channel plugin. When a user sends a voice message, the plugin instructs Claude to automatically download the audio file and transcribe it using a user-configured command (OpenAI Whisper, faster-whisper, whisper.cpp, OpenAI API, or any custom script). Claude then receives the spoken text and responds as if the user typed it. Tool-agnostic: any command that reads an audio file and prints text to stdout works. No modifications to the official Telegram pl

## Facts
- Page: https://tashan.sh/capability/plugin-undermove-claude-telegram-voice-claude-telegram-voice
- tashan id: plugin:undermove/claude-telegram-voice/claude-telegram-voice
- Source: https://github.com/Undermove/claude-telegram-voice
- Type: plugin
- Category: productivity
- tashan score: 28.0 / 100
- Adoption: 11.0
- Upkeep: 48.0
- Freshness: 65.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: not yet graded
- GitHub stars: 1
- License: MIT
- Official: no

## Install

```sh
/plugin marketplace add anthropics/claude-plugins-community
/plugin install claude-telegram-voice@claude-community
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-04 by tashan (https://tashan.sh) from public evidence. Scorer s5.
