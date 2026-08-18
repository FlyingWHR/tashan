#!/usr/bin/env python3
"""L5 — the dependency tree, resolved and scanned. What "no known advisories" was never covering.

    python3 pipeline/scan_deps.py                # nightly slice, demand-ordered
    DEPS_CAP=200 python3 pipeline/scan_deps.py   # a bigger bite
    python3 pipeline/scan_deps.py --selftest     # no network, no npm

WHY THIS EXISTS. scan_security queries OSV by PACKAGE NAME, so a finding means the capability's own
release is affected and a clean result means only that. A server whose dependency ships a known
vulnerability has always read "No known advisories" here. Every surface says "this package, not its
dependency tree" since 17 Aug, which is honest and is not the same as looking.

TWO MEASUREMENTS DECIDED THE SHAPE OF THIS FILE, and the gap between them is the reason it resolves
versions instead of taking the cheap route:

    matching dependency NAMES against OSV        25 of 29 "clean" capabilities look dirty   (86%)
    resolving the tree and querying with VERSIONS  1 of 14                                   (7%)

The 86% is nearly all noise — express, undici and open carry advisories at SOME version and resolve
to fixed ones. Shipping that number would have been a scare story, and a scare story from the
instrument that exists to stop scare stories. The 7% is real: prisma resolves deepmerge-ts@7.1.5,
which carries GHSA-ggr8-5vv4-36mx today.

HOW THE TREE IS RESOLVED. `npm install --package-lock-only`, which computes the full resolved graph
and writes a lockfile WITHOUT downloading or executing anything. `--ignore-scripts` is passed as
well, belt and braces: this resolves packages we already suspect, including some in OSV's malicious
database, and the one thing an auditor must never do is run them. Nothing from the tree is executed,
imported, or kept — the temp directory is removed after every package.

BUDGET IS FETCHES, NOT ROWS, and the walk is demand-ordered, for the reason written into
scan_security: a cached row must cost nothing, or the cache works against us and a run spends its
whole allowance re-reading what it already knows. Resolution takes seconds per package, so the
corpus is covered over weeks rather than in a night, most-installed first.
"""
import json, os, shutil, subprocess, sys, tempfile, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CACHE = os.path.join(ROOT, "data", "deps_cache.json")
CACHE_VERSION = 1          # bump when a finding's MEANING changes, or stale entries serve new rules
DEPS_CAP = int(os.environ.get("DEPS_CAP", "40"))
TTL_DAYS = int(os.environ.get("DEPS_TTL_DAYS", "14"))
OSV_BATCH = "https://api.osv.dev/v1/querybatch"
MAX_TREE = 2000            # a tree larger than this is a monorepo mistake, not a dependency graph


def _post(url, body, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json",
                                          "user-agent": "tashan-deps-scan"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def resolve_tree(spec, workdir=None, run=None):
    """{name: version} for the whole resolved graph, or None if npm could not resolve it.

    NOTHING IS DOWNLOADED AND NOTHING IS RUN. --package-lock-only computes the graph and writes a
    lockfile; --ignore-scripts means even npm's own lifecycle hooks stay off. That is not a
    performance choice — this resolves packages that are in OSV's malicious database.
    """
    run = run or (lambda cmd, cwd: subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=240))
    tmp = workdir or tempfile.mkdtemp(prefix="tashan-deps-")
    try:
        os.makedirs(tmp, exist_ok=True)
        with open(os.path.join(tmp, "package.json"), "w", encoding="utf-8") as fh:
            fh.write('{"name":"tashan-probe","private":true,"version":"1.0.0"}')
        r = run(["npm", "install", "--package-lock-only", "--ignore-scripts",
                 "--no-audit", "--no-fund", "--silent", spec], tmp)
        lock = os.path.join(tmp, "package-lock.json")
        if getattr(r, "returncode", 1) != 0 or not os.path.exists(lock):
            return None
        doc = json.load(open(lock, encoding="utf-8"))
        out = {}
        for path, meta in (doc.get("packages") or {}).items():
            if path.startswith("node_modules/") and meta.get("version"):
                out[path.split("node_modules/")[-1]] = meta["version"]
        return out if len(out) <= MAX_TREE else dict(list(out.items())[:MAX_TREE])
    except Exception:
        return None
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def vulnerable(tree, post=None, exclude=None):
    """[(name, version, [advisory ids])] for packages vulnerable AT THE RESOLVED VERSION.

    Queried WITH the version — the whole point. Without it, express and undici look vulnerable in
    almost every tree in the corpus and the result is a number nobody should publish.
    """
    post = post or _post
    # THE PACKAGE IS IN ITS OWN TREE. npm places the requested package under node_modules/ like any
    # other, so claude-cup came back as "1 vulnerable dependency" whose vulnerability was its own
    # MAL-2026-5789 — already reported at L1, and counted twice reads as two separate problems.
    # A capability cannot be its own dependency, so the root is dropped before the query.
    items = [(n, v) for n, v in tree.items() if n != exclude]
    out = []
    for i in range(0, len(items), 400):          # OSV caps a batch; 400 is comfortably under it
        chunk = items[i:i + 400]
        res = post(OSV_BATCH, {"queries": [{"package": {"name": n, "ecosystem": "npm"},
                                            "version": v} for n, v in chunk]})
        for (n, v), r in zip(chunk, (res or {}).get("results") or []):
            ids = [x.get("id") for x in (r.get("vulns") or []) if x.get("id")]
            if ids:
                out.append((n, v, ids))
    return out


def load_cache():
    if not os.path.exists(CACHE):
        return {"_v": CACHE_VERSION}
    try:
        c = json.load(open(CACHE, encoding="utf-8"))
    except ValueError:
        return {"_v": CACHE_VERSION}
    return c if c.get("_v") == CACHE_VERSION else {"_v": CACHE_VERSION}


def stale(entry):
    at = (entry or {}).get("at")
    if not at:
        return True
    try:
        return (datetime.now(timezone.utc).date()
                - datetime.strptime(at[:10], "%Y-%m-%d").date()).days >= TTL_DAYS
    except ValueError:
        return True


def main():
    import build
    con = build.db()
    cache = load_cache()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # DEMAND ORDER, and a cached row costs nothing. Never-scanned breaks the tie, so breadth still
    # advances every night — the rule scan_security had to learn the hard way.
    rows = con.execute(
        "SELECT id, npm_pkg, npm_latest_version FROM capabilities "
        "WHERE npm_pkg IS NOT NULL AND npm_latest_version IS NOT NULL AND npm_runnable = 1 "
        "ORDER BY npm_downloads DESC NULLS LAST, tashan_score DESC").fetchall()
    todo = [r for r in rows if stale(cache.get(r[1] + "@" + (r[2] or "")))][:DEPS_CAP]
    print(f"  {len(rows):,} launchable npm capabilities; resolving {len(todo)} "
          f"(cap {DEPS_CAP}, TTL {TTL_DAYS}d)...", flush=True)

    done = hit = 0
    for cap_id, pkg, ver in todo:
        key = f"{pkg}@{ver}"
        tree = resolve_tree(key)
        if tree is None:
            # A resolution failure is NOT a clean result and must never be cached as one. Left
            # unstamped so the next run tries again — the same rule enrich_npm learned when a
            # transient failure got cached as a permanent zero for 1,751 packages.
            continue
        try:
            vulns = vulnerable(tree, exclude=pkg)
        except Exception:
            continue
        cache[key] = {"at": today, "n": len(tree),
                      "v": [{"name": n, "version": v, "ids": ids} for n, v, ids in vulns]}
        con.execute("UPDATE capabilities SET dep_tree_n=?, dep_vuln_n=?, dep_vulns=?, "
                    "dep_scanned_at=? WHERE id=?",
                    (len(tree), len(vulns),
                     json.dumps(cache[key]["v"]) if vulns else None, today, cap_id))
        done += 1
        hit += 1 if vulns else 0
        if done % 10 == 0:
            con.commit()
            json.dump(cache, open(CACHE, "w", encoding="utf-8"))
            print(f"    deps {done}/{len(todo)}", flush=True)
    con.commit()
    json.dump(cache, open(CACHE, "w", encoding="utf-8"))
    total = con.execute("SELECT COUNT(*) FROM capabilities WHERE dep_scanned_at IS NOT NULL").fetchone()[0]
    withv = con.execute("SELECT COUNT(*) FROM capabilities WHERE dep_vuln_n > 0").fetchone()[0]
    print(f"  resolved {done} this run ({hit} with a vulnerable dependency)")
    print(f"  corpus: {total:,} trees scanned, {withv:,} carry a vulnerable dependency")
    build.export(con)
    con.close()
    return 0


def _selftest():
    # The lockfile shape, which is the only thing standing between us and a wrong tree.
    lock = {"packages": {"": {"name": "probe"},
                         "node_modules/a": {"version": "1.0.0"},
                         "node_modules/@scope/b": {"version": "2.3.4"},
                         "node_modules/c": {},                      # no version: not a package
                         "not_node_modules/d": {"version": "9"}}}   # not in the tree
    d = os.path.join(tempfile.mkdtemp(prefix="tashan-selftest-"), "w")
    os.makedirs(d)
    json.dump(lock, open(os.path.join(d, "package-lock.json"), "w"))
    class R: returncode = 0
    tree = resolve_tree("x@1", workdir=d, run=lambda cmd, cwd: R())
    assert tree == {"a": "1.0.0", "@scope/b": "2.3.4"}, tree
    # THE SAFETY FLAGS ARE THE FEATURE. This resolves packages in OSV's malicious database.
    seen = {}
    class R2: returncode = 1
    resolve_tree("evil@1", workdir=d, run=lambda cmd, cwd: (seen.update(cmd=cmd), R2())[1])
    assert "--ignore-scripts" in seen["cmd"], seen["cmd"]
    assert "--package-lock-only" in seen["cmd"], "must resolve, never install"
    # A failed resolve is not a clean tree.
    assert resolve_tree("nope@1", workdir=d, run=lambda cmd, cwd: R2()) is None

    # Queried WITH the version, or the answer is the 86% scare story instead of the 7% truth.
    asked = {}
    def fake_post(url, body, timeout=90):
        asked["q"] = body["queries"]
        return {"results": [{"vulns": [{"id": "GHSA-x"}]}, {}]}
    got = vulnerable({"deepmerge-ts": "7.1.5", "safe": "1.0.0"}, post=fake_post)
    assert all("version" in q for q in asked["q"]), asked["q"]
    assert got == [("deepmerge-ts", "7.1.5", ["GHSA-x"])], got
    # A CAPABILITY IS NOT ITS OWN DEPENDENCY. npm puts the requested package in the tree, so
    # claude-cup reported its own MAL-2026-5789 as a dependency finding — double-counting an
    # advisory L1 already publishes, and reading as two problems where there is one.
    vulnerable({"claude-cup": "0.9.12", "x": "1.0"}, post=fake_post, exclude="claude-cup")
    assert [q["package"]["name"] for q in asked["q"]] == ["x"], asked["q"]

    assert stale({}) and stale({"at": "2000-01-01"}) and not stale(
        {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    print("scan_deps selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
