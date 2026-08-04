#!/usr/bin/env python3
"""Every text colour token must be readable on the background it is used against.

WHY THIS EXISTS. An external audit measured `--text-faint` at roughly rgb(87,86,79) on the near-black
background — 2.67:1, against WCAG AA's 4.5:1 for body text — and it was right to the exact hex. That
token is used 79 times, and what it carries is the qualifying text: evidence counts, measurement
dates, "not yet graded", "not scanned yet", the coverage caveats under a score. On a site whose whole
claim is that it tells you what it does and does not know, the caveats were the least legible text on
the page.

Contrast is arithmetic, so it does not need an eye or a browser — it needs a test. Colours drift when
someone nudges a token to taste; this fails the build instead of waiting for the next audit.

Run: python3 tests/test_a11y_contrast.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "web", "css", "site.css")
AA_BODY, AA_LARGE = 4.5, 3.0
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def rgb(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


css = open(CSS, encoding="utf-8").read()


def token(name):
    m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{3,6}})", css)
    return rgb(m.group(1)) if m else None


bg = token("bg")
if bg is None:
    print("  FAIL could not read --bg from site.css")
    sys.exit(1)

print(f"# text tokens against --bg #{''.join(f'{c:02x}' for c in bg)}")
# --text-faint is BODY text (captions, counts, dates), not decorative, so it takes the 4.5:1 bar.
for name, floor, why in (
    ("text", AA_BODY, "primary copy"),
    ("text-dim", AA_BODY, "secondary copy"),
    ("text-faint", AA_BODY, "captions, counts, dates, coverage caveats — 79 uses"),
):
    c = token(name)
    if c is None:
        continue
    r = ratio(c, bg)
    ok(f"--{name} is {r:.2f}:1 (>= {floor} for {why})", r >= floor,
       f"#{''.join(f'{x:02x}' for x in c)} is {r:.2f}:1 — below WCAG AA")

# The accent carries scores and links; it only ever appears at >=14px semibold or larger, so it is
# held to the large-text bar rather than the body one.
acc = token("jade") or token("accent")
if acc:
    r = ratio(acc, bg)
    ok(f"accent is {r:.2f}:1 (>= {AA_LARGE} for large/semibold text)", r >= AA_LARGE)

print()
print("CONTRAST OK" if not fail else "CONTRAST FAILED")
sys.exit(fail)
