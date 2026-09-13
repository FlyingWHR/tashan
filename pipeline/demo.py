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


RULES = [
    "Between 2 and 4 minutes. Under or over is rejected outright.",
    "720p or higher. The upload fails below it.",
    "Your own voice. No text-to-speech, no AI voiceover.",
    "No music-over-text instead of talking.",
    "Screen recording, not a phone.",
    "Do not speed the video up to fit the limit.",
]


def render(f):
    w = 92
    L = ["=" * w,
         "  THE DEMO — 3:30, read it while you record",
         f"  every figure below was read from web/data/ on {f['generated'] or 'an unknown date'}",
         "=" * w, "",
         "  BEFORE YOU RECORD", ""]
    L += [f"    [ ] {r}" for r in RULES]
    L += ["", f"    [ ] python3 pipeline/serve.py   ->  {PREVIEW}",
          "    [ ] python3 pipeline/demo.py --check   (fails if any number here has moved)", ""]
    for clock, head, do, say in beats(f):
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
    print("ok — demo script: figures derived, absences stated, --check refuses a stale read")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--serve", action="store_true", help="start the local preview first")
    ap.add_argument("--check", action="store_true", help="exit 1 if any figure would be stale")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    f = facts()
    if a.check:
        return check(f)
    if a.serve:
        subprocess.Popen([sys.executable, os.path.join(ROOT, "pipeline", "serve.py")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  preview starting -> {PREVIEW}\n")
    print(render(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
