"""Check rendered public copy, including escaped text in machine-readable exports."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from build import HAN_TEXT

for path in (ROOT / "web").rglob("*"):
    if path.suffix not in {".html", ".json", ".txt", ".md", ".js", ".css", ".svg", ".xml"} and path.parent.name != "v0.1":
        continue
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    if (path.suffix == ".json" or path.parent.name == "v0.1") and "\\u" in text:
        text = json.dumps(json.loads(text), ensure_ascii=False)
    if HAN_TEXT.search(text):
        raise SystemExit(f"Unexpected Han text in {path.relative_to(ROOT)}")
print("ok — public pages and agent exports are free of Han text")
