#!/usr/bin/env python3
"""The "✓ Official" badge is an endorsement claim. It must be provable from the namespace.

This shipped as a substring search over `npm_pkg + " " + source_repo`, so anything whose name merely
contained the protocol's name inherited Anthropic's badge:

    @atomicmail/mcp-modelcontextprotocol   ->  "✓ Official from Anthropic"
    @perplexity-ai/mcp-server              ->  "✓ Official from Anthropic"   (via its source_repo)

Neither is Anthropic's. We were publishing an endorsement that nobody gave, on the same board that
refuses to call a lookalike package a typosquat because that is a claim we cannot support. Refusing
to accuse while happily vouching is the worse half of that trade.

Ownership is a namespace fact: the package sits in the organisation's own npm scope, or the
repository is owned by the organisation's own GitHub account. Matching is on the exact namespace
segment — the scope before the first "/", and the owner before the first "/".

Run: python3 tests/test_official.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))


from build import official_of        # module-level so the test exercises the shipped function


CASES = [
    # (npm_pkg, source_repo, expected org or None)
    ("@modelcontextprotocol/server-filesystem", "modelcontextprotocol/servers", "Anthropic"),
    ("@anthropic-ai/claude-code",               "anthropics/claude-code",       "Anthropic"),
    (None,                                      "anthropics/skills",            "Anthropic"),
    ("@openai/agents",                          "openai/openai-agents-js",      "OpenAI"),
    ("@azure/mcp",                              "microsoft/mcp",                "Microsoft"),
    (None,                                      "MicrosoftDocs/mcp",            "Microsoft"),
    ("chrome-devtools-mcp",                     "ChromeDevTools/chrome-devtools-mcp", "Google"),
    (None,                                      "gemini-cli-extensions/looker", "Google"),

    # --- the regressions this exists to prevent -------------------------------------------------
    ("@atomicmail/mcp-modelcontextprotocol", "atomic-mail/mcp", None),
    ("@perplexity-ai/mcp-server",            "modelcontextprotocol-servers/x", None),
    ("mcp-server-modelcontextprotocol",      "randomuser/thing",  None),
    ("my-anthropic-wrapper",                 "someone/anthropic-tools", None),
    ("google-maps-mcp",                      "notgoogle/google-maps-mcp", None),
    ("azure-helper",                         "contoso/azure-helper", None),
    ("openai-proxy",                         "hobbyist/openai-proxy", None),
    # scope lookalikes: the segment must match exactly, not merely start the same way
    ("@modelcontextprotocol-evil/server",    "attacker/server", None),
    (None,                                   "microsoft-fanclub/tools", None),
    (None,                                   "google-unofficial/thing", None),
    # empty / missing identifiers must never resolve to an org
    (None, None, None),
    ("", "", None),
]


def main():
    fail = 0
    for pkg, repo, want in CASES:
        got = official_of(pkg, repo)
        ok = got == want
        if not ok:
            fail = 1
        label = f"{(pkg or '—')[:44]:46} {(repo or '—')[:36]:38}"
        print(("  ok   " if ok else "  FAIL ") + label
              + f"-> {got!r}" + ("" if ok else f"   want {want!r}"))

    # And the shipped export must be clean: every badge on disk has to survive the same rule.
    import json
    path = os.path.join(ROOT, "web", "data", "capabilities.json")
    if os.path.exists(path):
        caps = json.load(open(path, encoding="utf-8"))["capabilities"]
        bad = [c for c in caps if c.get("official")
               and official_of(c.get("npm_pkg"), c.get("source_repo")) != c["official"]]
        if bad:
            fail = 1
            print(f"  FAIL  {len(bad)} exported badge(s) do not survive the rule, e.g. "
                  + ", ".join(c["name"] for c in bad[:3]))
        else:
            n = sum(1 for c in caps if c.get("official"))
            print(f"  ok   all {n} badges in the shipped export are namespace-provable")

    print("OFFICIAL BADGE FAILED" if fail else "ok — official badge (namespace-provable only)")
    return fail


if __name__ == "__main__":
    sys.exit(main())
