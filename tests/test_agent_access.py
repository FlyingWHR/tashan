#!/usr/bin/env python3
"""The endpoints we advertise to agents must actually answer agents.

llms.txt, the pricing page and for-hosts all say the same thing: no key, no signup, suitable for
direct agent use. Then Cloudflare's Bot Fight Mode returned 403 to any request whose User-Agent was
`Python-urllib/3.x` — the DEFAULT of the most common way to fetch a URL in Python, and a very common
path for agents, crawlers and LLM tooling. Measured 5 Aug 2026:

    UA: (none)               200
    UA: curl/8.4.0           200
    UA: Python-urllib/3.14   403      <- and this is what urlopen(url) sends
    affected: / · /llms.txt · /v0.1/scores · /data/index.json · /capability/*.md   ALL of them

An agent that gets a 403 on its first request does not retry with a nicer header. It concludes the
service is unavailable and stops asking — which is the exact failure the distribution thesis cannot
survive, and it is invisible from a browser.

IT IS NOT OUR SETTING. IT IS CLOUDFLARE, NETWORK-WIDE. Measured 8 Aug 2026 against third-party
sites, which is the test that should have been run first:

    UA                     tashan.sh   pages.dev   cloudflare.com   discord.com
    Python-urllib/3.14     403 1010    403 1010    403 1010         403 1010
    python-requests/2.31   200         200         -                -
    curl/8.4.0             200         200         200              200

Cloudflare refuses the literal string "Python-urllib" everywhere it sits in front of. Bot Fight Mode
and Browser Integrity Check were both turned off here and the 403s did not move, because neither was
ever the cause — error 1010 was read as "Browser Integrity Check" from the code alone and cost two
days of dashboard hunting. Nothing on this account, and nothing in this repo, can change it.

WHICH NARROWS THE PROBLEM TO ALMOST NOTHING. Only `urllib.request.urlopen()` WITH ITS DEFAULT HEADER
is refused. `requests` — what nearly every Python integration actually uses — gets 200, as do curl,
node-fetch, Go and every named AI crawler. So the fix is not a setting, it is to stop publishing a
snippet nobody should ship anyway: a one-line User-Agent makes urllib work, and any client that
identifies itself is fine.

Nothing in `_headers`, `functions/`, or the deploy reaches this. It is one toggle in the dashboard.

Network test. Skips (does not fail) when the site is unreachable, so it never breaks an offline run.

Run: python3 tests/test_agent_access.py
"""
import sys, urllib.error, urllib.request

BASE = "https://tashan.sh"
# The surfaces we tell agents to use, in the words we use to tell them.
PATHS = [
    ("/v0.1/scores", "the compact score lookup llms.txt points agents at"),
    ("/v0.1/servers", "the MCP-registry-shaped feed for hosts"),
    ("/llms.txt", "the answer-engine convention file"),
    ("/data/index.json", "what the published CLI reads on every run"),
    ("/capability/pkg-tavily-mcp.md", "the plain-markdown dossier tier"),
]
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


def status(path, ua=None):
    """ua=None means urllib's DEFAULT header — the case that was broken."""
    req = urllib.request.Request(BASE + path)
    if ua:
        req.add_header("User-Agent", ua)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


probe = status("/llms.txt", ua="tashan-selftest/1.0")
if probe is None:
    print("  -- site unreachable, skipping agent-access checks (offline run)")
    sys.exit(0)

print("# every advertised agent surface answers a client that identifies itself")
# `requests` rather than bare urllib: Cloudflare refuses the literal "Python-urllib" UA across its
# whole network, on cloudflare.com and discord.com too, so asserting it here would fail forever on
# something no setting of ours controls. What matters is that a normal Python client works.
for path, why in PATHS:
    code = status(path, ua="python-requests/2.31.0")
    ok(f"{path} — {why}", code == 200,
       f"HTTP {code} to a self-identifying Python client. THIS one is ours to fix.")

print()
print("# and the same surfaces answer the other clients agents actually use")
for ua in ("curl/8.4.0", "node-fetch/3.3.2", "Go-http-client/2.0", "ChatGPT-User/1.0"):
    code = status("/v0.1/scores", ua=ua)
    ok(f"/v0.1/scores answers {ua}", code == 200, f"HTTP {code}")

print()
print("# the answer engines can read us — this is the citation path, and it is separate")
# MEASURED 6 Aug 2026: every named crawler gets 200 and only the generic Python UA is refused. The
# distinction decides what to worry about. A blanket "agents are blocked" reading of the failures
# above is wrong and was briefly published in docs/AGENT-TRAFFIC.md: GEO is unobstructed, and what
# Bot Fight Mode costs us is the decision-time path — a tool call, a CI script, an integration
# someone writes after reading the outreach email. If one of these ever flips to 403, that IS the
# emergency, because it is the whole distribution thesis.
CRAWLERS = {
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Google-Extended": "Mozilla/5.0 (compatible; Google-Extended/1.0)",
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.1; +https://openai.com/gptbot",
    "OAI-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot",
    "ClaudeBot": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
}
for name, ua in CRAWLERS.items():
    codes = {p: status(p, ua=ua) for p in ("/", "/methodology.html", "/llms.txt")}
    ok(f"{name} can read the pages it would cite", set(codes.values()) == {200},
       ", ".join(f"{p} {c}" for p, c in codes.items() if c != 200))

print()
print("AGENT ACCESS OK" if not fail else "AGENT ACCESS FAILED")
sys.exit(fail)
