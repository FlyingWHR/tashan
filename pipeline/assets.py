#!/usr/bin/env python3
"""tashan — THE asset cache-busting version, in one place.

Every reference to `?v=N` across the site must move in lockstep or browsers keep serving stale JS/CSS
(the local dev server sends no cache headers at all). Keeping the number in six files was a documented
footgun and it fired repeatedly — a shipped hoisting bug and a whole round of "the fix didn't work"
debugging both traced back to a missed bump.

So: this module is the source of truth. The generators import V; the hand-written pages in web/*.html
are rewritten by `python3 pipeline/bump_assets.py`, which also re-runs every generator. Never edit a
`?v=` by hand again — run the bump script.
"""

V = 281


def q():
    """Query suffix for a versioned asset: /css/site.css<q()>"""
    return "?v=%d" % V
