#!/usr/bin/env python3
"""The firewall test — the ranking can never be bought.

tashan's entire differentiator is that Trust is derived ONLY from public signal, so no one can pay to
change a score. Today that holds because the schema has no commerce columns — but that's coincidence,
not enforcement. The moment listings/sales tables land, one JOIN into compute_scores() would erode the
whole thesis silently. This test makes the invariant executable: compute_scores() may read ONLY
public-signal columns, and the scoring code must never mention any commerce concept.

    python3 tests/test_firewall.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "pipeline", "build.py")

# The ONLY columns the scorer is allowed to read. All are re-derivable from public sources (npm, GitHub,
# the MCP registry, public configs). Add here only when you add a new PUBLIC signal — never a commerce one.
PUBLIC_SIGNAL = {
    "id", "config_reach", "config_repos", "stars_median", "stars_max", "last_seen",
    "npm_downloads", "npm_last_publish", "npm_created", "npm_maintainers", "npm_versions", "npm_deprecated",
    "registry_status", "registry_updated", "in_registry", "in_configs",
    "gh_stars", "gh_forks", "gh_open_issues", "gh_pushed", "gh_contributors", "gh_last_release",
    "gh_license", "gh_topics", "gh_has_discussions", "gh_archived",
}

# Words that must NEVER appear inside compute_scores(): if commerce ever leaks into scoring, it shows up here.
COMMERCE_DENY = ["price", "gmv", "revenue", "sales", "sale", "seller", "buyer", "for_sale", "listing",
                 "paid", "purchase", "order", "checkout", "stripe", "payout", "earning", "sponsor", "promoted"]

results = []
def check(name, ok, detail=""):
    results.append(ok)
    print(("  ok  " if ok else " FAIL ") + name + (("  — " + detail) if detail and not ok else ""))

def compute_scores_src():
    src = open(BUILD, encoding="utf-8").read()
    m = re.search(r"\ndef compute_scores\(con\):(.*?)\ndef ", src, re.S)
    assert m, "could not locate compute_scores() in build.py"
    return m.group(1)

def main():
    body = compute_scores_src()

    # 1. the scorer's SELECT reads only allowlisted public-signal columns
    sel = re.search(r'SELECT\s+(.*?)FROM capabilities', body, re.S)   # SQL is string-concatenated across lines
    check("compute_scores has a single SELECT ... FROM capabilities", bool(sel))
    if sel:
        raw = sel.group(1).replace('"', ' ').replace('\n', ' ')       # drop the concatenation quotes/newlines
        cols = [c for c in (x.strip() for x in raw.split(",")) if c]
        illegal = [c for c in cols if c not in PUBLIC_SIGNAL]
        check("scorer reads ONLY public-signal columns", not illegal,
              "non-allowlisted columns in the SELECT: " + repr(illegal))

    # 2. no commerce concept appears anywhere in the scoring function
    low = body.lower()
    hits = [w for w in COMMERCE_DENY if re.search(r"\b" + re.escape(w) + r"\b", low)]
    check("no commerce term appears in compute_scores()", not hits, "found: " + repr(hits))

    # 3. the capabilities schema itself carries no commerce column (belt-and-suspenders)
    schema = open(BUILD, encoding="utf-8").read()
    schema_low = schema[schema.find("SCHEMA ="):schema.find("def db(")].lower()
    mig_low = schema[schema.find("MIGRATE ="):schema.find("def db(")].lower()
    schema_hits = [w for w in COMMERCE_DENY if re.search(r"\b" + re.escape(w) + r"\b", schema_low + mig_low)]
    check("no commerce column in the capabilities schema/MIGRATE", not schema_hits, "found: " + repr(schema_hits))

    failed = results.count(False)
    print(f"\n{'='*46}\nfirewall: {results.count(True)}/{len(results)} passed" +
          (" · all green" if not failed else f" · {failed} FAILED"))
    sys.exit(failed)

if __name__ == "__main__":
    main()
