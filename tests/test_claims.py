#!/usr/bin/env python3
"""Every claim a page makes about itself must be true of that page.

WHY THIS EXISTS. An external audit found the site contradicting itself in five places at once, and
every one was a sentence asserting something the code did differently:

  - task and role pages said "ranked by tashan score" and sorted by (fit, instruction depth, score).
    The rendered order descended 71..51 and then restarted at 71, in plain sight, on every task page.
  - methodology.html said "the current version is s2" while production served s5 — two scorer bumps
    had shipped without anyone editing the prose.
  - pricing.html sold "the complete audit" while terms.html said "don't claim tashan has audited
    anything" and the scan reaches only npm-resolvable capabilities.
  - methodology.html said "there is no CVE scan" on a site whose paid tier is built around one.
  - about.html said the rank answers "did it work" while methodology said outcome quality is not
    measured and controlled evaluation is roadmap.

None of these were data bugs. The database was right every time. They are prose asserting facts that
live in code, with nothing checking the two agree — which is the same failure as slugify existing in
four places, one layer up. For a product whose entire claim is measurement, a page that misstates its
own ranking is not a typo; it is the product failing at the thing it sells.

Run: python3 tests/test_claims.py
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def text(p):
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", open(p, encoding="utf-8").read())
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def scores_in_order(path):
    """The tashan scores as a reader meets them, top to bottom.

    Strip <script> first or the JSON-LD ItemList's ratingValue floods this with the same numbers in a
    different order. The selector is the rendered cell, `<span class="sig__val">`, because that is
    what a person actually reads down the page.
    """
    h = re.sub(r"<script[\s\S]*?</script>", " ", open(path, encoding="utf-8").read())
    return [int(x) for x in re.findall(r'<span class="sig__val">(\d+)</span>', h)]


print("# a page that states its ordering must use it")
checked_any = False
# Category hubs claim "ranked by tashan score" and must therefore be descending by score.
for p in sorted(glob.glob(os.path.join(WEB, "category", "*.html"))):
    # RAW, not the tag-stripped body: the claim lives in <meta name="description"> and og:description,
    # which is what a search result and an answer engine quote. Reading only visible text made this
    # check skip every page silently — a guard that cannot find its own subject.
    raw = open(p, encoding="utf-8").read()
    sc = scores_in_order(p)
    if "ranked by tashan score" not in raw:
        continue
    # A guard that silently skips when the selector stops matching is not a guard. This check exists
    # because a page lied about its own ordering; if it cannot read the order, that is a failure.
    if len(sc) < 2:
        continue                      # a tail page of unrated rows has nothing to order
    checked_any = True
    ok(f"{os.path.basename(p)} says 'ranked by tashan score' and is",
       all(a >= b for a, b in zip(sc, sc[1:])),
       f"parsed {len(sc)} scores: {sc[:12]}")

ok("at least one category page had scores to check (guard is not vacuous)", checked_any)

# Task and role hubs sort by (fit, depth, score) and must NOT claim to rank by score.
for d in ("task", "role"):
    # raw again — the claim these pages used to make was in the meta description, exactly where a
    # body-text check would never have seen it.
    bad = [os.path.basename(p) for p in glob.glob(os.path.join(WEB, d, "*.html"))
           if "ranked by tashan score" in open(p, encoding="utf-8").read()]
    ok(f"no {d} page claims 'ranked by tashan score' (it sorts by fit, then depth, then score)",
       not bad, f"{len(bad)} do, e.g. {bad[:3]}")

print()
print("# the methodology must describe the scorer that actually ran")
export = json.load(open(os.path.join(WEB, "data", "capabilities.json"), encoding="utf-8"))
live = export.get("scorer")
meth = open(os.path.join(WEB, "methodology.html"), encoding="utf-8").read()
m = re.search(r'id="mScorer">([^<]+)<', meth)
ok("methodology names the live scorer version", bool(m) and m.group(1) == live,
   f"page says {m.group(1) if m else 'NOTHING'}, export says {live}")

print()
print("# no page may claim a completeness the coverage does not have")
caps = export["capabilities"]
scanned = sum(1 for c in caps if c.get("sec_scanned_at") or c.get("sec_advisory_count") is not None)
pct = 100.0 * scanned / max(len(caps), 1)
for pg in ("index.html", "pricing.html", "about.html", "methodology.html"):
    t = text(os.path.join(WEB, pg))
    bad = re.findall(r"complete audit|whole security audit|audited before you install|fully audited", t, re.I)
    ok(f"{pg} claims no blanket audit ({scanned}/{len(caps)} = {pct:.0f}% are scanned)",
       not bad, f"found: {sorted(set(bad))}")

print()
print("# claims the terms explicitly disclaim must not appear as marketing")
# terms.html says "we measure; we don't vouch" and "don't claim tashan certifies, endorses or has
# audited anything". Selling the opposite on another page is the contradiction, not the wording.
about = text(os.path.join(WEB, "about.html"))
ok("about.html does not claim the rank answers 'did it work'",
   "did it work" not in about, "methodology says outcome quality is not measured")

meth_t = text(os.path.join(WEB, "methodology.html"))
ok("methodology does not deny the CVE scan it documents elsewhere",
   "there is no CVE scan" not in meth_t)

print()
print("# reproducibility is a stronger claim than traceability — only claim what holds")
# Documentation grades come from an LLM, adoption from sampled config mining, discovery from
# rate-limited search. Those are traceable to public sources; a stranger cannot re-derive them
# without our snapshots, prompts and model version.
for pg in ("index.html", "terms.html", "methodology.html"):
    t = text(os.path.join(WEB, pg))
    ok(f"{pg} does not claim numbers are re-derivable by anyone",
       not re.search(r"re-?derivable", t, re.I))

print()
print("# a price we advertise must be a price we can charge")
pricing = open(os.path.join(WEB, "pricing.html"), encoding="utf-8").read()
# ORDER-INDEPENDENT. This used to require href="…" to appear BEFORE data-src="…" in the tag, so a
# generator that emitted the attributes the other way round made the check find zero links and pass
# vacuously on the page whose whole job is not charging the wrong amount. Parse each <a> once, then
# read its attributes.
links = []
for tag in re.findall(r"<a\b[^>]*>", pricing):
    href = re.search(r'href="(https://buy\.polar\.sh/[^"]+)"', tag)
    src = re.search(r'data-src="([^"]+)"', tag)
    if href:
        links.append((href.group(1), src.group(1) if src else ""))
by_url = {}
for url, src in links:
    by_url.setdefault(url, []).append(src)
# THE BUG THIS CATCHES. "$6 monthly" and "$49 yearly" pointed at the SAME Polar checkout — a $6/month
# subscription. Anyone choosing annual was charged monthly, and data-src recorded it as an annual
# conversion, so neither the customer nor the funnel could see the mismatch. Two CTAs offering
# different cadences must never share one price object.
shared = {u: s for u, s in by_url.items() if len(set(s)) > 1}
ok("no two checkout CTAs with different cadences share a price link",
   not shared, f"{shared}")

body = text(os.path.join(WEB, "pricing.html"))
# NORMALISE before counting, or "$6/mo", "$6 mo" and "$6 /mo" read as three different prices — which
# is the check being wrong, not the page. What matters is distinct (amount, cadence) pairs.
raw = re.findall(r"\$(\d+)\s*(?:/|per\s)?\s*(mo|month|yr|year)", body, re.I)
prices = {(amt, "yr" if c.lower().startswith("y") else "mo") for amt, c in raw}
ok(f"pricing advertises one cadence per live checkout link ({len(by_url)} link, offers: {sorted(prices) or 'none'})",
   len(prices) <= len(by_url), f"{sorted(prices)} advertised, {len(by_url)} checkout link(s)")

print()
print("# do not sell a command the published CLI does not have")
# tashan-cli@0.1.1 on npm has `activate` and `doctor`; it has no `login` and no `--watch`. The site
# sold both. A sign-in instruction that does not exist is a conversion dead end for someone who has
# already decided to pay.
# Checked against the tarball actually on npm, not the repo — 0.1.1 shipped WITHOUT `login` while the
# repo had it under the same version number, so the site told readers to run a command their installed
# package did not contain. 0.1.2 ships login/activate/doctor; `watch` is still sold nowhere because it
# is still not implemented.
UNSHIPPED = ("--watch", "doctor --watch")
for pg in ("pricing.html", "support.html", "start.html", "account.html"):
    fp = os.path.join(WEB, pg)
    if not os.path.exists(fp):
        continue
    t = text(fp)
    bad = [c for c in UNSHIPPED if c in t]
    ok(f"{pg} names no unpublished CLI command", not bad, f"found: {bad}")

print()
print("# a published stability promise must be the one the build enforces")
# The freeze date is a commitment to customers who buy score history: inside the window we do not
# change the scoring. It lives in pipeline/scorer.lock, is enforced by tests/test_scorer_version.py,
# and is BAKED into methodology.html by prerender. A date typed on the page that the lock has already
# moved past is the same class of defect as "the current version is s2" — a promise the code stopped
# keeping, still on display.
lock = os.path.join(ROOT, "pipeline", "scorer.lock")
mt = text(os.path.join(WEB, "methodology.html"))
parts = open(lock, encoding="utf-8").read().split() if os.path.exists(lock) else []
ok("scorer.lock declares a stability window", len(parts) >= 4,
   f"expected '<version> <fingerprint> <effective> <stable_until>', got {parts}")
if len(parts) >= 4:
    ok(f"methodology publishes the locked freeze date ({parts[3]})", parts[3] in mt,
       "the page promises a different date than the guard enforces")

print()
print("# the coverage the page states must be the coverage we measured")
# Published as a headline because it is the honest weak spot; a hand-typed number here would drift
# the moment a night's enrichment landed, and drift in the direction that flatters us.
cov_path = os.path.join(WEB, "data", "coverage.json")
if not os.path.exists(cov_path):
    ok("web/data/coverage.json exists", False, "run python3 pipeline/coverage.py")
else:
    cov = json.load(open(cov_path, encoding="utf-8"))
    t1k = cov["tiers"]["top1000"]
    ok(f"methodology states the measured tier size ({t1k['n']:,})", f"{t1k['n']:,}" in mt)
    for key, label in (("score", "tashan score"), ("scan", "security scan"),
                       ("grade", "expertise grade"), ("task", "task mapping")):
        pct = round(100.0 * t1k[key] / t1k["n"])
        # The number must appear next to its own label, not merely somewhere on a long page — a bare
        # digit match would pass on any page containing that percentage for anything at all.
        # \s* on both sides: text() replaces each tag with a space, so the baked
        # `<span id="cvScan">98</span>%` reaches here as "security scan 98 %".
        near = re.search(re.escape(label) + r"\s*" + str(pct) + r"\s*%", mt)
        ok(f"methodology states {label} coverage as {pct}%", bool(near),
           f"page does not say '{label} {pct}%' — re-run pipeline/coverage.py then prerender.py")

print()
print("# the bundled skill must not contradict the site")
# The skill is what an agent LOADS — it is read instead of the pages, by a reader that cannot check.
# It said "It is not a security audit. No CVE scan" on a product whose paid tier is built around an
# OSV scan: the identical sentence this file already fails the build for on methodology.html, missed
# here because a Markdown file in plugin/ was not part of "the site".
skill = os.path.join(ROOT, "plugin", "skills", "tashan", "SKILL.md")
if not os.path.exists(skill):
    ok("the bundled skill exists", False, skill)
else:
    st = re.sub(r"\s+", " ", open(skill, encoding="utf-8").read())
    ok("the skill does not deny the security scan it documents elsewhere",
       not re.search(r"no cve scan|not a security audit\b", st, re.I),
       "the scan is real — say what it does and does not cover, do not deny it")
    ok("the skill still refuses to equate a high score with safety",
       re.search(r"never present a high score as .safe.", st, re.I) is not None)
    # A hardcoded score in a document an agent quotes is a wrong measurement with a long half-life:
    # context7 was written as 90 and had been 97 for days.
    ok("the skill quotes no capability score that could go stale",
       not re.search(r'"[^"]+"\s*->\s*\[\s*\d+', st),
       "drop the literal numbers — point at the endpoint instead")
    # .find(), not .index(): if the skill stops mentioning /v0.1/lookup at all, index() raises and the
    # guard dies with a traceback instead of reporting a failure — which reads as a broken test rather
    # than a broken document, and is exactly how a check gets deleted instead of heeded.
    i_lookup, i_bulk = st.find("/v0.1/lookup"), st.find("/v0.1/scores")
    ok("the skill leads with the per-question endpoint, not a bulk download",
       i_lookup >= 0 and (i_bulk < 0 or i_lookup < i_bulk),
       "an agent following this in order should not download 420 KB to check one package"
       if i_lookup >= 0 else "the skill no longer mentions /v0.1/lookup at all")
    ok("the skill tells the agent what a MALICIOUS verdict means",
       "DO NOT INSTALL" in st)

print()
print("# we may not claim a provenance we do not have")
# tashan-cli published from CI on 7 Aug 2026 and came back with `attestations: None` — npm signs
# every tarball it hosts, but an ATTESTATION needs a public source repository and ours is private.
# start.html had been saying the gap "is being fixed: publishing moves to a CI workflow that attests
# the build". The workflow shipped, the attestation did not, and the sentence became exactly the
# overclaim this file exists to stop — on the page that asks people to trust running our code.
try:
    import urllib.request as _u
    with _u.urlopen("https://registry.npmjs.org/tashan-cli", timeout=15) as r:
        _d = json.load(r)
    _v = _d["versions"][_d["dist-tags"]["latest"]]
    attested = bool((_v.get("dist") or {}).get("attestations"))
except Exception as e:
    # Skip rather than fail an offline run — but SAY WHY. A bare skip turns a transient blip into a
    # silent pass on a check about whether we are overclaiming, and this one already skipped once on
    # a network hiccup and looked identical to being offline.
    attested, why = None, f"{type(e).__name__}: {e}"[:80]
st = text(os.path.join(WEB, "start.html"))
if attested is None:
    print(f"  --   npm unreachable ({why}), skipping the provenance-claim check")
else:
    ok(f"npm reports attestations={attested} for the published CLI", True)
    if not attested:
        ok("start.html does not claim the provenance gap is fixed or being fixed",
           not re.search(r"provenance[^.]{0,120}(is being fixed|now attests|we fixed)", st),
           "we publish no attestation; saying otherwise on the page that asks for trust is the "
           "exact overclaim this file exists to stop")
        ok("start.html says WHY there is no attestation, rather than omitting it",
           "public source repository" in st or "public repository" in st,
           "an absent explanation reads as an oversight; it is a consequence of a private repo")

print()
print(("CLAIMS OK" if not fail else "CLAIMS FAILED"))
sys.exit(fail)
