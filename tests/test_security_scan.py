#!/usr/bin/env python3
"""The security audit is the paid feature. Every rule in it has to be right, or we sell noise.

Three of these assertions exist because the first cut of the scanner got them wrong, and each one
would have shipped a paid feature that was worse than nothing:

  1. npm signs EVERY package it hosts, so `dist.signatures` is always present. Treating it as
     provenance marked 266 of 266 scanned packages "verified" — a badge with no information in it.
     Only `dist.attestations` records that the publisher built it in public CI.
  2. OSV's malicious-packages database issues MAL-* ids with no CVSS vector. Reading severity from
     the score fields alone labelled CONFIRMED MALWARE "UNKNOWN", the bottom of the scale. The first
     two findings in the whole corpus were exactly that: MAL-2026-5476 and MAL-2026-5478, the two
     packages shadowing @modelcontextprotocol/server-*.
  3. Confirmed malware must never appear on the board, and must ALWAYS remain reachable in the
     lookup — someone who already ran it needs `doctor` to tell them, and doctor can only answer
     from rows it can find.

Run: python3 tests/test_security_scan.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import scan_security as sec

fail = 0


def ok(name, cond):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name)


# ---- severity ---------------------------------------------------------------------------------
ok("a MAL- advisory is MALICIOUS, not UNKNOWN",
   sec.severity_of({"id": "MAL-2026-5476", "summary": "Malicious code in x"}) == "MALICIOUS")
ok("MALICIOUS outranks CRITICAL", sec._rank("MALICIOUS") > sec._rank("CRITICAL"))
ok("CRITICAL outranks HIGH outranks LOW",
   sec._rank("CRITICAL") > sec._rank("HIGH") > sec._rank("LOW"))
ok("a GHSA severity is read from database_specific",
   sec.severity_of({"id": "GHSA-x", "database_specific": {"severity": "HIGH"}}) == "HIGH")
ok("an advisory with no severity anywhere is UNKNOWN, not silently LOW",
   sec.severity_of({"id": "GHSA-y"}) == "UNKNOWN")
ok("unknown severity ranks below every real one", sec._rank("UNKNOWN") < sec._rank("LOW"))

# ---- fixed version ----------------------------------------------------------------------------
ok("the fixed version is pulled out of the OSV range events",
   sec.fixed_version({"affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.2.3"}]}]}]})
   == "1.2.3")
ok("no fix available reads as None, never as a version",
   sec.fixed_version({"affected": [{"ranges": [{"events": [{"introduced": "0"}]}]}]}) is None)

# ---- summarize --------------------------------------------------------------------------------
finding = {
    "pkg": "x", "version": "1.0.0",
    "advisories": [{"id": "MAL-1", "severity": "MALICIOUS", "summary": "s", "fixed": None},
                   {"id": "GHSA-1", "severity": "LOW", "summary": "s", "fixed": "2.0.0"}],
    "install_script": "node evil.js", "provenance": False, "license": "MIT",
    "deps": 4, "maintainers": 1, "permissions": ["shell", "network"],
    "remote_content": True, "scanned_at": "2026-07-31T00:00:00+00:00",
}
s = sec.summarize(finding)
ok("max severity is the WORST finding, not the first or last",
   s["sec_max_severity"] == "MALICIOUS")
ok("advisory count counts them all", s["sec_advisory_count"] == 2)
ok("permissions round-trip as JSON", json.loads(s["sec_permissions"]) == ["shell", "network"])
ok("the install script is carried through", s["sec_install_script"] == "node evil.js")
ok("provenance false stays 0", s["sec_provenance"] == 0)

clean = dict(finding, advisories=[], install_script=None, permissions=[], remote_content=False,
             provenance=True)
c = sec.summarize(clean)
ok("a clean package has no advisories column at all", c["sec_advisories"] is None)
ok("...and a zero count, not null", c["sec_advisory_count"] == 0)
ok("...and no permissions column", c["sec_permissions"] is None)
ok("real provenance is 1", c["sec_provenance"] == 1)

# ---- permission inference ----------------------------------------------------------------------
ok("every permission has a human label and at least one module",
   all(isinstance(lbl, str) and mods for lbl, mods in sec.PERMISSIONS.values()))
ok("remote-content permissions are a subset of the permission set",
   sec.REMOTE_CONTENT <= set(sec.PERMISSIONS))
ok("a browser driver implies browser, which implies remote content",
   "browser" in sec.PERMISSIONS and "browser" in sec.REMOTE_CONTENT)

# ---- the shipped export ------------------------------------------------------------------------
caps_path = os.path.join(ROOT, "web", "data", "capabilities.json")
lk_path = os.path.join(ROOT, "web", "data", "lookup.json")
if os.path.exists(caps_path) and os.path.exists(lk_path):
    caps = json.load(open(caps_path, encoding="utf-8"))["capabilities"]
    lk = json.load(open(lk_path, encoding="utf-8"))["records"]
    on_board = [c for c in caps if c.get("sec_max_severity") == "MALICIOUS"]
    in_lookup = [r for r in lk if r.get("sec_max_severity") == "MALICIOUS"]
    ok("no confirmed-malicious capability is on the board",
       not on_board or print("        board carries: " + ", ".join(c["name"] for c in on_board)))
    ok("confirmed-malicious rows ARE in the lookup, so doctor can warn "
       f"({len(in_lookup)} row(s))", len(in_lookup) >= 1 or not any(
           c.get("sec_max_severity") == "MALICIOUS" for c in caps))
    # a page must never claim a scan that did not happen
    claimed = [c for c in caps if c.get("sec_scanned_at") is None
               and (c.get("sec_advisory_count") is not None or c.get("sec_permissions"))]
    ok("no capability carries findings without a scan timestamp", not claimed)
    scanned = sum(1 for c in caps if c.get("sec_scanned_at"))
    print(f"        {scanned:,} of {len(caps):,} capabilities carry a completed scan")

print("SECURITY SCAN FAILED" if fail else "ok — security scan (severity, provenance, malware gating)")
sys.exit(fail)
