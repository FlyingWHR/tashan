#!/usr/bin/env python3
"""tashan — bump the asset version everywhere, then regenerate. One command, no hand-editing.

    python3 pipeline/bump_assets.py            # V+1, rewrite web/*.html, regenerate all pages
    python3 pipeline/bump_assets.py --check    # verify every ?v= on disk agrees with assets.V

Run this after ANY change under web/css/ or web/js/. Forgetting to bump is how stale JS reaches the
browser; doing it by hand across six files is how it gets forgotten. --check is what the test suite
calls so a mismatch fails loudly instead of silently serving a cached file.
"""
import glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import assets

HTML = sorted(glob.glob(os.path.join(ROOT, "web", "*.html")))
GENERATORS = ["prerender.py", "gen_content.py", "gen_hubs.py"]


def versions_on_disk():
    """Every distinct ?v=N found in the hand-written pages and the generated tree."""
    found = {}
    for f in HTML + sorted(glob.glob(os.path.join(ROOT, "web", "*", "*.html"))):
        for m in re.finditer(r"\?v=(\d+)", open(f).read()):
            found.setdefault(int(m.group(1)), []).append(os.path.relpath(f, ROOT))
    return found


def check():
    found = versions_on_disk()
    if not found:
        print("no versioned assets found"); return 0
    if set(found) == {assets.V}:
        n = sum(len(v) for v in found.values())
        print(f"ok — every ?v= on disk is v={assets.V} ({n} references)")
        return 0
    print(f"MISMATCH — assets.V is {assets.V} but disk has {sorted(found)}")
    for v, files in sorted(found.items()):
        if v != assets.V:
            print(f"  v={v}: {len(files)} refs, e.g. {files[0]}")
    print("  fix: python3 pipeline/bump_assets.py")
    return 1


def bump():
    old, new = assets.V, assets.V + 1
    p = os.path.join(ROOT, "pipeline", "assets.py")
    s = open(p).read()
    open(p, "w").write(re.sub(r"^V = \d+$", "V = %d" % new, s, count=1, flags=re.M))
    for f in HTML:
        s = open(f).read()
        o = re.sub(r"\?v=\d+", "?v=%d" % new, s)
        if o != s:
            open(f, "w").write(o)
    print(f"asset version {old} -> {new}  ({len(HTML)} pages + generators)")
    for g in GENERATORS:
        gp = os.path.join(ROOT, "pipeline", g)
        if not os.path.exists(gp):
            continue
        r = subprocess.run([sys.executable, gp], capture_output=True, text=True)
        tail = (r.stdout or r.stderr).strip().splitlines()
        print(f"  {g}: {tail[-1] if tail else 'ok'}")
    return 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else bump())
