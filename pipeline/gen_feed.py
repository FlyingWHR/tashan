#!/usr/bin/env python3
"""An Atom feed of what actually changed — the only thing here that is new every day.

    python3 pipeline/gen_feed.py

WHY A FEED IS DISTRIBUTION AND A SITEMAP IS NOT. A sitemap asks a crawler to come and look. A feed
is pulled: by readers, by aggregators, by newsletter tooling, and by the answer engines that treat a
dated stream as a freshness signal about a whole domain. Nothing here had one.

It is also the only content this project produces that is genuinely NEW rather than recomputed. A
score is a snapshot anyone could derive from public sources today; "minia2a started running a script
when it installs, on 5 August" exists only because somebody recorded the day before. That is the
asset, and it was reaching one page each and no channel at all.

WHAT IT IS NOT. It is not a marketing list and there is nobody to unsubscribe: it is a file, pulled
by whoever wants it. For a product whose credibility rests on judging other people's packages
without being a nuisance, the distribution has to be the kind people opt into.

Stdlib only. Deterministic: same events in, byte-identical file out, so a nightly run that changed
nothing does not churn a commit.
"""
import html, json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
OUT = os.path.join(ROOT, "web", "changes.xml")
BASE = "https://tashan.sh"
MAX_ITEMS = 50

SEV_RANK = {"high": 0, "medium": 1, "low": 2}


def esc(t):
    return html.escape(str(t or ""), quote=True)


def build(caps, generated):
    items = []
    for c in caps:
        for ch in (c.get("changes") or []):
            items.append((SEV_RANK.get(ch.get("sev"), 3), ch.get("at") or "", c, ch))
    # newest first, most serious first within a day — the order a reader would want, not the order
    # the table happened to be in
    items.sort(key=lambda t: (t[1], -t[0]), reverse=True)
    items = items[:MAX_ITEMS]

    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<feed xmlns="http://www.w3.org/2005/Atom">',
           "  <title>tashan — what changed</title>",
           '  <link href="%s/changes.xml" rel="self"/>' % BASE,
           '  <link href="%s/"/>' % BASE,
           "  <id>%s/changes.xml</id>" % BASE,
           "  <updated>%s</updated>" % (items[0][1] + "T00:00:00Z" if items else generated),
           "  <subtitle>Advisories, install scripts, permission changes and abandonment across "
           "the MCP corpus — measured daily from public evidence.</subtitle>",
           "  <author><name>tashan</name><uri>%s</uri></author>" % BASE,
           "  <rights>CC BY 4.0 — attribute tashan (tashan.sh).</rights>"]
    for _, at, c, ch in items:
        slug = c.get("slug") or ""
        url = BASE + "/capability/" + slug + ".html"
        name = c.get("label") or c.get("name") or slug
        title = "%s — %s" % (name, ch.get("what") or "changed")
        body = (ch.get("why") or "") + (("  " + ch["action"]) if ch.get("action") else "")
        out += ["  <entry>",
                "    <title>%s</title>" % esc(title),
                '    <link href="%s"/>' % esc(url),
                "    <id>%s#%s-%s</id>" % (esc(url), esc(ch.get("kind") or "change"), esc(at)),
                "    <updated>%sT00:00:00Z</updated>" % esc(at),
                "    <category term=\"%s\"/>" % esc(ch.get("kind") or "change"),
                "    <summary>%s</summary>" % esc(body.strip()),
                "  </entry>"]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    caps = d["capabilities"] if isinstance(d, dict) else d
    gen = (d.get("metadata", {}) or {}).get("generated_at") if isinstance(d, dict) else None
    gen = gen or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    xml = build(caps, gen)
    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    if old == xml:
        print("feed: unchanged")
        return 0
    open(OUT, "w", encoding="utf-8").write(xml)
    print("feed: %d entries -> web/changes.xml" % xml.count("<entry>"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
