#!/usr/bin/env python3
"""Generate embeddable SVG badges per ranked capability — the PLG loop-1 primitive.
Maintainers embed `https://tashan.sh/badge/<slug>.svg` in their README:
  ![tashan](https://tashan.sh/badge/pkg-upstash-context7-mcp.svg)
Terminal-flavored: near-black + amber, monospace, verdict colored. Static (no server needed)."""
import json, os, re, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "tashan.db")
OUT = os.path.join(ROOT, "web", "badge")
os.makedirs(OUT, exist_ok=True)

VCOLOR = {"deep": "#5cf0c0", "solid": "#34e0a0", "thin": "#8a8a93"}
# The 他山之石 stone, as vector paths — same geometry as web/assets/favicon.svg and the --logo CSS var.
# The badge is the highest cast-range artifact we ship (it renders inside other people's READMEs), so it
# must carry the actual mark, not a generic ◆ that could be anyone's.
MARK = ('<g transform="translate(7,4.2) scale(0.38)">'
        '<path d="M17 4 L23 10 L29 22 L18 28 L5 24 L4 13 Z" fill="#34e0a0"/>'
        '<path d="M17 4 L4 13 L14 15 Z" fill="#5cf0c0"/>'
        '<path d="M17 4 L23 10 L29 22 L18 28 L14 15 Z" fill="#1f9e78"/></g>')
CW = 6.6          # monospace char width at 11px
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

def slug(cid):
    return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def badge(trust, verdict):
    left = "  tashan"          # leading space reserves room for the vector mark
    right_score = str(int(trust))
    right = right_score + ("  " + verdict if verdict else "")
    lw = round(len(left) * CW + 16)
    rw = round(len(right) * CW + 16)
    W, H = lw + rw, 20
    vcol = VCOLOR.get(verdict, "#34e0a0")
    # right text: score in amber, verdict in its color
    if verdict:
        rtext = (f'<tspan fill="#34e0a0">{right_score}</tspan>'
                 f'<tspan fill="#5b5b63">  ·  </tspan><tspan fill="{vcol}">{esc(verdict)}</tspan>')
    else:
        rtext = f'<tspan fill="#34e0a0">{right_score}</tspan>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" role="img" aria-label="tashan: {right_score} {esc(verdict or "")}">
<rect width="{W}" height="{H}" rx="4" fill="#09090b"/>
<rect width="{lw}" height="{H}" rx="4" fill="#18181b"/>
<rect x="{lw-4}" width="4" height="{H}" fill="#18181b"/>
<rect x="{lw}" width="{rw}" height="{H}" rx="4" fill="#0d0d10"/>
<rect x="{lw}" width="4" height="{H}" fill="#0d0d10"/>
<line x1="{lw}" y1="3" x2="{lw}" y2="17" stroke="rgba(233,162,59,.35)"/>
{MARK}<text x="21" y="14" font-family="{MONO}" font-size="11" font-weight="600"><tspan fill="#ededf0">tashan</tspan></text>
<text x="{lw+8}" y="14" font-family="{MONO}" font-size="11" font-weight="600">{rtext}</text>
</svg>'''

def main():
    # The EXPORT, not the DB. The DB is the source of truth for what we have measured; the export is
    # the set we PUBLISH, and export() drops rows the DB still holds — demo servers, the two
    # dependency-confusion canaries, and MAL-* malicious packages that junk() removes from the board
    # entirely. Reading the DB here published 408 badges for capabilities no page exists for, which
    # includes handing a green tashan badge to a package we classified as malicious, embeddable in its
    # own README. A badge is the highest-cast artifact we ship; it must never outrun the board.
    caps = json.load(open(os.path.join(ROOT, "web", "data", "capabilities.json")))["capabilities"]
    # READ the export's slug, never re-derive it. slug(id) is right for almost every row and WRONG for
    # any that lost a collision (`@stripe/mcp` vs `stripe-mcp` both derive to pkg-stripe-mcp), which
    # would hand two capabilities one badge file — the second overwriting the first, so a package
    # could embed a badge showing a DIFFERENT package's score in its own README.
    # NO STATIC .svg FILES. This wrote one badge per scored capability, and that is a file count
    # that grows with the corpus forever: at 6,453 badges the site hit 21,782 files and Cloudflare
    # Pages — which refuses any deployment over 20,000 — would not publish AT ALL. Capping by score
    # bought one release and no more; 4,684 discovered npm packages are still unenriched and each
    # scores once it is.
    #
    # A badge is a pure function of (score, verdict). It does not need to be a file. functions/badge/
    # renders it on demand from the map written here — ONE file instead of thousands, and the route
    # already carries a 1h edge cache so origin hits are rare. Existing embeds keep working: same
    # URLs, same bytes (tests/test_badge_parity.mjs pins the two renderers together).
    rows = [(c["id"], c.get("slug") or slug(c["id"]), c["tashan_score"], c.get("expertise_verdict"))
            for c in caps if c.get("tashan_score") is not None]
    # Compact on purpose: [score, verdict] per slug, verdict omitted when absent. The Function fetches
    # this once per isolate, so its size is a cold-start cost, not a per-request one.
    m = {}
    for cid, sl, trust, verdict in rows:
        m[sl] = [int(trust), verdict] if verdict else [int(trust)]
    out = os.path.join(ROOT, "web", "data", "badges.json")
    json.dump(m, open(out, "w"), separators=(",", ":"), sort_keys=True)
    # Remove any .svg left from the static era, or Pages serves the stale file and the Function never
    # runs — static assets win over Functions on the same path.
    stale = [f for f in os.listdir(OUT) if f.endswith(".svg")] if os.path.isdir(OUT) else []
    for f in stale:
        os.remove(os.path.join(OUT, f))
    print(f"{len(m)} badges -> {out} (served by functions/badge, {len(stale)} static .svg removed)")
    for cid, sl, trust, verdict in rows[:3]:
        print(f"  {cid}  ->  /badge/{sl}.svg   (tashan score {int(trust)}{' · '+verdict if verdict else ''})")

if __name__ == "__main__":
    main()
