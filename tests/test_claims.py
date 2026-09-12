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
    # THE BUY ROUTE, not the Polar URL. Every CTA now goes through /api/buy?plan=…, which repairs
    # the checkout link's success_url before handing the buyer over. `plan` is exactly as
    # discriminating as the old link was — two cadences sharing one plan is the same bug as two
    # cadences sharing one Polar checkout, and is what this still catches.
    href = re.search(r'href="(/api/buy\?plan=[^"]+)"', tag)
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
print("# one price ladder, and the docs must not invent a second")
# GROWTH.md advertised "$0.20 USDC deep-grades any capability on the spot ... (Live on
# pricing.html)". pricing.html has never mentioned USDC, x402 or a per-call price, and on-demand
# deep-grading is not a product. A strategy doc describing a shipped feature that does not exist is
# how a second, unreconciled ladder came to be invented beside it.
_x402src = open(os.path.join(ROOT, "functions", "api", "_x402.js"), encoding="utf-8").read()
# FIELD ORDER IS NOT PART OF THE CONTRACT. This used to require `usd:` on the line immediately
# after the opening brace, so adding `path:` above it — a one-line change in _x402.js — zeroed the
# whole dict and turned every price check below into a comparison against nothing. The "still
# parses" guard caught it, which is the only reason that guard is there. Now the key is found
# first and `usd` is looked for anywhere inside its block.
_priced = {}
for _m in re.finditer(r'"([a-z-]+)":\s*\{', _x402src):
    _blk = _x402src[_m.end():_x402src.find("\n  },", _m.end())]
    _u = re.search(r"\busd:\s*([0-9.]+)", _blk)
    if _u:
        _priced[_m.group(1)] = _u.group(1)
# A COUNT IS THE WRONG ASSERTION. This was `>= 4`, which made removing a product a test failure —
# and one had to be removed: `security-detail` sold advisory detail that redact_paid() already
# publishes free, so the ladder is deliberately shorter than it was. What must hold is that the
# parse still works (a rename of the PRICED shape would otherwise silently zero every check below)
# and that every price the docs quote is a price the code charges.
ok("PRICED still parses", bool(_priced), str(_priced))
# THE RULE THAT MAKES THE LADDER DEFENSIBLE: every priced resource sells TIME or ASSEMBLY, never the
# current state of anything. Current state is the free tier, and the free tier is the distribution.
# `security-detail` violated it and is gone; this stops it, or a sibling, coming back unnoticed.
ok("nothing on the price ladder sells current state",
   "security-detail" not in _priced,
   "advisory detail is free in the export and at /v0.1/lookup — pricing it charges for a giveaway")
_doc = open(os.path.join(ROOT, "docs", "X402.md"), encoding="utf-8").read()
for _k, _usd in _priced.items():
    ok(f"docs/X402.md quotes {_k} at the price the code charges (${_usd})",
       f"`{_k}` | ${_usd}" in _doc or f"${_usd}" in _doc, f"code says ${_usd}")
_growth = open(os.path.join(ROOT, "docs", "GROWTH.md"), encoding="utf-8").read()
# The phrase may still appear inside the correction note, which QUOTES it — that is history, not a
# claim. Only an occurrence outside a blockquote is the site promising something again.
_live_claims = [ln for ln in _growth.splitlines()
                if "Live on `pricing.html`" in ln and not ln.lstrip().startswith(">")]
ok("GROWTH.md does not claim a per-call product is live on pricing.html",
   not _live_claims,
   "it said $0.20 USDC deep-grade was live; pricing.html has never mentioned USDC")
ok("...and the correction is recorded rather than the line quietly deleted",
   "Corrected 14 Aug 2026" in _growth)

print()
print("# the post-purchase hand-off must be reachable")
# THE BUG THIS EXISTS FOR. functions/api/checkout.js exchanges a checkout id for a session, and
# POLAR_ORG_TOKEN is set on the Pages project — the auto sign-in was built and deployed. But the
# Polar checkout links' success_url is a bare https://tashan.sh/welcome.html with no id on it, so
# that endpoint is never reached and every paying customer is asked to paste a licence key. Polar
# substitutes {CHECKOUT_ID} only into a parameter you write yourself; it appends nothing.
# We cannot assert Polar's configuration from here. We CAN assert that our half stays able to
# receive the id, so the moment success_url is fixed the flow works.
_w = open(os.path.join(WEB, "js", "welcome.js"), encoding="utf-8").read()
ok("welcome.js exchanges a checkout id if one arrives",
   "checkout_id" in _w and "/api/checkout?id=" in _w,
   "without this, pointing success_url at /welcome.html?checkout_id=… silently does nothing")
ok("...and still falls back to the paste form rather than stranding anyone",
   "location.replace" in _w and "key" in _w.lower())
_c = open(os.path.join(ROOT, "functions", "api", "checkout.js"), encoding="utf-8").read()
ok("the /api/checkout hand-off still exists to be pointed at",
   "export async function onRequest" in _c)

print()
print("# do not document an endpoint that does not exist")
# We have shipped docs for an unpublished CLI command before, which is the check directly below
# this one. The agent-facing endpoints are the same hazard with a worse failure: an agent that POSTs
# to a 404 does not file a bug, it stops calling. Assert each documented route has a Function.
_hosts = open(os.path.join(WEB, "for-hosts.html"), encoding="utf-8").read()
for _route in sorted(set(re.findall(r"/v0\.1/([a-z]+)", _hosts))):
    _f = os.path.join(ROOT, "functions", "v0.1", _route + ".js")
    _catchall = os.path.join(ROOT, "functions", "v0.1", "[[route]].js")
    ok(f"for-hosts.html documents /v0.1/{_route}, and it is served",
       os.path.exists(_f) or os.path.exists(_catchall))
# The price on the page must be the price the code quotes — same rule as the pricing page.
# REUSES `_priced` from above rather than re-parsing. This block carried its own copy of the same
# brittle regex, so adding one field to a PRICED entry broke the price check in two places at once.
for _key, _label in (("capability-kit", "kit"), ("config-audit", "audit")):
    _v = _priced.get(_key)
    ok(f"the {_label} price on for-hosts.html matches PRICED['{_key}']",
       bool(_v) and ("$" + _v) in _hosts, f"code says ${_v or '?'}")

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
print("# a published judgment must be contestable, and the promise must be kept-able")
# We print a verdict on someone's documentation under their project's name. Until there was a route
# to contest it, the only thing on the page was requests.html — which is for asking us to MEASURE
# something, not for saying we got it wrong.
mt = text(os.path.join(WEB, "methodology.html"))
ok("methodology states a correction turnaround",
   re.search(r"within\s+\*{0,2}?five working days", mt) is not None or "five working days" in mt,
   "a correction path with no turnaround is a gesture")
ok("…and does not promise to remove a grade on request",
   "We do not remove a grade because someone asks" in mt
   or "do not remove a grade because someone asks" in mt,
   "a rating that folds on request is not a measurement")
_graded = [c for c in json.load(open(os.path.join(WEB, "data", "capabilities.json"),
                                     encoding="utf-8"))["capabilities"]
           if c.get("expertise_verdict") and c.get("expertise_note")]
if _graded:
    _pg = os.path.join(WEB, "capability", _graded[0]["slug"] + ".html")
    _src = open(_pg, encoding="utf-8").read() if os.path.exists(_pg) else ""
    ok(f"a graded dossier carries the correction link ({_graded[0]['slug']})",
       "grade-correction" in _src,
       "the judgment is on this page; so must the way to challenge it be")

print()

print()
print("# the score's own limits, measured and published")
# A LOW SCORE IS NOT A SAFETY SIGNAL, and we only know that because we tested it against the series
# instead of asserting it. The raw association says high scores are 224x riskier; conditioning on
# having shipped a release shows that is detection bias — a dormant package cannot add an install
# script. Publishing the caveat WITHOUT the arithmetic behind it would be the same unfounded
# confidence the finding warns against, so both must stay on the page.
_meth = open(os.path.join(WEB, "methodology.html"), encoding="utf-8").read()
ok("methodology says plainly that a low score does not mean safe",
   "does NOT mean" in _meth and "does not mean safe" in _meth.replace("<b>", "").replace("</b>", ""))
ok("...and shows the measurement rather than asserting it",
   "224" in _meth and "0.35%" in _meth,
   "the caveat without its numbers is just another claim")
ok("...and admits what the sample cannot answer",
   "too few to read" in _meth or "cannot yet say" in _meth)
ok("the analysis behind it is in the repo and re-runnable",
   os.path.exists(os.path.join(ROOT, "pipeline", "validate_score.py")))

# ------------------------------------------------------------------------------------------------
# ONE ECOSYSTEM, ONE NUMBER.
#
# The site stated the size of what it measures in four places and gave four different answers:
# index.html "12,001 capabilities measured / of 60,110 tracked" (generated by prerender.py),
# stats.html "30,233 carry a score", for-hosts.html "5,278 measured servers today", and pricing.html
# "300 of the things we measure are abandoned or deprecated" against stats.html's 1,218. For a
# product whose only asset is credibility, a reader who checks two pages catches it in ten seconds.
#
# The rule is not "these must all be equal" — tracked, scored and scanned are genuinely different
# populations. The rule is that any count of them must come from the database, so a stale hardcoded
# figure cannot outlive the run that made it true.
import sqlite3
DB = os.path.join(ROOT, "data", "tashan.db")
if os.path.exists(DB):
    con = sqlite3.connect(DB)
    scored = con.execute("SELECT COUNT(*) FROM capabilities WHERE tashan_score IS NOT NULL").fetchone()[0]
    tracked = con.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]
    dead = con.execute("SELECT COUNT(*) FROM capabilities WHERE vitality='abandoned' "
                       "OR npm_deprecated=1 OR gh_archived=1").fetchone()[0]
    # Every standalone thousands-separated integer on these pages, checked against the two
    # populations it could plausibly be. A number within 2% of neither is a stale claim.
    # stats.html and index.html are GENERATED (gen_stats.py, prerender.py), so their numbers are
    # whatever the last run measured and cannot go stale on their own. These two are hand-written,
    # which is exactly why they drifted.
    for page in ("for-hosts.html", "pricing.html"):
        path = os.path.join(WEB, page)
        if not os.path.exists(path):
            continue
        body = text(path)
        for m in re.finditer(r"\b(\d{1,3}(?:,\d{3})+)\b", body):
            n = int(m.group(1).replace(",", ""))
            near = min(abs(n - p) / max(p, 1) for p in (scored, tracked, dead))
            ok(f"{page}: {m.group(1)} is a live count, not a stale one",
               near < 0.02 or n < 1000,
               f"{n:,} matches none of scored ({scored:,}), tracked ({tracked:,}) "
               f"or abandoned ({dead:,}) — prerender.bake_counts stamps these")
    con.close()

print(("CLAIMS OK" if not fail else "CLAIMS FAILED"))
sys.exit(fail)
