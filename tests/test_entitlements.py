#!/usr/bin/env python3
"""Pricing, Terms and Refunds must describe the same product.

They did not. Pricing sold advisory detail, install-script contents and the permission surface; Terms
committed to "the named replacement ... and the score-history API"; Refunds said what Terms said. So a
buyer reading the legal page could not discover that the thing they were sold was included, and a
buyer reading the pricing page could not discover that it was not contractually promised. Both
documents were internally coherent, which is why nothing caught it.

data/entitlements.json is now the one definition. This asserts that:
  - every feature the pricing page sells exists there and is not `planned`
  - every PAID feature appears in Terms and Refunds, because those are what a customer is owed
  - nothing marked `planned` is described anywhere as something you get
  - every live feature names a concrete delivery path

`watch` is the live example of the last two: it was the headline of the paid plan and had no
implementation anywhere.

Run: python3 tests/test_entitlements.py
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
ENT = json.load(open(os.path.join(ROOT, "data", "entitlements.json"), encoding="utf-8"))
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def text(pg):
    h = open(os.path.join(WEB, pg), encoding="utf-8").read()
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).lower()


feats = ENT["features"]
paid = [f for f in feats if f["pro"] and not f["free"] and f["status"] != "planned"]
planned = [f for f in feats if f["status"] == "planned"]

print("# the source of truth is well-formed")
ok(f"every live/beta feature names a delivery path ({len(feats) - len(planned)} features)",
   all(f.get("delivered_by") for f in feats if f["status"] != "planned"),
   str([f["id"] for f in feats if f["status"] != "planned" and not f.get("delivered_by")]))
ok("no planned feature is marked as included in a tier",
   all(not (f["free"] or f["pro"]) for f in planned),
   str([f["id"] for f in planned if f["free"] or f["pro"]]))

print()
print("# the legal pages owe the customer what pricing sold them")
# A paid feature must be recoverable from Terms and Refunds — not word-for-word, but by its subject.
KEYWORDS = {
    "advisory-detail": ("advisor", "cve", "ghsa"),
    "install-script": ("install script", "install-time", "install time"),
    "permissions": ("permission",),
    "history": ("history", "historic"),
    "replacement": ("replacement", "replace"),
}
for pg in ("terms.html", "refunds.html"):
    t = text(pg)
    missing = [f["id"] for f in paid
               if not any(k in t for k in KEYWORDS.get(f["id"], (f["id"],)))]
    ok(f"{pg} covers every paid feature ({len(paid)} of them)", not missing,
       f"absent from the document a customer is bound by: {missing}")

print()
print("# nothing anywhere sells what does not exist")
for pg in ("pricing.html", "terms.html", "refunds.html", "start.html", "support.html", "index.html"):
    p = os.path.join(WEB, pg)
    if not os.path.exists(p):
        continue
    t = text(pg)
    bad = []
    for f in planned:
        # the feature's own id and its most quotable phrase
        for probe in (f["id"], "doctor --watch", "--watch"):
            if probe and probe in t:
                bad.append(probe)
    ok(f"{pg} does not offer a planned feature", not bad, f"found {sorted(set(bad))}")

print()
print("# the price on the page is the price in the source")
pt = text("pricing.html")
pro = ENT["tiers"]["pro"]
ok(f"pricing shows {pro['price']}/{pro['cadence']}",
   pro["price"].lower() in pt, f"{pro['price']} not found on the page")

print()
print("ENTITLEMENTS OK" if not fail else "ENTITLEMENTS FAILED")
sys.exit(fail)
