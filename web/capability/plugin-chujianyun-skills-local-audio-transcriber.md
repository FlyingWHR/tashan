# Local Audio Transcriber

> 本地录音转文字工具。当用户发送已有录音、音频或视频文件，并希望把语音转成 Markdown 文稿和 SRT 字幕时使用。Apple Silicon 优先用 MLX/Apple GPU 和 whisper-large-v3-turbo-q4，本地转写，不生成 txt/json/vtt，不用于现场临时录音，也不默认调用云端语音识别服务。

## Facts
- Page: https://tashan.sh/capability/plugin-chujianyun-skills-local-audio-transcriber
- tashan id: plugin:chujianyun/skills/local-audio-transcriber
- Source: https://github.com/chujianyun/skills
- Type: plugin
- Category: other
- tashan score: 40.0 / 100
- Adoption: 7.0
- Upkeep: 81.0
- Freshness: 98.0
- Evidence coverage: 84% of the inputs this score can use
- Health: active
- Instruction depth: thin
- License: NOASSERTION
- Official: no

## Install

```sh
/plugin marketplace add chujianyun/skills
/plugin install local-audio-transcriber@wuming-skills
```

## Security audit
Not scanned. We audit npm-published capabilities; this one has no npm package we can resolve, or has not reached the queue. This is not a clean bill of health.

---
Measured 2026-08-03 by tashan (https://tashan.sh) from public evidence. Scorer s5.
