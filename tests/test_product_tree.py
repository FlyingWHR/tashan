#!/usr/bin/env python3
"""docs/PRODUCT-TREE.md must describe every surface that exists, and describe none that don't.

Two days of polish kept turning up the same shape of bug: a label disagreeing with the board it
belonged to, a sort reading a renamed column, a hub table with a different row anatomy from the
Index, 68 hub pages with no index page, a rename applied to the schema and to no prose. None were
hard to SEE. They were hard to LOOK FOR, because nothing enumerated the surfaces to check.

This asserts the enumeration stays honest:

  1. every hand-written route on disk has a purpose written for it (a page nobody can describe in
     one line should not exist)
  2. the tree names no route that has been deleted
  3. every non-page surface it claims — CLI, MCP server, paid API, webhook, gate, plugin — exists
  4. the tree is not stale: page count and generated-tree counts match disk

Run: python3 tests/test_product_tree.py
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE = os.path.join(ROOT, "docs", "PRODUCT-TREE.md")
WEB = os.path.join(ROOT, "web")


def main():
    if not os.path.exists(TREE):
        print("  FAIL  docs/PRODUCT-TREE.md missing — run python3 pipeline/gen_product_tree.py")
        return 1
    doc = open(TREE, encoding="utf-8").read()
    fail = []

    # `*` excludes the generated-tree rows (/capability/*.html), which are patterns covering
    # thousands of pages, not routes — the first cut compared them against disk as if each were a
    # single file and reported all four as deleted.
    listed = {r for r in re.findall(r"^\| `(/[^`]+\.html)`", doc, re.M) if "*" not in r}
    on_disk = {"/" + os.path.basename(p) for p in glob.glob(os.path.join(WEB, "*.html"))}

    for route in sorted(on_disk - listed):
        fail.append(f"{route} exists on disk but is not in the tree — add it to PURPOSE in "
                    f"pipeline/gen_product_tree.py")
    for route in sorted(listed - on_disk):
        fail.append(f"{route} is in the tree but not on disk — the page was deleted, the entry was not")

    for m in re.finditer(r"^\| `(/[^`]+)`[^|]*\|([^|]*)\|", doc, re.M):
        if "UNDESCRIBED" in m.group(2):
            fail.append(f"{m.group(1)} has no purpose written")

    # every non-page surface the tree claims must actually be there
    for m in re.finditer(r"^\| `([^`]+)`(\s+\*\*MISSING\*\*)?\s*\|", doc, re.M):
        path, missing = m.group(1), m.group(2)
        if path.startswith("/"):
            continue
        if missing or not os.path.exists(os.path.join(ROOT, path)):
            fail.append(f"the tree claims a surface that does not exist: {path}")

    # staleness: the generated-tree counts are the fastest thing to drift
    for pattern, count in re.findall(r"^\| `(/\w+)/\*\.html` \| ([\d,]+) \|", doc, re.M):
        d = os.path.join(WEB, pattern.strip("/"))
        actual = len(glob.glob(os.path.join(d, "*.html"))) if os.path.isdir(d) else 0
        if actual != int(count.replace(",", "")):
            fail.append(f"{pattern}/*.html says {count} pages, disk has {actual:,} — tree is stale, "
                        f"regenerate with python3 pipeline/gen_product_tree.py")

    if fail:
        print(f"  FAIL  {len(fail)} product-tree problem(s):")
        for f in fail[:20]:
            print("        " + f)
        if len(fail) > 20:
            print(f"        … and {len(fail) - 20} more")
        return 1

    print(f"  ok    product tree: {len(listed)} routes described, non-page surfaces present, "
          f"counts match disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
