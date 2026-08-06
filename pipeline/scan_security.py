#!/usr/bin/env python3
"""Security audit for every capability we can reach, from public evidence only.

    python3 pipeline/scan_security.py            # incremental, cached
    python3 pipeline/scan_security.py --full     # re-scan everything
    SEC_CAP=200 python3 pipeline/scan_security.py

Four layers, in the order a person installing an agent tool actually cares about:

  L1  KNOWN VULNERABILITIES   OSV.dev, queried with the version you would install TODAY. A finding
                              means the current release is affected — not "this package once had a
                              CVE five years ago", which is the alarmist version of the same data.
  L2  SUPPLY CHAIN            install-time scripts, provenance, maintainer concentration, dependency
                              surface, missing licence, registry removal.
  L3  PERMISSION SURFACE      what the thing can reach on your machine: files, shell, network,
                              browser, credentials, cloud. Derived from DECLARED dependencies — no
                              code is executed and nothing is installed.
  L4  REMOTE CONTENT          whether it pulls remote content back into the agent's context, which is
                              the injection-exposure question specific to this ecosystem.

Every input is public and linked to its source: the npm packument we already fetch, and OSV.dev's free
keyless API. Nothing here executes package code, and nothing here can be bought — the firewall in
tests/test_firewall.py still governs the score, and none of these columns feed it.
"""
import json, os, re, sqlite3, sys, time
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
CACHE = os.path.join(ROOT, "data", "security_cache.json")
OSV = "https://api.osv.dev/v1/query"
NPM = "https://registry.npmjs.org/"
# A budget of NETWORK FETCHES, not of rows. It used to be a `LIMIT` on the query, which quietly made
# the two things the same and let the cache work against us: a cached row still consumed a slot, so
# once the top of the queue was cached the run spent its whole budget doing nothing and never reached
# the packages that needed fetching. Counting fetches lets the walk go all the way down the demand
# order every night and spend the budget only where there is something to learn.
SEC_CAP = int(os.environ.get("SEC_CAP", "1500"))
# How long a finding stays good. Tighter than the npm metadata TTL because the things it reads move
# under us: a CVE is published against a version that is already installed everywhere, a maintainer
# adds a postinstall in a patch release, a package is added to the malicious database. At ~2,300
# scanned that is ~330 re-fetches a day, well inside SEC_CAP with room for new discovery.
SEC_TTL_DAYS = int(os.environ.get("SEC_TTL_DAYS", "7"))


def expired(at):
    """True when a finding is older than the TTL, or carries no timestamp to judge it by."""
    if not at:
        return True
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(at)).days >= SEC_TTL_DAYS
    except ValueError:
        return True

# ---- L3: permission surface --------------------------------------------------------------------
# A declared dependency is a commitment: you cannot drive a browser without shipping a browser
# driver. This is deliberately conservative — it under-reports (a server can shell out with plain
# node:child_process and declare nothing) and never over-reports, and the UI says so. Under-reporting
# a permission is a missed warning; over-reporting one is an accusation we cannot support.
PERMISSIONS = {
    "filesystem":  ("reads and writes files",
                    ["fs-extra", "glob", "minimatch", "chokidar", "graceful-fs", "rimraf",
                     "fast-glob", "globby", "mkdirp", "tmp", "node:fs"]),
    "shell":       ("runs shell commands",
                    ["shelljs", "execa", "cross-spawn", "node-pty", "child_process",
                     "node:child_process", "zx", "sudo-prompt"]),
    "network":     ("makes network requests",
                    ["node-fetch", "axios", "got", "undici", "superagent", "request", "ky",
                     "cross-fetch", "isomorphic-fetch"]),
    "browser":     ("drives a browser",
                    ["puppeteer", "puppeteer-core", "playwright", "playwright-core",
                     "@playwright/test", "@playwright/browser-chromium", "selenium-webdriver",
                     "chrome-remote-interface"]),
    "database":    ("connects to databases",
                    ["pg", "mysql", "mysql2", "better-sqlite3", "sqlite3", "mongodb", "redis",
                     "ioredis", "@prisma/client", "knex"]),
    "credentials": ("handles credentials or secrets",
                    ["keytar", "dotenv", "google-auth-library", "@aws-sdk/credential-providers",
                     "@azure/identity", "jsonwebtoken", "oauth", "simple-oauth2"]),
    "cloud":       ("talks to cloud provider APIs",
                    ["aws-sdk", "@aws-sdk/client-s3", "@google-cloud/storage", "@azure/storage-blob",
                     "@aws-sdk/client-ec2", "googleapis"]),
}
# L4: a capability that reaches the network or a browser can carry third-party text back into the
# model's context. That is a fact about its surface, not an accusation about its behaviour.
REMOTE_CONTENT = {"network", "browser"}

# MALICIOUS sits above CRITICAL. OSV's malicious-packages database issues MAL- ids with no CVSS
# vector, so scoring them by severity field alone labelled confirmed malware "UNKNOWN" — the bottom
# of the scale. The first two findings in the corpus were MAL-2026-5476 and MAL-2026-5478, the
# dependency-confusion canaries shadowing @modelcontextprotocol/server-*, reported as unknown-risk.
SEVERITY_ORDER = ["LOW", "MODERATE", "MEDIUM", "HIGH", "CRITICAL", "MALICIOUS"]

# Bump when the shape or meaning of a cached finding changes, so stale entries are re-fetched
# instead of silently serving a value computed by the old, wrong rule.
# 3: records whether the package declares a `bin`. Nothing about an existing finding's meaning
#    changed, but the field cannot be back-filled from a cached entry, and "absent" must not be read
#    as "no bin" — the board gate below treats unknown and false very differently.
CACHE_VERSION = 3


def _rank(sev):
    s = (sev or "").upper()
    return SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else -1


def post_json(url, payload, timeout=20, retries=2):
    body = json.dumps(payload).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=body, headers={"content-type": "application/json",
                                         "User-Agent": "tashan-pipeline"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == retries:
                return None
        except Exception:
            if attempt == retries:
                return None
        time.sleep(1 + attempt)
    return None


def get_json(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tashan-pipeline"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def severity_of(vuln):
    """OSV puts severity in several places depending on which database supplied the record."""
    if str(vuln.get("id", "")).startswith("MAL-"):
        return "MALICIOUS"           # OSV malicious-packages: the package IS the attack
    ds = vuln.get("database_specific") or {}
    if ds.get("severity"):
        return str(ds["severity"]).upper()
    for aff in vuln.get("affected") or []:
        s = (aff.get("database_specific") or {}).get("severity")
        if s:
            return str(s).upper()
    for s in vuln.get("severity") or []:
        # CVSS vector — map the base score into the same buckets GHSA uses
        sc = str(s.get("score") or "")
        m = re.search(r"/AV:", sc)
        if not m:
            try:
                v = float(sc)
                return ("CRITICAL" if v >= 9 else "HIGH" if v >= 7
                        else "MODERATE" if v >= 4 else "LOW")
            except ValueError:
                pass
    return "UNKNOWN"


def fixed_version(vuln):
    for aff in vuln.get("affected") or []:
        for rng in aff.get("ranges") or []:
            for ev in rng.get("events") or []:
                if ev.get("fixed"):
                    return ev["fixed"]
    return None


def scan_npm(pkg):
    """One package -> the full finding set. Returns None when npm has nothing for this name."""
    doc = get_json(NPM + urllib.parse.quote(pkg, safe="@/"))
    if not doc or "dist-tags" not in doc:
        return None
    latest = (doc.get("dist-tags") or {}).get("latest")
    v = (doc.get("versions") or {}).get(latest) or {}
    scripts = v.get("scripts") or {}
    deps = sorted((v.get("dependencies") or {}).keys())
    dist = v.get("dist") or {}

    # L1 — queried WITH the version, so a hit means the release you would install today is affected
    payload = {"package": {"name": pkg, "ecosystem": "npm"}}
    if latest:
        payload["version"] = latest
    osv = post_json(OSV, payload) or {}
    advisories = []
    for x in (osv.get("vulns") or []):
        advisories.append({
            "id": x.get("id"),
            "severity": severity_of(x),
            "summary": (x.get("summary") or "")[:200],
            "fixed": fixed_version(x),
        })
    advisories.sort(key=lambda a: -_rank(a["severity"]))

    # L2 — install-time code execution is the highest-leverage supply-chain signal there is
    install_script = scripts.get("postinstall") or scripts.get("preinstall") or None
    # `signatures` is on EVERY npm package — the registry signs its own tarballs — so treating it as
    # provenance marked 266 of 266 scanned packages as verified, which is a badge that means nothing.
    # Only `attestations` records that the publisher built it in public CI.
    provenance = bool(dist.get("attestations"))

    # L3 — declared dependencies only
    perms = sorted(k for k, (_lbl, mods) in PERMISSIONS.items()
                   if any(d in mods for d in deps))

    # NOT a security signal — an identity one, recorded here because this is the only stage that
    # already holds the version manifest. A host launches an MCP server by running a command, so a
    # package with no `bin` cannot be one: it is a library you build servers WITH. The board was
    # ranking @modelcontextprotocol/sdk at #1 by adoption on 53M weekly downloads, plus /core,
    # /client, /node, /express, /hono and /fastify — every one of them a build-time dependency
    # presented to a reader as something to install.
    runnable = bool(v.get("bin"))

    return {
        "pkg": pkg,
        "version": latest,
        "advisories": advisories,
        "install_script": install_script[:300] if install_script else None,
        "provenance": provenance,
        "runnable": runnable,
        "license": v.get("license") if isinstance(v.get("license"), str) else None,
        "deps": len(deps),
        "maintainers": len(doc.get("maintainers") or []),
        "permissions": perms,
        "remote_content": bool(set(perms) & REMOTE_CONTENT),
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "v": CACHE_VERSION,
    }


def summarize(f):
    """Collapse a finding set into the columns the site and CLI read."""
    adv = f.get("advisories") or []
    worst = max((a["severity"] for a in adv), key=_rank, default=None) if adv else None
    return {
        "sec_advisories": json.dumps(adv) if adv else None,
        "sec_advisory_count": len(adv),
        "sec_max_severity": worst,
        "sec_install_script": f.get("install_script"),
        "sec_provenance": 1 if f.get("provenance") else 0,
        # NULL, not 0, when the cached finding predates the field. `.get()` returning None here and
        # being written as 0 would assert "this package declares no bin" about every package scanned
        # before today — and that assertion takes a capability off the board.
        "npm_runnable": None if "runnable" not in f else (1 if f["runnable"] else 0),
        "sec_permissions": json.dumps(f["permissions"]) if f.get("permissions") else None,
        "sec_remote_content": 1 if f.get("remote_content") else 0,
        "sec_dep_count": f.get("deps"),
        "sec_scanned_at": f.get("scanned_at"),
        "npm_license": f.get("license"),
        "npm_latest_version": f.get("version"),
    }


def main():
    import build                                   # reuse db(), schema, migrations
    full = "--full" in sys.argv
    con = build.db()
    con.execute("PRAGMA busy_timeout = 30000")
    cache = {}
    if os.path.exists(CACHE) and not full:
        try:
            cache = json.load(open(CACHE))
        except (ValueError, OSError):
            cache = {}

    # BY DEMAND FIRST, never-scanned only as the tie-break. The old order put every never-scanned row
    # ahead of every scanned one, which reads as fairness and is the wrong risk model for this stage:
    # a stale advisory scan on a package with 53M weekly installs is a worse thing to publish than a
    # missing one on a package with 200. Staleness here is the safety problem, so re-verification of
    # the most-used has to outrank breadth. Breadth still advances every night — the fetch budget is
    # spent on whatever is stale or new as the walk goes down, and a cached, current row costs nothing.
    rows = con.execute(
        "SELECT id, npm_pkg FROM capabilities WHERE npm_pkg IS NOT NULL "
        "ORDER BY npm_downloads DESC NULLS LAST, (sec_scanned_at IS NULL) DESC, config_reach DESC"
    ).fetchall()
    print(f"  walking {len(rows):,} npm-backed capabilities, budget {SEC_CAP:,} fetches "
          f"({len(cache)} cached)...", flush=True)

    scanned = fresh = flagged = 0
    for cid, pkg in rows:
        if build.bad_pkg(pkg):
            continue
        f = cache.get(pkg)
        if f is not None and f.get("v") != CACHE_VERSION:
            f = None                 # computed by an older rule — re-fetch rather than trust it
        elif f is not None and expired(f.get("scanned_at")):
            # AND AN ADVISORY SCAN GOES OFF. A version bump alone would have frozen this cache the
            # moment the sweep finished: scanned once, correct that day, served for ever. Everything
            # this stage reads is a moving target — a new CVE lands against the version already
            # published, a maintainer adds a postinstall, a package is flagged malicious. This is the
            # one stage where serving a memory as a measurement is a safety problem, not a staleness
            # one, and the whole point of the demand-first walk is that the answer stays true.
            f = None
        if f is None:
            if fresh >= SEC_CAP:
                continue             # budget spent; the rest of the walk still syncs from cache
            f = scan_npm(pkg)
            if f is None:
                continue
            cache[pkg] = f
            fresh += 1
            if fresh % 25 == 0:
                json.dump(cache, open(CACHE, "w"))         # checkpoint: a long run must be resumable
                # AND commit, which releases the write lock. Holding one transaction across a
                # 1,900-package scan locks the database for the whole run — every other pipeline
                # stage and the test suite fail with "database is locked" until it finishes.
                print(f"    {fresh} fetched…", flush=True)
        cols = summarize(f)
        con.execute("UPDATE capabilities SET " + ", ".join(f"{k}=?" for k in cols) + " WHERE id=?",
                    list(cols.values()) + [cid])
        # Commit per row. Batching every 25 held the write lock across ~50 network calls, which is
        # minutes — longer than build.db()'s 60s busy_timeout, so every other process (the test
        # suite, any pipeline stage) died with "database is locked" for the whole scan. A SQLite
        # commit is microseconds; the network is the only slow part here, so there is nothing to
        # batch for.
        con.commit()
        scanned += 1
        if cols["sec_advisory_count"] or cols["sec_install_script"] or cols["sec_permissions"]:
            flagged += 1
    con.commit()
    json.dump(cache, open(CACHE, "w"))

    adv = con.execute("SELECT COUNT(*) FROM capabilities WHERE sec_advisory_count > 0").fetchone()[0]
    ins = con.execute("SELECT COUNT(*) FROM capabilities WHERE sec_install_script IS NOT NULL").fetchone()[0]
    perm = con.execute("SELECT COUNT(*) FROM capabilities WHERE sec_permissions IS NOT NULL").fetchone()[0]
    print(f"  scanned {scanned} ({fresh} newly fetched) · {flagged} with at least one finding")
    print(f"  advisories: {adv} capabilities · install scripts: {ins} · permission surface: {perm}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
