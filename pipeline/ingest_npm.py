#!/usr/bin/env python3
"""tashan — discover MCP servers published to npm.

THE GAP THIS CLOSES. Until now nothing SEARCHED npm. An npm-published server reached the board only if
the official registry happened to list it, or if the config scraper happened to find it in somebody's
public `mcp.json`. Everything else was invisible no matter how widely used.

That is not a small tail. A comparison against a competing directory found `@playwright/mcp` —
Microsoft's own Playwright server, 34,303 stars on its repo, published to npm right now — completely
absent, while a third-party alternative (`@executeautomation/playwright-mcp-server`) sat on the board
at 73. `task-master-ai` had zero rows. These were never a missing SOURCE TYPE; they were a missing
search over a source we already depend on.

WHY npm SPECIFICALLY, AND NOT A GITHUB CRAWL. The same comparison showed 10,648 GitHub-discovered MCP
repos we had never seen — but 71% of them have <=1 star, and a bare repo yields no downloads, no
publish cadence, no deprecation flag and nothing OSV can be queried with. An npm package yields all
four. Everything found here flows into the EXISTING phase-C enrichment and the security scan, so it
arrives fully measurable rather than as another row we can only count.

Identity is `pkg:<npm-name>`, the convention phase A already uses, so a package the scraper later
finds in a real config MERGES into this row instead of forking a second one.

Deliberately conservative about what counts as a hit: `keywords:mcp` alone returns 63,915 packages,
most of which are not MCP servers at all. A result must NAME itself as one (see looks_like_mcp) —
under-collecting is recoverable on the next run, and junk on the board is not.

    python3 pipeline/ingest_npm.py              # incremental (cached page results)
    python3 pipeline/ingest_npm.py --refresh    # re-run every query
    python3 pipeline/ingest_npm.py --dry-run    # show what it would add, write nothing

Env: NPM_SEARCH_CAP (max results per query, default 1500). Stdlib only.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build

CACHE = os.path.join(ROOT, "data", "npm_search_cache.json")
SEARCH = "https://registry.npmjs.org/-/v1/search"
PAGE = 250                                   # npm caps a page at 250 regardless of what you ask for
CAP = int(os.environ.get("NPM_SEARCH_CAP", "1500"))

# Ordered by precision, not by size. `keywords:` is an exact facet; the bare-text queries are there to
# catch packages whose author never set a keyword, which is most of the long tail.
QUERIES = [
    "keywords:modelcontextprotocol",
    "keywords:mcp-server",
    "keywords:mcp",
    "mcp-server",
    "modelcontextprotocol server",
]

# A package must SAY it is one. Matching on the bare substring "mcp" anywhere would sweep in every
# package whose description mentions the protocol in passing, plus unrelated acronyms (mcp = "master
# control program", "multi-chip package"). Anchored on the name, or an explicit keyword, or a
# description that names the protocol.
NAME_RE = re.compile(r"(^|[/@_-])mcp([_-]|$)|mcp[_-]server|server[_-]mcp|modelcontextprotocol", re.I)
DESC_RE = re.compile(r"model[\s-]?context[\s-]?protocol|\bmcp\s+server\b", re.I)
KEYWORDS = {"mcp", "mcp-server", "modelcontextprotocol", "model-context-protocol", "mcp-servers"}


def looks_like_mcp(pkg):
    name = pkg.get("name") or ""
    if NAME_RE.search(name):
        return True
    if KEYWORDS & {str(k).lower() for k in (pkg.get("keywords") or [])}:
        return True
    return bool(DESC_RE.search(pkg.get("description") or ""))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "tashan/1.0 (+https://tashan.sh)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def search(query, cache, refresh):
    """Page through one query. Cached per (query, offset) so a re-run costs nothing."""
    out, frm = [], 0
    while frm < CAP:
        key = f"{query}|{frm}"
        page = None if refresh else cache.get(key)
        if page is None:
            url = f"{SEARCH}?text={urllib.parse.quote(query)}&size={PAGE}&from={frm}"
            d = fetch(url)
            if d is None:
                print(f"    {query}: fetch failed at offset {frm}, stopping this query", flush=True)
                break
            page = [o.get("package") or {} for o in (d.get("objects") or [])]
            cache[key] = page
        out += page
        if len(page) < PAGE:
            break
        frm += PAGE
    return out


SEED = ["tashan-cli"]


def fetch_pkg(name):
    """One package by exact name, shaped like a search hit so the caller treats it identically.

    Search cannot reach a package with no downloads, and this bypasses ranking rather than relevance:
    the row still has to survive looks_like_mcp() and every export gate like any other.
    """
    doc = fetch(f"https://registry.npmjs.org/{urllib.parse.quote(name, safe='@/')}")
    if not doc or "dist-tags" not in doc:
        print(f"  seed: {name} not on npm — skipped", flush=True)
        return None
    latest = (doc.get("dist-tags") or {}).get("latest")
    v = (doc.get("versions") or {}).get(latest) or {}
    repo = (v.get("repository") or {}).get("url") if isinstance(v.get("repository"), dict) else None
    p = {"name": name, "description": doc.get("description") or v.get("description"),
         "keywords": v.get("keywords") or [], "links": {"repository": repo or ""}}
    if not looks_like_mcp(p):
        print(f"  seed: {name} does not describe itself as an MCP capability — skipped", flush=True)
        return None
    return p


def repo_of(pkg):
    """owner/repo from links.repository, when it is a plain GitHub URL."""
    link = ((pkg.get("links") or {}).get("repository") or "")
    m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", link)
    return m.group(1) if m else None


def main():
    refresh = "--refresh" in sys.argv
    dry = "--dry-run" in sys.argv
    cache = {}
    if os.path.exists(CACHE) and not refresh:
        try: cache = json.load(open(CACHE))
        except Exception: cache = {}

    found = {}
    # WE MEASURE OURSELVES BY THE SAME RULES. npm search ranks by popularity, so a new package is
    # invisible to it — `keywords:mcp` alone matches 32,000 packages and returns the top 1,500. Our
    # own CLI was therefore absent from the corpus while every page on the site asked people to run
    # it, which is the one omission an independent rater cannot afford: we ask you to npx an
    # unfamiliar package in order to find risky packages, and published no reading of our own.
    # It gets whatever the evidence gives, including the unflattering parts — 1 maintainer, and no
    # build provenance, which puts us squarely inside the ~77% we point at.
    for name in SEED:
        p = fetch_pkg(name)
        if p:
            found[name] = p
            print(f"  seed: {name} — tracked because it is ours, scored like anything else", flush=True)
    for q in QUERIES:
        hits = search(q, cache, refresh)
        kept = [p for p in hits if p.get("name") and looks_like_mcp(p) and not build.bad_pkg(p["name"])]
        for p in kept:
            found.setdefault(p["name"], p)
        print(f"  {q}: {len(hits)} results, {len(kept)} look like MCP servers", flush=True)
    if not dry:
        json.dump(cache, open(CACHE, "w"))

    con = build.db()
    have = {r[0] for r in con.execute("SELECT npm_pkg FROM capabilities WHERE npm_pkg IS NOT NULL")}
    new = [p for n, p in sorted(found.items()) if n not in have]
    print(f"\n{len(found)} distinct MCP-looking packages; {len(new)} not already tracked")

    if dry:
        for p in sorted(new, key=lambda p: -(p.get("name") and 1 or 0))[:25]:
            print(f"    + {p['name']}  ({(p.get('description') or '')[:60]})")
        con.close(); return 0

    n = 0
    for p in found.values():
        name = p["name"]
        # in_registry stays 0: this is npm-published, which is not the same claim as being LISTED in
        # the official MCP registry, and conflating them would inflate a coverage number we publish.
        con.execute("""INSERT INTO capabilities (id, name, kind, description, npm_pkg, source_repo, in_registry)
            VALUES (?,?,'npm',?,?,?,0)
            ON CONFLICT(id) DO UPDATE SET
              description=COALESCE(capabilities.description, excluded.description),
              source_repo=COALESCE(capabilities.source_repo, excluded.source_repo),
              npm_pkg=COALESCE(capabilities.npm_pkg, excluded.npm_pkg)""",
            ("pkg:" + name, name, p.get("description"), name, repo_of(p)))
        n += 1
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM capabilities WHERE npm_pkg IS NOT NULL").fetchone()[0]
    print(f"upserted {n} npm packages ({len(new)} new) -> {total} npm-backed capabilities in DB")
    print("  they carry no downloads/dates yet — build.py phase C enriches them on the next run")
    con.close()
    return 0


def selftest():
    assert looks_like_mcp({"name": "@playwright/mcp"})
    assert looks_like_mcp({"name": "mcp-server-git"})
    assert looks_like_mcp({"name": "task-master", "keywords": ["MCP"]})
    assert looks_like_mcp({"name": "whatever", "description": "A Model Context Protocol server"})
    # must NOT sweep in unrelated acronyms or passing mentions
    assert not looks_like_mcp({"name": "mcpherson-utils"})
    assert not looks_like_mcp({"name": "multi-chip-package"})
    assert not looks_like_mcp({"name": "some-lib", "description": "works nicely alongside mcp tooling"})
    assert repo_of({"links": {"repository": "https://github.com/microsoft/playwright-mcp.git"}}) == "microsoft/playwright-mcp"
    assert repo_of({"links": {}}) is None
    print("ok — MCP detection anchors on name/keyword/protocol-name, and repo parsing handles .git")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
