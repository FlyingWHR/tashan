"""Check rendered public copy, including escaped text in machine-readable exports."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from build import HAN_TEXT, public_copy

sample = {"tasks": [{"t": "agent-development", "e": "运行模型"}, {"t": "testing", "e": "run tests"}]}
public_copy(sample)
assert sample["tasks"] == [{"t": "agent-development", "e": None}, {"t": "testing", "e": "run tests"}]

for path in (ROOT / "web").rglob("*"):
    if path.suffix not in {".html", ".json", ".txt", ".md", ".js", ".css", ".svg", ".xml"} and path.parent.name != "v0.1":
        continue
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    if (path.suffix == ".json" or path.parent.name == "v0.1") and "\\u" in text:
        text = json.dumps(json.loads(text), ensure_ascii=False)
    match = HAN_TEXT.search(text)
    if match:
        context = text[max(0, match.start() - 85):match.end() + 65]
        raise SystemExit(f"Unexpected Han text in {path.relative_to(ROOT)} near {context!r}")
print("ok — public pages and agent exports are free of Han text")
