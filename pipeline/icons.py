#!/usr/bin/env python3
"""One definition of every category and job-role icon, emitted to both surfaces that need it.

    python3 pipeline/icons.py

The rail is rendered by JavaScript and the hubs are rendered by Python. Defining the icons twice is
exactly the shape of bug this codebase kept producing all week — a label that disagreed with the
board, a sort reading a renamed column, a hub table with a different row anatomy. So the paths live
here once and are written out to:

    web/assets/icons.svg   the sprite, inlined once per page that uses icons

The JS rail does NOT need a copy of the path data: it emits `<use href="#i-cat-search">` and the
inlined sprite supplies the geometry. That keeps this the single definition rather than one-plus-a-
mirror, which is the arrangement that has gone wrong repeatedly in this codebase.

tests/test_icons.py asserts every taxonomy id has an icon and every icon is referenced.

AXIS-ALIGNED THIN LINES ARE A TRAP. A 2.25 stroke on a 24 grid drawn at 18px is 1.69 device pixels;
placed on an integer coordinate it straddles two pixel columns and anti-aliases to half intensity in
each, so it disappears while a diagonal of the SAME path length stays crisp. The bar chart measured
53 units of length against the visible chevrons' 33 and was still invisible. Give axis-aligned marks
more mass (outline the bars) and sit them on half-integer coordinates.

DESIGN: 24x24 grid, stroke-only, `currentColor`, weight 2, round caps. Weight 2 rather than
1.75 because these render at 16-18px: on a 24-unit grid that is 1.17 device pixels at 1.75, which
greys out to almost nothing against a dark background. Stroke rather than fill so
one icon works on the board, in a jade-accented chip and on a dark card without three variants. No
emoji: they are colour images the theme cannot control, they render differently on every platform,
and this project already learned that non-ASCII glyphs turn into tofu in the wrong font.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- the 15 domain categories (web/data/categories.json) ---------------------------------------
CATEGORY = {
    "browser":      "M3 6h18v13H3z M3 10h18 M6 8h1 M8.5 8h1",                    # browser window
    "search":       "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M16.5 16.5 21 21",           # magnifier
    "database":     "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3 M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6 M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
    "devtools":     "m7 8-4 4 4 4 M13 7l-2 10 M17 8l4 4-4 4",                          # </> chevrons
    "cloud":        "M7 18h10a4 4 0 0 0 .6-7.96 6 6 0 0 0-11.48 1.7A3.5 3.5 0 0 0 7 18Z",
    "files":        "M4 7a2 2 0 0 1 2-2h3l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z",
    "data":         "M2.5 20.5h19 M5.5 20.5v-6h3v6 M11.5 20.5v-11h3v11 M17.5 20.5v-8h3v8",  # outlined bars
    "docs":         "M4 5a2 2 0 0 1 2-2h9l5 5v13H6a2 2 0 0 1-2-2Z M15 3v5h5 M8 13h8 M8 17h5",
    "comms":        "M4 5h16v11H9l-5 4Z M8 9h8 M8 12h5",                               # speech bubble
    "design":       "m5 19 4-1 9.5-9.5a2.1 2.1 0 0 0-3-3L6 15Z M14.5 6.5l3 3",         # pen nib
    # A ring with six 2px spokes collapsed into a dot at 18px. The sparkle is the conventional mark
    # and survives the size, which is the only test that matters for a 16-18px icon.
    "ai":           "M11 3.5 13 8.5 18 10.5 13 12.5 11 17.5 9 12.5 4 10.5 9 8.5Z M18 15.5l1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1Z",
    "finance":      "M12 3v18 M16.5 7.5c0-1.9-2-3-4.5-3s-4.5 1.1-4.5 3 2 2.8 4.5 3.3 4.5 1.4 4.5 3.2-2 3-4.5 3-4.5-1.1-4.5-3",
    "productivity": "M4 12.5 9 17.5 20 6.5",                                            # check
    "security":     "M12 3 20 6v6c0 4.5-3.3 7.9-8 9-4.7-1.1-8-4.5-8-9V6Z M9 12l2 2 4-4",
    # not h.01 dots: a zero-length subpath renders only if the engine honours round caps on
    # it, and these two icons were staking their whole visibility on that bet.
    # 3-unit dashes are a 2px mark at ship size — still invisible. Circles carry curvature,
    # so they never straddle a pixel boundary the way a short axis-aligned dash does.
    "other":        "M4.6 12.5a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 1 0-2.8 0 M10.6 12.5a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 1 0-2.8 0 M16.6 12.5a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 1 0-2.8 0",
}

# ---- job roles (web/data/tasks.json). "Also" is the trailing merged group on /browse.html -------
ROLE = {
    # an agent operator runs the agent itself: a terminal prompt
    "agent-operator": "M3.5 5.5h17v13h-17Z M7 10l2.5 2.5L7 15 M12.5 15.5h4",
    "engineer":     "m7 8-4 4 4 4 M13 7l-2 10 M17 8l4 4-4 4",
    "ops":          "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6 M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3 14.6H3a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4.6 7a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9 3.6V3a2 2 0 1 1 4 0v.1A1.6 1.6 0 0 0 15 4.6",
    "pm":           "M4 4h16v16H4z M9 4v16 M14 8h4 M14 12h4",                           # board
    "marketer":     "M4 10v4h3l6 4V6L7 10Z M17 9a4 4 0 0 1 0 6",                        # megaphone
    "ai-engineer":  "M9 4h6v3h3v10h-3v3H9v-3H6V7h3Z M9.5 10.5h5v3h-5Z",                 # chip
    "designer":     "m5 19 4-1 9.5-9.5a2.1 2.1 0 0 0-3-3L6 15Z M14.5 6.5l3 3",
    "data-analyst": "M2.5 20.5h19 M5.5 20.5v-6h3v6 M11.5 20.5v-11h3v11 M17.5 20.5v-8h3v8",
    "writer":       "M4 20h16 M6 16 16.5 5.5a2.1 2.1 0 0 1 3 3L9 19l-4 1Z",
    "researcher":   "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M16.5 16.5 21 21 M8 11h6 M11 8v6",
    "creator":      "M3 6h18v12H3z M3 9h18 M9 12l4 2.5L9 17Z",                          # film / play
    "legal":        "M12 4v16 M6 20h12 M4 9h16 M7 9l-3 5h6Zm10 0-3 5h6Z",               # scales
    "hr":           "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6 M3 20a6 6 0 0 1 12 0 M17 8a2.5 2.5 0 1 0 0-5 M17 12a5 5 0 0 1 4 8",
    "devops":       "M4 6h16v4H4z M4 14h16v4H4z M7 8h1 M7 16h1",                # stacked servers
    "finance":      "M12 3v18 M16.5 7.5c0-1.9-2-3-4.5-3s-4.5 1.1-4.5 3 2 2.8 4.5 3.3 4.5 1.4 4.5 3.2-2 3-4.5 3-4.5-1.1-4.5-3",
    "data-engineer": "M4 7h6a2 2 0 0 1 2 2v6a2 2 0 0 0 2 2h6 M17 4l3 3-3 3 M17 14l3 3-3 3",  # pipeline
    "security":     "M12 3 20 6v6c0 4.5-3.3 7.9-8 9-4.7-1.1-8-4.5-8-9V6Z M9 12l2 2 4-4",
    "web-dev":      "M3 6h18v13H3z M3 10h18 M6 8h1 M8.5 8h1",
    "support":      "M4 5h16v11H9l-5 4Z M12 8v3 M11.6 13h.8",
    "sales":        "M4 17 10 11l3 3 7-7 M14 7h6v6",                                    # trend up
    "educator":     "M3 8 12 4l9 4-9 4Z M7 11v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5v-5",    # mortarboard
    "scientist":    "M9 3v6l-5 9a2 2 0 0 0 1.8 3h12.4a2 2 0 0 0 1.8-3l-5-9V3 M8 3h8 M8 14h8",
    "hardware":     "M9 4h6v3h3v10h-3v3H9v-3H6V7h3Z M9.5 10.5h5v3h-5Z",
    "creator-video": "M3 6h18v12H3z M3 9h18 M9 12l4 2.5L9 17Z",
    "Also":         "M4.6 12.5a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 1 0-2.8 0 M10.6 12.5a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 1 0-2.8 0 M16.6 12.5a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 1 0-2.8 0",
}

# UI glyphs, as opposed to taxonomy marks. Rendered inline by chrome.py rather than through the
# sprite, because the nav appears on pages that do not carry one.
UI = {
    "account": "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M4.5 20a7.5 7.5 0 0 1 15 0",
}


STYLE = ('fill="none" stroke="currentColor" stroke-width="2.25" '
         'stroke-linecap="round" stroke-linejoin="round"')


def paths(prefix, table):
    return {prefix + k: v for k, v in table.items()}


def all_icons():
    out = paths("cat-", CATEGORY)
    out.update(paths("role-", ROLE))
    out.update(paths("ui-", UI))
    return out


def sprite():
    """One <svg> block of <symbol>s, inlined into a page once and referenced with <use>."""
    # STYLE GOES ON THE SYMBOL, NEVER ON THE SPRITE ROOT. <use> clones the referenced element into a
    # shadow tree under the <use>, and inherited properties (fill, stroke, stroke-width) resolve
    # against the REFERENCING element's ancestors, not the sprite's. With the paint on the root svg,
    # every icon on the site inherited nothing and fell back to the SVG defaults — fill:black,
    # stroke:none — so all 39 rendered as a solid black blob on a black page. Nothing errored: the
    # symbols existed, the refs resolved, the boxes measured 17x17, and the sprite itself looked
    # correct when opened on its own. tests/test_icons.py asserts the attributes are on the symbols.
    #
    # One <path> per icon: the d attribute already supports multiple subpaths via M, so splitting
    # them into separate elements would triple the sprite for no rendering difference.
    syms = [f'<symbol id="i-{name}" viewBox="0 0 24 24" {STYLE}><path d="{d}"/></symbol>'
            for name, d in all_icons().items()]
    return '<svg class="icon-sprite" aria-hidden="true">' + "".join(syms) + "</svg>"


def use(name, cls="icon"):
    """The reference. aria-hidden because every icon here sits beside its own text label."""
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{name}"/></svg>'


def main():
    icons = all_icons()
    os.makedirs(os.path.join(ROOT, "web", "assets"), exist_ok=True)
    open(os.path.join(ROOT, "web", "assets", "icons.svg"), "w").write(sprite())

    print(f"  {len(CATEGORY)} category + {len(ROLE)} role icons "
          f"-> web/assets/icons.svg ({os.path.getsize(os.path.join(ROOT, 'web', 'assets', 'icons.svg'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
