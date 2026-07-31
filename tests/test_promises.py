#!/usr/bin/env python3
"""Every feature the pricing page sells must have code that delivers it.

THE DEFECT THIS EXISTS TO PREVENT, which shipped. The pricing page sold five Pro features and the
product delivered two. "The advisory itself — which CVE or GHSA … and the version that fixes it" and
"What the install script actually runs, and the full permission list" had NO implementation
anywhere: no endpoint served them, no CLI path printed them, and capability.js made no gated fetch at
all. Meanwhile every capability page carried an "unlock detail" link that a paying customer could
click forever without anything changing.

That is not a missing feature. It is a page describing, in the present tense, what $6 buys today.

WHY A TEST AND NOT A NOTE. Copy is edited far more often than plumbing, and the failure is silent —
nothing errors when a bullet point outruns the code. docs/FEATURE-AUDIT.md records the analysis; this
records the invariant, so the build breaks rather than the promise.

HOW IT WORKS. Each claim below is pinned to a marker in the copy and to the code that fulfils it. A
claim whose delivery code is missing fails. If you cut the claim from the page, delete its entry here
too — that is the honest path and it is meant to be easy.

Run: python3 tests/test_promises.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def read(rel):
    p = os.path.join(ROOT, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


PRICING = read("web/pricing.html")

# claim key -> (a phrase that appears in the pricing copy, [(file, regex that proves delivery)])
CLAIMS = {
    "named replacement": (
        "The replacement, named",
        [("cli/tashan.mjs", r"if \(pro\)")],
    ),
    "score history": (
        "Every score since we started measuring",
        [("functions/api/history.js", r"validate\(env"),
         ("cli/tashan.mjs", r"/api/history")],
    ),
    # For these two the proof MUST be a gated endpoint. redact_paid() strips the raw values from
    # every public payload, so no client can render them from data it already holds — a delivery path
    # necessarily means a licensed fetch.
    #
    # An earlier version of this file accepted `sec_install_script.*(script|command)` in the CLI as
    # proof and passed, because re.S let `.*` run to the end of the file and match an unrelated word.
    # The only hit was `r.row.sec_install_script ||` inside the UPSELL condition — the code that
    # advertises the feature was being read as the code that delivers it. A test that passes wrongly
    # is worse than no test, so the proof is now a named file that must actually exist.
    # Proof = the gated endpoint RETURNS the field, and a client asks for it. Matching the KV
    # storage key would pass on a stub that stores but never serves.
    "advisory detail": (
        "which CVE or GHSA",
        [("functions/api/security.js", r"advisories:\s*rec\."),
         ("web/js/capability.js", r"/api/security")],
    ),
    "install script contents": (
        "What the install script actually runs",
        [("functions/api/security.js", r"install_script:\s*rec\."),
         ("web/js/capability.js", r"install_script")],
    ),
}

for key, (phrase, proofs) in CLAIMS.items():
    sold = phrase.lower() in re.sub(r"\s+", " ", PRICING).lower()
    if not sold:
        print(f"  --   '{key}' is no longer sold on the pricing page — nothing to deliver")
        continue
    delivered = [f"{f}" for f, rx in proofs if re.search(rx, read(f), re.S)]
    ok(f"'{key}' is sold, and something delivers it", bool(delivered),
       "sold on /pricing.html but no code delivers it — either build it or cut the claim "
       f"(looked in: {', '.join(f for f, _ in proofs)})")

# The unlock link is itself a promise: it says detail exists behind a licence. If nothing on the web
# can ever resolve it, the link is decoration on the one page carrying a buy button.
unlock_in_ui = 'class="unlock"' in read("web/js/capability.js") or 'class="unlock"' in read("pipeline/prerender.py")
web_can_resolve = bool(re.search(r"/api/security|signed_in|sec_advisories", read("web/js/capability.js")))
ok("an 'unlock detail' link on the web can actually resolve for a licence holder",
   not unlock_in_ui or web_can_resolve,
   "capability.js renders 'unlock detail' but never checks for a licence and never fetches gated "
   "detail — a paying customer sees exactly what a stranger sees on every page of the site")

# And the free floor, from the other direction: these must never become paid.
FREE_FOREVER = ("tashan score", "expertise", "sec_advisory_count", "sec_max_severity")
idx = read("pipeline/build.py")
slim = re.search(r"SLIM = \[(.*?)\]", idx, re.S)
slim_txt = slim.group(1) if slim else ""
# sec_permissions is a DOSSIER fact, not a board column, so it lives in the export rather than the
# slim index. Check it where it actually ships.
exp_cols = re.search(r'"sec_advisory_count","sec_max_severity".*?\]', idx, re.S)
slim_txt += (exp_cols.group(0) if exp_cols else "")
# sec_permissions is on this list because the free column promises "what it can reach on your
# machine". It was briefly truncated to one entry to "protect" a paid claim that sold the same fact,
# which broke the free promise AND stopped the headline read warning about credentials.
missing_free = [f for f in ("tashan_score", "expertise_verdict", "sec_advisory_count",
                            "sec_max_severity", "sec_permissions")
                if f not in slim_txt]
ok("the free tier still ships score, grade and the existence of every finding", not missing_free,
   f"missing from the public board index: {missing_free}")

print("\nPROMISES FAILED — the page sells something the product does not do" if fail
      else "\nok — every feature sold is a feature delivered")
sys.exit(fail)
