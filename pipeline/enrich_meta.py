#!/usr/bin/env python3
"""tashan — fill in description / homepage / license from the npm registry.

Two gaps this closes:

1. THE FLAGSHIP PAGES HAD NO PROSE. build.py's npm phase fetches download counts and publish dates but
   throws the packument's `description` away, so the highest-trust capabilities — context7,
   chrome-devtools, server-filesystem — rendered with an empty description. The most-linked pages on the
   site had the least content, which is bad for readers and worse for answer engines that quote a
   sentence.

2. `homepage` WAS EMPTY FOR EVERY ROW (0/2012). npm carries `homepage`, `repository.url` and `bugs.url`,
   which is the canonical "where does this actually live" link a directory owes its users.

Cached in data/npm_meta_cache.json, separate from npm_cache.json so this never invalidates the
download-stats cache. Re-runs only fetch packages not already cached.

    python3 pipeline/enrich_meta.py            # fill anything missing
    python3 pipeline/enrich_meta.py --refresh  # refetch everything

Stdlib only.  Env: META_CAP (max fetches per run, default 900).
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build

CACHE = os.path.join(ROOT, "data", "npm_meta_cache.json")
CAP = int(os.environ.get("META_CAP", "900"))
UA = {"User-Agent": "tashan/1.0 (+https://tashan.sh) capability-metadata"}


def fetch(pkg):
    url = "https://registry.npmjs.org/" + urllib.parse.quote(pkg, safe="@/")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
    except Exception:
        return None
    latest = ((d.get("dist-tags") or {}).get("latest")) or ""
    ver = (d.get("versions") or {}).get(latest) or {}
    repo = d.get("repository") or ver.get("repository") or {}
    if isinstance(repo, str):
        repo_url = repo
    else:
        repo_url = repo.get("url") or ""
    # git+https://github.com/owner/repo.git  ->  owner/repo
    m = re.search(r"github\.com[/:]([^/]+/[^/.#]+)", repo_url or "")
    home = d.get("homepage") or ver.get("homepage") or ""
    # npm defaults homepage to the repo's readme anchor; that is not a product homepage
    if home and re.search(r"github\.com/.+#readme$", home):
        home = ""
    lic = d.get("license") or ver.get("license") or ""
    if isinstance(lic, dict):
        lic = lic.get("type") or ""
    return {"description": (d.get("description") or ver.get("description") or "").strip()[:500],
            "homepage": home.strip()[:300],
            "source_repo": m.group(1) if m else None,
            "license": lic if isinstance(lic, str) else ""}


def main():
    refresh = "--refresh" in sys.argv
    cache = {}
    if os.path.exists(CACHE) and not refresh:
        try:
            cache = json.load(open(CACHE))
        except Exception:
            cache = {}
    con = build.db()
    rows = con.execute("SELECT id, npm_pkg, description, homepage, source_repo, gh_license "
                       "FROM capabilities WHERE npm_pkg IS NOT NULL AND npm_pkg != ''").fetchall()
    todo = [r for r in rows if refresh or not (r[2] and r[3])]
    print(f"{len(rows)} npm-backed capabilities; {len(todo)} missing description or homepage")
    fetched = filled_d = filled_h = filled_r = 0
    for cid, pkg, desc, home, srepo, lic in todo:
        if fetched >= CAP:
            print(f"  (capped at {CAP}; rerun to continue)")
            break
        meta = cache.get(pkg)
        if meta is None:
            meta = fetch(pkg)
            if meta is None:
                continue
            cache[pkg] = meta
            fetched += 1
            time.sleep(0.05)                       # be polite to the public registry
        nd = meta.get("description") or None
        nh = meta.get("homepage") or None
        nr = meta.get("source_repo") or None
        nl = meta.get("license") or None
        # COALESCE semantics: never overwrite something we already measured, only fill blanks
        con.execute("UPDATE capabilities SET "
                    "description = COALESCE(NULLIF(description,''), ?), "
                    "homepage    = COALESCE(NULLIF(homepage,''), ?), "
                    "source_repo = COALESCE(NULLIF(source_repo,''), ?), "
                    "gh_license  = COALESCE(NULLIF(gh_license,''), ?) WHERE id = ?",
                    (nd, nh, nr, nl, cid))
        filled_d += 1 if (nd and not desc) else 0
        filled_h += 1 if (nh and not home) else 0
        filled_r += 1 if (nr and not srepo) else 0
    con.commit()
    json.dump(cache, open(CACHE, "w"))
    have_d = con.execute("SELECT COUNT(*) FROM capabilities WHERE description IS NOT NULL AND description != ''").fetchone()[0]
    have_h = con.execute("SELECT COUNT(*) FROM capabilities WHERE homepage IS NOT NULL AND homepage != ''").fetchone()[0]
    print(f"fetched {fetched} packuments; filled {filled_d} descriptions, {filled_h} homepages, {filled_r} repos")
    print(f"corpus now: {have_d} with a description, {have_h} with a homepage")
    build.export(con)
    con.close()


if __name__ == "__main__":
    main()
