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

Every input is public and re-derivable: the npm packument we already fetch, and OSV.dev's free
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
SEC_CAP = int(os.environ.get("SEC_CAP", "1500"))

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

SEVERITY_ORDER = ["LOW", "MODERATE", "MEDIUM", "HIGH", "CRITICAL"]


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
    provenance = bool(dist.get("attestations")) or bool(dist.get("signatures"))

    # L3 — declared dependencies only
    perms = sorted(k for k, (_lbl, mods) in PERMISSIONS.items()
                   if any(d in mods for d in deps))

    return {
        "pkg": pkg,
        "version": latest,
        "advisories": advisories,
        "install_script": install_script[:300] if install_script else None,
        "provenance": provenance,
        "license": v.get("license") if isinstance(v.get("license"), str) else None,
        "deps": len(deps),
        "maintainers": len(doc.get("maintainers") or []),
        "permissions": perms,
        "remote_content": bool(set(perms) & REMOTE_CONTENT),
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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

    rows = con.execute(
        "SELECT id, npm_pkg FROM capabilities WHERE npm_pkg IS NOT NULL "
        "ORDER BY (sec_scanned_at IS NULL) DESC, npm_downloads DESC NULLS LAST, config_reach DESC "
        "LIMIT ?", (SEC_CAP,)).fetchall()
    print(f"  scanning {len(rows)} npm-backed capabilities "
          f"({len(cache)} cached)...", flush=True)

    scanned = fresh = flagged = 0
    for cid, pkg in rows:
        if build.bad_pkg(pkg):
            continue
        f = cache.get(pkg)
        if f is None:
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
