#!/usr/bin/env python3
"""Every `npx …` invocation we publish must name a package that actually resolves to US.

This has now been wrong twice, both times shipped:

  1. `npx -y tashan-mcp` — documented in the plugin manifest and the site. No package of that name
     has ever existed; npm would 404. `tashan-mcp` is one of our BIN names, and npx resolves
     PACKAGE names, not bins.
  2. `npx tashan …` — the entire CLI documentation, every install snippet, and the Claude Code
     plugin's mcpServers args. `tashan` on npm was registered in 2020 by an unrelated project and
     ships no bin at all, so the command downloaded a stranger's package and died with
     "could not determine executable to run".

Both are invisible to every other test: the CLI works perfectly when run from a checkout, and the
HTML is well-formed. The failure only appears on a user's machine, at the first command they ever
run, which is the worst possible place to find it.

The rule: any npx invocation naming a package that starts with "tashan" must name EXACTLY the
`name` in cli/package.json. Bin names are checked separately — they may differ from the package,
but only the package name may appear after npx.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = json.load(open(os.path.join(ROOT, "cli", "package.json")))
NAME, BINS = PKG["name"], set(PKG.get("bin", {}))

# Source we hand-write. Generated pages (web/capability, web/category, web/skills) come from the
# generators, which ARE checked here — fixing a generator fixes its thousands of outputs.
SCAN_DIRS = ["cli", "docs", "pipeline", "plugin", ".claude-plugin", "tests"]
SCAN_EXT = (".mjs", ".js", ".py", ".md", ".json", ".html", ".txt", ".sh")
SCAN_FILES = ["CLAUDE.md", "PROJECT.md", "README.md"]

# `npx tashan-cli mcp`, `npx -y tashan-cli doctor`
NPX = re.compile(r"npx\s+(?:-y\s+|--yes\s+)?(@?[\w.@/-]+)")
# the JSON form the shell regex cannot see: "args": ["-y", "tashan-cli", "mcp"]
ARGS = re.compile(r'"(?:-y|--yes)"\s*,\s*"(@?[\w.@/-]+)"')


def files():
    for f in SCAN_FILES:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            yield p
    for d in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, d)):
            dirnames[:] = [x for x in dirnames if x not in ("node_modules", "__pycache__", ".git")]
            for fn in filenames:
                if fn.endswith(SCAN_EXT):
                    yield os.path.join(dirpath, fn)
    for fn in sorted(os.listdir(os.path.join(ROOT, "web"))):     # top-level pages
        if fn.endswith(".html"):
            yield os.path.join(ROOT, "web", fn)
    # Hand-written non-HTML we publish — llms.txt, robots.txt, and the installable skill. These
    # live in SUBdirectories, which the listdir above cannot see; web/skill/SKILL.md sat here with
    # the dead package name after every other file had been fixed. The thousands of generated
    # .html pages are deliberately not walked: they come from the generators, already scanned.
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "web")):
        dirnames[:] = [x for x in dirnames if x not in ("data", "assets", "capability",
                                                        "category", "skills")]
        for fn in filenames:
            if fn.endswith((".md", ".txt")):
                yield os.path.join(dirpath, fn)


def main():
    bad = []
    for path in files():
        rel = os.path.relpath(path, ROOT)
        if rel == os.path.join("tests", "test_pkg_name.py"):
            continue          # this file quotes the broken names deliberately, to explain them
        try:
            src = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(src.split("\n"), 1):
            for rx in (NPX, ARGS):
                for pkg in rx.findall(line):
                    # A VERSION SPECIFIER IS PART OF THE SYNTAX, NOT PART OF THE NAME.
                    # `npx tashan-cli@latest` failed this test as "no such package", which is the
                    # opposite of true — @latest is exactly what you type to get past a cached older
                    # copy, which is the whole point when verifying a fresh publish. Strip a
                    # trailing @spec (never the leading @ of a scope) and compare the name itself.
                    at = pkg.rfind("@")
                    if at > 0:
                        pkg = pkg[:at]
                    if not pkg.lower().startswith("tashan"):
                        continue          # npx-ing someone else's package is normal, that is the product
                    if pkg == NAME:
                        continue
                    why = ("that is a BIN name, not a package — npx resolves packages"
                           if pkg in BINS else "no such package, or not ours")
                    bad.append((rel, lineno, pkg, why))

    if not bad:
        print(f"  ok    every npx invocation names {NAME!r} (the published package)")
        return 0

    print(f"  FAIL  {len(bad)} npx invocation(s) name a package that is not {NAME!r}:")
    for rel, lineno, pkg, why in bad:
        print(f"        {rel}:{lineno}  npx … {pkg}   — {why}")
    print(f"\n        Users hit this on their very first command. Either publish under the name")
    print(f"        used above, or change these to {NAME!r}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
