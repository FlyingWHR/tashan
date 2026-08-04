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

THE FIX IS NOT IN THIS REPO. Bot Fight Mode is a zone-level Cloudflare setting; the deploy token
carries zone:read, not zone:write. Turn it off at dash.cloudflare.com -> tashan.sh -> Security ->
Bots. Free-tier Bot Fight Mode cannot be scoped by path, so it is on or off; Super Bot Fight Mode
allows an exception for /v0.1/* and /data/* if the protection is wanted elsewhere.

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

print("# every advertised agent surface answers a stdlib Python client")
for path, why in PATHS:
    code = status(path)                       # deliberately the DEFAULT urllib User-Agent
    ok(f"{path} — {why}", code == 200,
       f"HTTP {code} to a default urllib client. Bot Fight Mode is refusing the agents we invite.")

print()
print("# and the same surfaces answer the other clients agents actually use")
for ua in ("curl/8.4.0", "node-fetch/3.3.2", "Go-http-client/2.0", "ChatGPT-User/1.0"):
    code = status("/v0.1/scores", ua=ua)
    ok(f"/v0.1/scores answers {ua}", code == 200, f"HTTP {code}")

print()
print("AGENT ACCESS OK" if not fail else "AGENT ACCESS FAILED")
sys.exit(fail)
