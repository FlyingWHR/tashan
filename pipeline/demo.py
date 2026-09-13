#!/usr/bin/env python3
"""The demo script, with every number read off the live data instead of typed.

    python3 pipeline/demo.py             # print the beat sheet
    python3 pipeline/demo.py --serve     # start the local preview first, then print it
    python3 pipeline/demo.py --check     # exit 1 if anything would be stale on camera
    python3 pipeline/demo.py --selftest

WHY THIS EXISTS. The script lived in docs/HACKATHON.md with its figures typed into the prose, and
within a week it told the presenter to say "11,914 measured of 55,268 tracked" over a page reading
12,656 of 95,195, and "$247,247 settled" over a page reading $247,318. Reading a stale number aloud,
on camera, on a product whose entire claim is that its numbers are current, is the most expensive
sentence in the submission — and it is the exact failure this codebase already refuses everywhere
else: numbers are derived, never typed.

So the script is generated. If the pipeline runs the night before the recording, the words change
with it. `--check` is the guard to run immediately before hitting record: it re-reads the published
files and the machine's own config and fails if the beat sheet in your hand cannot be spoken.

ETHGLOBAL'S RULES, which decide the shape of this and are not negotiable (verified against
ethglobal.com/events/ethonline/info/details, 13 Sep 2026):

    "Must be between 2 and 4 minutes"           -> the beats below total 3:30, with slack at both ends
    "DO NOT export ... less than 720p"          -> upload fails outright below it
    "DO NOT use a text to speech synthesizer / AI Voiceover"
    "DO NOT use mobile phones to record"
    "DO NOT speed up the video to fit under the time limit"
    "DO NOT play music with text on the video describing your project (instead of talking)"

The voiceover rule is why this file prints a script rather than producing a video: the narration has
to be a person, and the last two rules close the obvious ways around that. Nothing here can record
it for you, and nothing should try.
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
PREVIEW = "http://localhost:4173"


def load(rel):
    p = os.path.join(WEB, "data", rel)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def money(v):
    """Dollars as a presenter would say them. $166,661 — never $166,660.9964."""
    if v is None:
        return None
    return "$%s" % format(round(v), ",") if v >= 100 else "$%.2f" % v


def inventory():
    """This machine's own agent config, via the CLI the demo opens with.

    Read live because it is the one figure the audience watches being produced: the presenter runs
    doctor on camera, so the script must say what THIS laptop will print, not what some laptop
    printed once. Absent (node missing, CLI moved) is returned as None rather than guessed — a beat
    sheet that invents an inventory is worse than one that says it could not read it.
    """
    cli = os.path.join(ROOT, "cli", "tashan.mjs")
    if not os.path.exists(cli):
        return None
    try:
        out = subprocess.run(["node", cli, "doctor", "--json"], capture_output=True, text=True,
                             timeout=180, cwd=ROOT)
        inv = (json.loads(out.stdout) or {}).get("inventory") or {}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if not inv:
        return None
    return {
        "servers": len(inv.get("servers") or []),
        "plugins": len(inv.get("plugins") or []),
        "skills": len(inv.get("skills") or []),
        "projects": inv.get("projects") or 0,
        "unowned": sum(1 for s in (inv.get("skills") or []) if s.get("authored")),
    }


def facts(with_inventory=True):
    """Every number the script speaks, in one place, all of it derived."""
    idx, dem, exp = load("index.json"), load("demand.json"), load("capabilities.json")
    eco = dem.get("economy") or {}
    caps = exp.get("capabilities") or []
    paid = sorted((c for c in caps if c.get("paid_usd")), key=lambda c: -c["paid_usd"])
    ours = next((c for c in caps if c.get("id") == "pkg:tashan-cli"), None)
    listed = (eco.get("receivers_paid") or 0) + (eco.get("receivers_never_paid") or 0)
    return {
        "measured": idx.get("measured"),
        "tracked": idx.get("total_capabilities"),
        "generated": (idx.get("generated_at") or "")[:10],
        "scanned": idx.get("risk_scanned"),
        "paid_usd": eco.get("paid_usd"),
        "payments": eco.get("payments"),
        "receivers_paid": eco.get("receivers_paid"),
        "receivers_never": eco.get("receivers_never_paid"),
        "receivers_listed": listed or None,
        "median_usd": eco.get("median_usd"),
        "top": paid[0] if paid else None,
        "ours": ours,
        "inv": inventory() if with_inventory else None,
    }


# ---- the beat sheet ------------------------------------------------------------------------------
# Four beats, 3:30, inside the 2-4 minute window with room at both ends. Each is (clock, heading,
# what you DO, what you SAY) — the two are separated because reading a stage direction aloud is the
# most common way a first take dies.

def beats(f):
    n = lambda v: "—" if v is None else format(v, ",")
    inv, top, ours = f["inv"], f["top"], f["ours"]

    if inv:
        opener = (f"{n(inv['servers'])} MCP servers, {n(inv['plugins'])} plugins, "
                  f"{n(inv['skills'])} skills, across {n(inv['projects'])} projects. "
                  f"{n(inv['unowned'])} of those skills are owned by no plugin — nothing will ever "
                  f"update them but me. I did not know that before I wrote this, and neither does "
                  f"anyone else running an agent.")
    else:
        opener = ("[could not read this machine's config — run `node cli/tashan.mjs doctor` and say "
                  "what it prints]")

    out = [(
        "0:00-0:25", "The problem, on your own machine",
        ["Terminal, full screen.", "Run:  npx tashan-cli doctor"],
        [opener],
    ), (
        "0:25-1:10", "What tashan is",
        [f"Open {PREVIEW}", "Point at the hero, then click any capability."],
        [f"{n(f['measured'])} measured, of {n(f['tracked'])} tracked. Measured today.",
         "Every number has its inputs on the page: upkeep, freshness, adoption, and how much of the "
         "evidence we actually have. Plus an advisory scan against the version you would install "
         "today.",
         "Nobody can pay to move a rank. That is not a promise on an about page — it is "
         "tests/test_firewall.py. It reads the scorer's source and fails the build if it touches a "
         "column that is not public signal."],
    ), (
        "1:10-2:30", "The money, and the point of the whole thing",
        ["Click 'Who gets paid'.", "Read the figures off the page, then scroll to the table."],
        ["Everything I just showed you is a proxy. Downloads, stars, publish cadence — all of them "
         "can exist without one person finding the thing useful. This cannot.",
         f"{n(f['receivers_paid'])} of {n(f['receivers_listed'])} listed x402 services have been "
         f"paid at least once. {n(f['receivers_never'])} never have. "
         f"{money(f['paid_usd']) or '—'} settled"
         + (f", across {n(f['payments'])} payments" if f["payments"] else "") + ".",
         f"And the median service has earned {money(f['median_usd']) or '—'} in its entire life.",
         "A directory lists all of them and publishes evidence about none of them. This is the "
         "first index of which ones anybody actually paid."]
        + ([f"Land on {top['name']}: {money(top['paid_usd'])} across "
            f"{n(top.get('paid_calls'))} calls, tashan score "
            f"{int(top['tashan_score']) if top.get('tashan_score') else '—'}.",
            "Adoption and payment are different questions, and this is what it looks like when they "
            "disagree. Payment is deliberately not an input to the score — 'someone pays for this' "
            "and 'this is well made' are different claims."] if top else [])
        + ([f"Then find our own row — Cmd-F for tashan — {money(ours.get('paid_usd') or 0)}, "
            f"never paid.",
            "We publish a price too, so we are in our own table, on zero. Nobody put us there and "
            "nobody exempted us. An instrument that leaves itself out of its own measurement is not "
            "an instrument."] if ours else []),
    ), (
        "2:30-3:30", "How it was built, and what it is for",
        ["Back to the terminal.", "Run:  npx tashan-cli mcp   (or show the agent calling it)"],
        ["Your agent can ask this before it installs anything, instead of after.",
         "An unknown name comes back unmeasured — never 'bad'. A clean scan says nothing known is "
         "wrong, not 'safe'. An agent cannot ask a follow-up question, so every answer carries its "
         "own caveat.",
         "Everything on the site is public evidence and it stays free. What is paid for is the work: "
         "the history behind a row, and the answer assembled on demand."],
    )]
    return out


# ---- the tracks, and whether we actually qualify -------------------------------------------------
# Verified 13 Sep 2026 against ethglobal.com/events/ethonline2026/prizes. `need` is the sponsor's own
# requirement list, shortened but not softened; `gate` names the check in qualify() that tests it.
#
# THE POINT OF ENCODING THIS. It is very easy to write a submission that describes the project you
# wish you had entered. docs/SUBMISSION.md already claimed all three Bazantic tracks on the strength
# of our own MCP server — but every Bazantic track requires artifacts that live on bazantic.com, and
# we have never had an account. Claiming a track we do not qualify for is the exact failure this
# product exists to point at, aimed at ourselves.
TRACKS = [
    {"id": "graph1", "sponsor": "The Graph", "prize": "$5,000",
     "name": "Best Use of Composable or Standardized Graph Products",
     "need": ["Compose two or more of The Graph's products, or build on a standardized schema",
              "Consume live data from a Graph provider",
              "Public repo", "Demo video, 2-4 min"],
     "gate": ["graph_composed", "graph_live", "repo_public", "video"],
     "beats": ["money", "regraph", "index"]},
    {"id": "graph3", "sponsor": "The Graph", "prize": "$5,000",
     "name": "Best AI Tooling or AI Use Case with The Graph - Continuity",
     "need": ["The Graph is a load-bearing part of the project",
              "Consume live data via providers",
              "Meaningful work with the data: reasoning, decisions, automation",
              "Open-source code with README", "Demo video", "Select the Continuity pool"],
     "gate": ["graph_live", "graph_work", "repo_public", "video"],
     "beats": ["money", "agent", "regraph"]},
    {"id": "baz1", "sponsor": "Bazantic", "prize": "$1,000",
     "name": "Help an Agent Use Your Hackathon Project - Continuity",
     "need": ["A bazantic.com account", "An x402/MPP Gateway for the project",
              "A Recipe explaining when/why/how to use the service",
              "Show the improvement: raw API info vs the Recipe",
              "Screen recording", "The bazantic username in the submission"],
     "gate": ["baz_account", "baz_gateway", "baz_recipe", "video"],
     "beats": ["agent", "x402", "money"]},
    {"id": "baz2", "sponsor": "Bazantic", "prize": "$1,000",
     "name": "Best Recipe Using EthGlobal Hackathon Sponsor APIs",
     "need": ["A bazantic.com account", "An x402/MPP Gateway",
              "At least one OTHER service from Bazantic or a hackathon sponsor",
              "A recipe combining them in one working flow",
              "Screen recording of the completed task", "The bazantic username"],
     "gate": ["baz_account", "baz_gateway", "baz_recipe", "baz_second_service", "video"],
     "beats": ["money", "agent", "x402"]},
    {"id": "baz3", "sponsor": "Bazantic", "prize": "$1,000",
     "name": "Agentify a New API",
     "need": ["A bazantic.com account", "A Gateway for an API not previously on Bazantic",
              "A recipe using the new service with the hackathon project",
              "Screen recording", "The bazantic username"],
     "gate": ["baz_account", "baz_gateway", "baz_recipe", "video"],
     "beats": ["money", "agent", "x402"]},
]

# What each gate means in one line, for the failure message. A blocker a reader cannot act on is
# just bad news.
GATE_FIX = {
    "graph_composed": "compose 2+ Graph products — we read a published subgraph THROUGH Subgraph MCP",
    "graph_live": "web/data/demand.json must be read via subgraph-mcp — re-run with GRAPH_API_KEY set",
    "graph_work": "the data must drive reasoning/decisions, not just be displayed",
    "repo_public": "THE REPO IS PRIVATE. Every track here requires a public repo. `gh repo edit "
                   "--visibility public` (and check for secrets first)",
    "video": "record it — 2-4 min, 720p+, your own voice. `python3 pipeline/demo.py --track <id>`",
    "baz_account": "create a bazantic.com account and put the username in data/hackathon.json",
    "baz_gateway": "build the x402/MPP Gateway on bazantic.com for our API",
    "baz_recipe": "publish a Bazantic Recipe describing when/why/how to call it",
    # TRACK 2 ONLY, and it was missing from this table while the track read as clear. The recipe we
    # published binds three tools and all three are ours, which satisfies Tracks 1 and 3 and NOT
    # this one: it wants information moving between two services, with the result depending on both.
    "baz_second_service": "bind a SECOND service (a sponsor's, or The Graph's Subgraph MCP) into a "
                          "recipe so the answer depends on both — record it in data/hackathon.json "
                          "as bazantic_second_service",
}


def qualify(f=None):
    """Which gates we actually pass, checked rather than assumed.

    Offline-safe: everything here reads the repo or the published files. `repo_public` is the one
    that needs the network, so it degrades to None (unknown) rather than guessing — and a None gate
    is reported as UNKNOWN, never as a pass. A qualification matrix that resolves an unknown in our
    favour is worse than no matrix.
    """
    dem = load("demand.json")
    state = {}
    p = os.path.join(ROOT, "data", "hackathon.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                state = json.load(fh) or {}
        except (OSError, ValueError):
            state = {}
    via = (dem.get("via") or "")
    g = {
        "graph_composed": via == "subgraph-mcp" and bool(dem.get("source")),
        "graph_live": via == "subgraph-mcp" and bool((dem.get("economy") or {}).get("paid_usd")),
        # Reasoning over the data, not a passthrough: we join receipts to a catalogue, refuse to
        # attribute a shared address, and expose the result as an agent tool.
        "graph_work": bool(dem.get("paid_capabilities")) and os.path.exists(
            os.path.join(ROOT, "pipeline", "paid_demand.py")),
        "repo_public": _repo_public(),
        "video": bool(state.get("video_url")),
        "baz_account": bool(state.get("bazantic_username")),
        "baz_gateway": bool(state.get("bazantic_gateway")),
        "baz_recipe": bool(state.get("bazantic_recipe")),
        "baz_second_service": bool(state.get("bazantic_second_service")),
    }
    return g


def _repo_public():
    """None when we cannot tell. Never a guess."""
    try:
        out = subprocess.run(["gh", "repo", "view", "--json", "isPrivate"],
                             capture_output=True, text=True, timeout=25, cwd=ROOT)
        if out.returncode != 0:
            return None
        return not json.loads(out.stdout).get("isPrivate", True)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def fit():
    """The qualification matrix. Prints every blocker with the thing that clears it."""
    g = qualify()
    w = 92
    print("=" * w)
    print("  TRACK FIT — checked, not assumed")
    print("  requirements verified 13 Sep 2026 against ethglobal.com/events/ethonline2026/prizes")
    print("=" * w)
    blocked = 0
    for t in TRACKS:
        miss = [k for k in t["gate"] if g.get(k) is not True]
        unknown = [k for k in t["gate"] if g.get(k) is None]
        state = "QUALIFIES" if not miss else ("UNKNOWN" if miss == unknown else "BLOCKED")
        blocked += state != "QUALIFIES"
        print(f"\n  [{state:<9}] {t['sponsor']} {t['prize']} — {t['name']}")
        for n in t["need"]:
            print(f"      · {n}")
        for k in miss:
            mark = "?" if g.get(k) is None else "x"
            print(f"      {mark} {GATE_FIX[k]}")
    print("\n" + "=" * w)
    print(f"  {len(TRACKS) - blocked} of {len(TRACKS)} tracks clear today.")
    print("  Record blockers you have cleared in data/hackathon.json:")
    print('    {"bazantic_username": "...", "bazantic_gateway": "...", '
          '"bazantic_recipe": "...", "video_url": "..."}')
    print("=" * w)
    return 0


RULES = [
    "Between 2 and 4 minutes. Under or over is rejected outright.",
    "720p or higher. The upload fails below it.",
    "Your own voice. No text-to-speech, no AI voiceover.",
    "No music-over-text instead of talking.",
    "Screen recording, not a phone.",
    "Do not speed the video up to fit the limit.",
]


# THE BEAT A SPONSOR'S JUDGE IS ACTUALLY LOOKING FOR. The general script tells the product's story;
# a track submission has to additionally SHOW the thing the sponsor wrote down. For The Graph that is
# the composition running live — not a slide claiming it — and for Bazantic it is the Recipe doing
# something the raw API could not. Inserted as its own beat so it cannot be lost inside the narrative.
TRACK_BEAT = {
    "graph1": ("+0:40", "The composition, running",
               ["Terminal.", "Run:  GRAPH_API_KEY=<key> python3 pipeline/paid_demand.py",
                "Then scroll to 'Re-run it yourself' on /paid.html."],
               ["Two Graph products, composed. A subgraph published on The Graph Network, read "
                "through The Graph's own Subgraph MCP server — the same tool call any agent can "
                "make.",
                "That is live data from a Graph provider, refreshed nightly, not a snapshot.",
                "The page prints the endpoint, the tool and the query, and one command re-runs the "
                "whole hop from a clone. You check us rather than trusting our exporter."]),
    "graph3": ("+0:40", "What we do with the data",
               ["Show /paid.html, then the MCP tool answering."],
               ["The Graph is load-bearing for this feature: without it there is no page.",
                "And it is not a passthrough. We join receipts to a 12,656-row catalogue by exact "
                "host, refuse to attribute an address shared by several services, compute the "
                "distribution rather than the total, and expose the answer as an agent tool.",
                "A sum is the one statistic a concentrated economy always passes, so we never "
                "publish it alone."]),
    "baz1": ("+0:40", "The Recipe, against the raw API",
             ["Show the raw endpoint first, then the Bazantic Recipe doing the same job."],
             ["This is what an agent saw before: a URL and a JSON body it has to guess at.",
              "This is the Recipe: when to call it, why, and what the answer means.",
              "Same API. The difference is whether an agent can use it without being told."]),
    "baz2": ("+0:40", "Two services, one flow",
             ["Show the recipe combining tashan with the second service end to end."],
             ["Our catalogue supplies identity and quality. The second service supplies what we "
              "cannot measure. Neither half answers the question alone.",
              "One flow, one task completed, start to finish."]),
    "baz3": ("+0:40", "An API agents could not reach before",
             ["Show the Gateway, then an agent calling it."],
             ["The paid-demand signal exists nowhere else — no directory publishes which x402 "
              "services have actually been paid.",
              "It was a file and an MCP tool. Now it is a Bazantic Gateway, so any agent on the "
              "platform can ask it without knowing we exist."]),
}


def render(f, track=None):
    w = 92
    t = next((x for x in TRACKS if x["id"] == track), None) if track else None
    L = ["=" * w,
         "  THE DEMO — 3:30, read it while you record" if not t
         else f"  THE DEMO for {t['sponsor']} {t['prize']} — {t['name']}",
         f"  every figure below was read from web/data/ on {f['generated'] or 'an unknown date'}",
         "=" * w, ""]
    if t:
        g = qualify()
        L += ["  WHAT THIS JUDGE REQUIRES", ""]
        for need in t["need"]:
            L.append(f"    · {need}")
        miss = [k for k in t["gate"] if g.get(k) is not True]
        if miss:
            L += ["", "  !! NOT QUALIFYING YET — recording this does not fix these:", ""]
            L += [f"    {'?' if g.get(k) is None else 'x'} {GATE_FIX[k]}" for k in miss]
        L.append("")
    L += ["  BEFORE YOU RECORD", ""]
    L += [f"    [ ] {r}" for r in RULES]
    L += ["", f"    [ ] python3 pipeline/serve.py   ->  {PREVIEW}",
          "    [ ] python3 pipeline/demo.py --check   (fails if any number here has moved)", ""]
    seq = list(beats(f))
    if t and t["id"] in TRACK_BEAT:
        # After the product is established (beat 2) and before the money beat, so the sponsor's
        # requirement lands on a viewer who now knows what they are looking at.
        seq.insert(2, TRACK_BEAT[t["id"]])
    for clock, head, do, say in seq:
        L += ["-" * w, f"  {clock}  {head}", "-" * w, ""]
        for d in do:
            L.append(f"    DO    {d}")
        L.append("")
        for s in say:
            L.append(f"    SAY   {s}")
        L.append("")
    L += ["=" * w,
          "  Nothing here records the video. ETHGlobal requires a human voice, and the two rules",
          "  that close the loopholes (no sped-up video, no music-over-text) mean there is no",
          "  version of this a model can hand you finished.",
          "=" * w]
    return "\n".join(L)


def check(f, quiet=False):
    """Refuse the script if it cannot be spoken truthfully. Run it before hitting record.

    `quiet` is for the selftest, which deliberately feeds it a broken fixture: printing that
    fixture's FAIL lines into a green suite run is how a reader learns to skim past the word FAIL,
    and this repo has already paid for that lesson twice.
    """
    bad = []
    need = ("measured", "tracked", "paid_usd", "receivers_paid", "median_usd")
    for k in need:
        if f.get(k) in (None, 0):
            bad.append(f"{k} is missing from the published data — run pipeline/run.py --site")
    if f.get("inv") is None:
        bad.append("could not read this machine's agent config — the opening beat has no numbers")
    if not f.get("top"):
        bad.append("no capability has an attributable payment — the 1:10 beat has no table to land on")
    if f.get("ours") is None:
        bad.append("pkg:tashan-cli is not in the export — the 'we are in our own table' beat is false")
    if not quiet:
        for b in bad:
            print("  FAIL " + b)
        print("  ok   every figure in the script is live" if not bad
              else "\nDEMO SCRIPT WOULD BE STALE")
    return 1 if bad else 0


def _selftest():
    assert money(166660.9964) == "$166,661", money(166660.9964)
    assert money(0.5125) == "$0.51"
    assert money(0.0) == "$0.00"
    assert money(None) is None
    # A missing inventory must degrade to a stage direction, never to an invented number.
    f = {"measured": 1, "tracked": 2, "generated": "2026-09-13", "scanned": 0, "paid_usd": 1.0,
         "payments": None, "receivers_paid": 1, "receivers_never": 0, "receivers_listed": 1,
         "median_usd": 0.5, "top": None, "ours": None, "inv": None}
    txt = render(f)
    assert "could not read this machine's config" in txt
    assert "$0" not in txt.split("SAY")[1]          # no fabricated inventory figures
    assert check(dict(f), quiet=True) == 1           # and --check refuses to let it be recorded
    # With everything present the beats speak real numbers and nothing is a placeholder.
    f2 = dict(f, inv={"servers": 12, "plugins": 11, "skills": 241, "projects": 52, "unowned": 113},
              top={"name": "blockrun-mcp", "paid_usd": 166661.0, "paid_calls": 8718793,
                   "tashan_score": 68.0},
              ours={"id": "pkg:tashan-cli", "paid_usd": 0.0})
    t2 = render(f2)
    assert "113 of those skills are owned by no plugin" in t2
    assert "$166,661 across 8,718,793 calls" in t2, t2
    # An absent figure must never reach the page as a placeholder inside a spoken number phrase —
    # em-dashes in the prose itself are fine, "across — payments" is not. `payments` is None in this
    # fixture, and the clause that would have spoken it has to be omitted whole.
    assert "across — payments" not in t2 and "— settled" not in t2, t2
    assert "payments." not in t2, "the payments clause must vanish when the figure is absent"
    assert check(dict(f2), quiet=True) == 0
    # ---- the qualification matrix must never round in our favour --------------------------------
    # docs/SUBMISSION.md claimed all three Bazantic tracks on the strength of our own MCP server,
    # while every one of them requires artifacts on bazantic.com we have never had. So the gates are
    # tested for the two ways a fit check goes wrong: a missing gate reading as a pass, and an
    # UNKNOWN (the network check we cannot always make) reading as a pass.
    for t in TRACKS:
        assert t["gate"], f"{t['id']} has no gate — a track that cannot fail is not a check"
        assert all(k in GATE_FIX for k in t["gate"]), f"{t['id']} names a gate with no fix line"
        assert t["need"], f"{t['id']} records no requirement"
    import io, contextlib
    for fake, expect in (({k: False for k in GATE_FIX}, "BLOCKED"),   # checked and absent
                         ({k: True for k in GATE_FIX}, "QUALIFIES")):  # checked and present
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            _real, globals()["qualify"] = qualify, (lambda _f=None, _g=fake: dict(_g))
            try:
                fit()
            finally:
                globals()["qualify"] = _real
        assert expect in buf.getvalue(), f"fit() did not report {expect} for {fake and 'all-pass'}"
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        _real, globals()["qualify"] = qualify, (lambda _f=None: {k: None for k in GATE_FIX})
        try:
            fit()
        finally:
            globals()["qualify"] = _real
    out = buf.getvalue()
    assert "QUALIFIES" not in out, "an UNKNOWN gate must never be reported as qualifying"
    assert "UNKNOWN" in out, "an unknowable gate must say so rather than pick a side"
    # A track script must print the sponsor's own requirements and its unmet gates.
    with contextlib.redirect_stdout(io.StringIO()):
        _real, globals()["qualify"] = qualify, (lambda _f=None: {k: False for k in GATE_FIX})
        try:
            s = render(f2, "graph1")
        finally:
            globals()["qualify"] = _real
    assert "NOT QUALIFYING YET" in s and "Consume live data from a Graph provider" in s
    assert "Two Graph products, composed" in s, "the track beat did not make it into the script"
    print("ok — demo script: figures derived, absences stated, --check refuses a stale read")
    print("ok — track fit: no gate rounds in our favour, unknown never reads as qualifying")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--serve", action="store_true", help="start the local preview first")
    ap.add_argument("--check", action="store_true", help="exit 1 if any figure would be stale")
    ap.add_argument("--fit", action="store_true",
                    help="which prize tracks we actually qualify for, and what blocks the rest")
    ap.add_argument("--track", choices=[t["id"] for t in TRACKS],
                    help="tune the script to one sponsor's requirements")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if a.fit:
        return fit()
    f = facts()
    if a.check:
        return check(f)
    if a.serve:
        subprocess.Popen([sys.executable, os.path.join(ROOT, "pipeline", "serve.py")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  preview starting -> {PREVIEW}\n")
    print(render(f, a.track))
    return 0


if __name__ == "__main__":
    sys.exit(main())
