#!/usr/bin/env python3
"""capability_id() — the config parser that decides what a row IS.

A wrong id is worse than a missing one: it invents a capability AND loses the real one.
These cases are the shapes that actually appeared in public configs.

Run: python3 tests/test_scrape.py
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scraper"))
from scrape import capability_id

CASES = [
    # (label, entry, expected_id)
    # A Windows volume mount used to yield the DRIVE LETTER as the image: ids `docker:C` / `docker:D`
    # were in the database, and the real image in those configs was never counted.
    ("windows mount does not become the image",
     {"command": "docker", "args": ["run", "-i", "--rm", "-v", "C:/Users/me/data:/data",
                                    "ghcr.io/acme/thing:1.2"]}, "docker:ghcr.io/acme/thing"),
    ("backslash windows mount",
     {"command": "docker", "args": ["run", "-v", "D:\\work\\x:/x", "mcp/sequentialthinking"]},
     "docker:mcp/sequentialthinking"),
    ("posix mount does not become the image",
     {"command": "docker", "args": ["run", "-i", "--rm", "-v", "/home/me/d:/d",
                                    "ghcr.io/github/github-mcp-server"]},
     "docker:ghcr.io/github/github-mcp-server"),
    ("npx scoped package",
     {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"]},
     "pkg:@modelcontextprotocol/server-filesystem"),
    ("remote url keys on the host",
     {"url": "https://mcp.example.com/v1/sse?k=1"}, "url:mcp.example.com"),
    # an mcp-named arg is claimed by the package branch first, whatever the command is
    ("uvx mcp-named package keys as a package",
     {"command": "uvx", "args": ["mcp-server-git"]}, "pkg:mcp-server-git"),
    ("uvx non-mcp package falls through to the python branch",
     {"command": "uvx", "args": ["some-tool"]}, "py:some-tool"),
]

fail = 0
for label, entry, want in CASES:
    got, _kind = capability_id("x", entry)
    ok = got == want
    if not ok:
        fail = 1
    print(("  ok   " if ok else "  FAIL ") + label + ("" if ok else f"  got {got!r} want {want!r}"))

# A config that mounts a volume but names no image must not invent one. Falling through to the
# `key:` convention is correct; producing `docker:C` is the bug.
import re as _re
for junk_entry in ({"command": "docker", "args": ["run", "-v", "C:/x:/x"]},
                   {"command": "docker", "args": ["run", "-v", "D:/y:/y"]}):
    got, _ = capability_id("x", junk_entry)
    ok = got is None or not _re.match(r"^docker:[A-Za-z]$", got)
    if not ok:
        fail = 1
    print(("  ok   " if ok else "  FAIL ") + f"mount-only config invents no image id ({got!r})")

print("SCRAPE PARSER OK" if not fail else "SCRAPE PARSER FAILED")
sys.exit(fail)
