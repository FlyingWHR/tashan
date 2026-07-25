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

VCOLOR = {"deep": "#5cf0c0", "solid": "#34e0a0", "thin": "#8a8a93", "wrapper": "#f2604a", "slop": "#f2604a"}
CW = 6.6          # monospace char width at 11px
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

def slug(cid):
    return re.sub(r"[^a-z0-9]+", "-", cid.lower()).strip("-")

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def badge(trust, verdict):
    left = "◆ tashan"
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
<text x="8" y="14" font-family="{MONO}" font-size="11" font-weight="600"><tspan fill="#34e0a0">◆</tspan><tspan fill="#ededf0"> tashan</tspan></text>
<text x="{lw+8}" y="14" font-family="{MONO}" font-size="11" font-weight="600">{rtext}</text>
</svg>'''

def main():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT id, trust, expertise_verdict FROM capabilities WHERE trust IS NOT NULL").fetchall()
    n = 0
    for cid, trust, verdict in rows:
        open(os.path.join(OUT, slug(cid) + ".svg"), "w").write(badge(trust, verdict))
        n += 1
    print(f"{n} badges -> {OUT}")
    # a couple of demo prints so the slug scheme is visible
    for cid, trust, verdict in rows[:3]:
        print(f"  {cid}  ->  /badge/{slug(cid)}.svg   (Trust {int(trust)}{' · '+verdict if verdict else ''})")

if __name__ == "__main__":
    main()
