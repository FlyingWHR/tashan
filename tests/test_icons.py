#!/usr/bin/env python3
"""Every taxonomy id has an icon, and no icon is invisible at the size it ships.

Four of the first 39 rendered as nothing, and none of it showed up as an error — the symbols existed,
the <use> refs resolved, the boxes measured 18x18, and the paths had valid geometry. They were simply
not visible:

  cat-other, role-Also        `M6 12h.01` — a zero-length subpath that draws only if the engine
                              honours round caps on it. Total path length: 0.03 units.
  cat-data, role-data-analyst purely axis-aligned thin lines. A 2.25 stroke on a 24 grid at 18px is
                              1.69 device pixels; on an integer coordinate it straddles two pixel
                              columns and anti-aliases to half intensity in each. The bar chart had
                              MORE path length (53 units) than the clearly-visible chevrons (33).

So "the symbol exists" is not the property worth testing. These are.

Run: python3 tests/test_icons.py
"""
import json, os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import icons

fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


NUM = re.compile(r"-?\d+(?:\.\d+)?")


def span(d):
    """Crude extent of a path in grid units. Enough to catch a mark too small to see."""
    xs = [float(n) for n in NUM.findall(d)]
    return (max(xs) - min(xs)) if xs else 0


# ---- coverage: the taxonomies drive the icon set, not the other way round -----------------------
cats = [c["id"] for c in json.load(open(os.path.join(ROOT, "web", "data", "categories.json")))["categories"]]
roles = [r["id"] for r in json.load(open(os.path.join(ROOT, "web", "data", "tasks.json")))["roles"]]

missing_cat = [c for c in cats if c not in icons.CATEGORY]
missing_role = [r for r in roles if r not in icons.ROLE]
ok(f"every one of the {len(cats)} categories has an icon", not missing_cat, ", ".join(missing_cat))
ok(f"every one of the {len(roles)} job roles has an icon", not missing_role, ", ".join(missing_role))
ok("the merged 'Also' group on /browse.html has one", "Also" in icons.ROLE)

# ---- visibility --------------------------------------------------------------------------------
zero = [n for n, d in icons.all_icons().items() if re.search(r"[hv]\s*-?0?\.0\d", d)]
ok("no icon relies on a zero-length subpath to be visible", not zero, ", ".join(zero))

tiny = [n for n, d in icons.all_icons().items() if span(d) < 8]
ok("no icon is smaller than a third of the grid", not tiny,
   ", ".join(f"{n} spans {span(icons.all_icons()[n]):.0f}u" for n in tiny))

# an icon made ONLY of axis-aligned segments is the anti-aliasing trap; it needs enough marks to
# survive it, which outlined shapes have and three bare lines do not
def axis_only(d):
    """True only when every drawn segment is horizontal or vertical.

    "M4 12.5 9 17.5 20 6.5" is a move plus two IMPLICIT linetos — a check mark, all diagonal. An
    earlier version of this looked for explicit L commands, found none, and reported the most
    obviously visible icon in the set as an invisibility risk.
    """
    if re.search(r"[aAcCqQsStT]", d):
        return False                       # any curve
    if re.search(r"[lL]", d):
        return False                       # explicit lineto
    for seg in re.findall(r"[Mm]([^A-Za-z]*)", d):
        if len(NUM.findall(seg)) > 2:      # more than one coordinate pair => implicit linetos
            return False
    return True


thin_axis = [n for n, d in icons.all_icons().items()
             if axis_only(d) and len(re.findall(r"[MmHhVvLl]", d)) < 6]
ok("no icon is a handful of bare axis-aligned strokes", not thin_axis, ", ".join(thin_axis))

# ---- the sprite ---------------------------------------------------------------------------------
sprite_path = os.path.join(ROOT, "web", "assets", "icons.svg")
if os.path.exists(sprite_path):
    raw = open(sprite_path, encoding="utf-8").read()
    try:
        ET.fromstring(raw)
        ok("the sprite is well-formed XML", True)
    except ET.ParseError as e:
        ok("the sprite is well-formed XML", False, str(e))
    ok(f"the sprite carries all {len(icons.all_icons())} symbols",
       raw.count("<symbol") == len(icons.all_icons()),
       f"{raw.count('<symbol')} in the file")
    ok("the sprite is regenerated, not stale",
       all(f'id="i-{n}"' in raw for n in icons.all_icons()),
       "run python3 pipeline/icons.py")
    ok("the sprite stays small enough to inline on every page", len(raw) < 12000,
       f"{len(raw)} bytes")
else:
    ok("web/assets/icons.svg exists", False, "run python3 pipeline/icons.py")

# ---- inlined, and referenced ---------------------------------------------------------------------
idx = os.path.join(ROOT, "web", "index.html")
if os.path.exists(idx):
    src = open(idx, encoding="utf-8").read()
    ok("the sprite is inlined on the Index (external <use> loses currentColor in Safari)",
       'class="icon-sprite"' in src, "run pipeline/bump_assets.py")
    ok("no un-substituted <!--ICONS--> marker was shipped", "<!--ICONS-->" not in src)

print("ICONS FAILED" if fail else "ok — icons (coverage + visible at ship size)")
sys.exit(fail)
