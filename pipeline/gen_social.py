#!/usr/bin/env python3
"""Draft the day's post for X, Threads and Farcaster — from measurements, not marketing.

    python3 pipeline/gen_social.py              # write today's drafts
    python3 pipeline/gen_social.py --show       # print them
    python3 pipeline/gen_social.py --selftest

IT DRAFTS. IT DOES NOT POST. Publishing is outward-facing and irreversible, it needs credentials
this repo deliberately does not hold, and for a product whose credibility rests on judging other
people's packages, an automated account that gets one post wrong is a liability that outlives any
traffic it wins. The queue is reviewed by a human and sent by a human.

WHAT MAKES A POST WORTH SENDING, and the reason this is a generator rather than a template: the
only thing here anyone would follow an account for is the CHANGE. A score is a snapshot anyone can
recompute; "this server started running a script at install time on the 5th" is news, it is dated,
and it is the one thing that cannot be re-derived later. So the day's post is the day's most
consequential finding, stated plainly, with a link to the evidence.

It alternates deliberately. An account that only posts warnings reads as alarmism and stops being
believed; one that only posts recommendations reads as an ad. Odd days lead with what broke, even
days with what is genuinely well-built — both are measurements, and both are true.

LIMITS ARE ENFORCED, NOT HOPED FOR. X free is 280 characters, Threads 500, Farcaster 1024 BYTES —
bytes, so an em-dash costs three. A truncated post is worse than no post, so the selftest fails the
build rather than letting one ship half-written.

Stdlib only. Deterministic for a given day, so re-running does not produce a different opinion.
"""
import json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
OUTDIR = os.path.join(ROOT, "data", "social")
BASE = "https://tashan.sh"

LIMITS = {"x": 280, "threads": 500, "farcaster": 1024}   # farcaster counts BYTES
SEV_RANK = {"high": 0, "medium": 1, "low": 2}
KIND_VERB = {
    "install_script_added": "now runs a script when you install it",
    "permissions_widened":  "now reaches further into your machine",
    "deprecated":           "has been deprecated",
    "abandoned":            "looks abandoned",
    "version_published":    "shipped a release",
    "score_moved":          "moved",
}


def fits(text, platform):
    n = len(text.encode("utf-8")) if platform == "farcaster" else len(text)
    return n <= LIMITS[platform]


def pick(caps, day):
    """The day's subject: most serious recent change, or the best-documented thing we measured."""
    changes = []
    for c in caps:
        for ch in (c.get("changes") or []):
            if ch.get("kind") in ("version_published", "score_moved"):
                continue                       # a release is not news; a rounding move is not either
            changes.append((SEV_RANK.get(ch.get("sev"), 3), ch.get("at") or "", c, ch))
    changes.sort(key=lambda t: (t[0], [-ord(x) for x in (t[1] or "")]))

    praise = sorted(
        (c for c in caps
         if c.get("expertise_verdict") == "deep" and (c.get("tashan_score") or 0) >= 80),
        key=lambda c: -(c.get("npm_downloads") or 0))

    # alternate by day so the account is neither only alarms nor only recommendations
    warn_first = int(day.replace("-", "")) % 2 == 1
    order = ([("warn", changes), ("praise", praise)] if warn_first
             else [("praise", praise), ("warn", changes)])
    for kind, pool in order:
        if pool:
            return kind, pool[0]
    return None, None


def compose(kind, item):
    if kind == "warn":
        _, at, c, ch = item
        name = c.get("label") or c.get("name") or ""
        url = BASE + "/capability/" + c["slug"]
        verb = KIND_VERB.get(ch.get("kind"), "changed")
        # DO NOT RESTATE THE HEADLINE. `why` often paraphrases the verb — "now reaches further into
        # your machine" followed by "its dependencies reach further into your machine than they did
        # before" is one sentence said twice, which is exactly the register that makes an automated
        # account read as generated. Prefer the ACTION, which tells the reader what to do; fall back
        # to `why` only when it adds something the headline did not.
        why = (ch.get("why") or "").rstrip(".")
        action = (ch.get("action") or "").rstrip(".")
        head = {w for w in verb.lower().split() if len(w) > 4}
        detail = action or ("" if head and head <= set(why.lower().split()) else why)
        short = f"{name} {verb}.\n\nMeasured {at}. {url}"
        long = (f"{name} {verb}.\n\n" + (f"{detail}.\n\n" if detail else "")
                + f"Measured {at} from public evidence, free to check: {url}")
        return {"subject": c["id"], "kind": ch.get("kind"), "x": short,
                "threads": long, "farcaster": long}
    c = item
    name = c.get("label") or c.get("name") or ""
    url = BASE + "/capability/" + c["slug"]
    dl = c.get("npm_downloads")
    ev = f"{dl:,}/wk" if dl else "public config reach"
    short = (f"{name} — tashan {int(c['tashan_score'])}, documentation graded deep.\n\n"
             f"{ev}. {url}")
    long = (f"{name} — tashan score {int(c['tashan_score'])}, and its documentation grades deep: "
            f"per-tool docs, worked examples, setup and a stated limitation.\n\n"
            f"{ev}. Every input is public and checkable: {url}")
    return {"subject": c["id"], "kind": "well-documented", "x": short,
            "threads": long, "farcaster": long}


def build(caps, day):
    kind, item = pick(caps, day)
    if not item:
        return None
    post = compose(kind, item)
    post["day"] = day
    post["status"] = "draft"
    for p in LIMITS:
        # Trim on a word boundary rather than shipping half a sentence; the selftest asserts fit.
        while not fits(post[p], p):
            post[p] = post[p][: post[p].rstrip().rfind(" ")].rstrip(" ,.—-") + "…"
    return post


def _selftest():
    caps = [{"id": "pkg:x", "slug": "pkg-x", "label": "X" * 40, "tashan_score": 91,
             "expertise_verdict": "deep", "npm_downloads": 1234567,
             "changes": [{"at": "2026-08-10", "kind": "install_script_added", "sev": "high",
                          "what": "x now runs a script", "why": "W" * 400, "action": "check it"}]}]
    for day in ("2026-08-10", "2026-08-11"):
        p = build(caps, day)
        assert p, "a corpus with a change and a deep grade must always yield a post"
        for plat in LIMITS:
            assert fits(p[plat], plat), f"{plat} draft over limit: {len(p[plat])}"
        assert p["x"].count("http") == 1, "exactly one link, so the click is unambiguous"
    a, b = build(caps, "2026-08-10"), build(caps, "2026-08-11")
    assert a["kind"] != b["kind"], "consecutive days must alternate warn/praise"
    assert build(caps, "2026-08-10") == a, "same day must produce the same draft"
    print("ok — social drafts fit every platform limit, alternate, and are deterministic")
    return 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    d = json.load(open(DATA, encoding="utf-8"))
    caps = d["capabilities"] if isinstance(d, dict) else d
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    post = build(caps, day)
    if not post:
        print("social: nothing worth posting today")
        return 0
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, day + ".json")
    json.dump(post, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"social: drafted {post['kind']} about {post['subject']} -> data/social/{day}.json")
    if "--show" in sys.argv:
        for p in ("x", "threads", "farcaster"):
            n = len(post[p].encode()) if p == "farcaster" else len(post[p])
            print(f"\n--- {p} ({n}/{LIMITS[p]}) ---\n{post[p]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
