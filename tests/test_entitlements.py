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
print("# the price an AGENT is quoted is the price a human is quoted")
# /api/history answers a credential-less caller with 402 and the terms, so the price is published to
# machines as well as to people. Two copies of a price is exactly how the score once differed
# between the board and a hub table. This is the guard.
# (/api/security was in this list until it was made free — it returned only current state, which
# redact_paid() and /v0.1/lookup already publish. See docs/X402.md.)
_lic = open(os.path.join(ROOT, "functions", "api", "_license.js"), encoding="utf-8").read()
_offer = re.search(r"export const OFFER = \{(.*?)\n\};", _lic, re.S)
ok("functions/api/_license.js still exports OFFER (the machine-readable price)", bool(_offer))
if _offer:
    body = _offer.group(1)
    quoted = {(int(a), c) for a, c in re.findall(r"amount:\s*(\d+),\s*currency:\s*\"(\w+)\"", body)}
    ok("the 402 quotes both plans", quoted == {(6, "USD"), (50, "USD")}, f"found {sorted(quoted)}")
    for amt in (6, 50):
        ok(f"${amt} in the 402 also appears on pricing.html", f"${amt}" in pt)
    # A checkout URL that 404s is worse than none: the agent hands its human a dead link. Read the
    # RAW html here, not text() — a URL lives in an href, so the visible-text copy has none by
    # construction and this compared the quote against an empty set.
    _raw = open(os.path.join(WEB, "pricing.html"), encoding="utf-8").read()
    # MATCH ON THE BUY ROUTE, not on a Polar URL. Both surfaces now send buyers through /api/buy,
    # which repairs the checkout link's success_url on the way past; a raw buy.polar.sh link is the
    # one route that skips it. The check is unchanged in intent — an agent must never hand its
    # human a checkout the page itself does not offer — only in what a checkout looks like.
    _plans = lambda t: set(re.findall(r"/api/buy\?plan=([a-z]+)", t))
    page_links, quoted_links = _plans(_raw), _plans(body)
    ok("every checkout URL quoted to an agent is one the pricing page also links",
       quoted_links and quoted_links <= page_links,
       f"only in the 402: {sorted(quoted_links - page_links)}")
    ok("the 402 quotes no raw Polar link — that route skips the success_url repair",
       "buy.polar.sh" not in body, "found a direct Polar URL in OFFER")
    # The firewall, restated for machines: the refusal must name what costs nothing.
    ok("the 402 names the free surfaces, so a bounce does not read as 'everything is paid'",
       "lookup.json" in body and "llms.txt" in body)

print()
print("# the Pro column must not claim credit for something the Free column gives away")
# THE SAME PAGE SOLD ADVISORY DETAIL TWICE. The free column said "which CVE or GHSA, its severity
# and the version that fixes it … the detail, not just the count", and four lines below the Pro
# column's command hint read "# with Pro: history, advisory detail, replacements". redact_paid()
# had made that free months earlier. A reader comparing the two columns cannot tell what the £6
# actually buys, and the honest list is short: TIME (the series) and the named replacement.
_hint = re.search(r"# with Pro:([^<]*)", open(os.path.join(WEB, "pricing.html"), encoding="utf-8").read())
ok("the Pro command hint exists to be checked", bool(_hint))
if _hint:
    _claimed = _hint.group(1).lower()
    _free_ids = {f["id"] for f in feats if f["free"]}
    _PHRASE = {"advisory-detail": "advisory detail", "install-script": "install script",
               "permissions": "permission"}
    _wrong = [i for i in _free_ids if _PHRASE.get(i) and _PHRASE[i] in _claimed]
    ok("...and it names nothing that entitlements.json marks free",
       not _wrong, f"claimed as a Pro benefit but free to everyone: {_wrong} — hint reads '{_claimed.strip()}'")

print()
print("# a feature we sell must not be sitting in the public export")
# THE CONTRADICTION THIS CATCHES, which had been live for weeks and which no other check could see.
# `advisory-detail`, `install-script` and `permissions` were marked pro-only HERE — the single
# definition of what is sold — long after build.py's redact_paid() had moved all three into the
# public export, pricing.html had started advertising them in the FREE column, and every dossier had
# begun printing "Nothing in this audit is behind a licence". Three documents agreed with each
# other and the source of truth disagreed with all of them.
#
# Prose comparison cannot catch that. This can: if a feature is sold as pro-only, the data behind it
# must NOT be in the file anyone can curl. It ties the commercial claim to the actual bytes.
_EXPORT_COLUMN = {
    "advisory-detail": "sec_advisories",
    "install-script": "sec_install_script",
    "permissions": "sec_permissions",
}
_lookup = json.load(open(os.path.join(WEB, "data", "lookup.json"), encoding="utf-8"))["records"]
_present = {k for r in _lookup for k in r}
for _f in feats:
    _col = _EXPORT_COLUMN.get(_f["id"])
    if not _col or _f["status"] == "planned":
        continue
    if _f["pro"] and not _f["free"]:
        ok(f"{_f['id']} is sold as paid, so {_col} must not be in the public export",
           _col not in _present,
           f"{_col} is in /data/lookup.json — this charges for a giveaway")
    else:
        # The inverse matters just as much: a feature listed as free must actually be delivered
        # free, or the free tier is a claim rather than a fact.
        ok(f"{_f['id']} is listed as free, so {_col} is actually in the public export",
           _col in _present, f"{_col} is missing from /data/lookup.json")

print()
print("# llms.txt is the file we tell every AI crawler to read")
# It never stated the price. An answer engine asked "how much is tashan" had nothing of ours to
# cite, on a site whose product is agent-readability.
_llms = open(os.path.join(WEB, "llms.txt"), encoding="utf-8").read()
ok("llms.txt names the monthly price", ENT["tiers"]["pro"]["price"] in _llms)
_ann = (ENT["tiers"]["pro"].get("annual") or {}).get("price")
ok("llms.txt names the annual price too (it existed only in a data attribute)",
   not _ann or _ann in _llms, f"{_ann} missing")
ok("llms.txt says what is FREE before what is paid", "free" in _llms.lower())
ok("llms.txt restates the firewall for machines",
   "pay to change" in _llms.lower(), "the one rule that makes the measurement worth citing")

print()
print("ENTITLEMENTS OK" if not fail else "ENTITLEMENTS FAILED")
sys.exit(fail)
