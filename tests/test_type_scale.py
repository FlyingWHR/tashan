#!/usr/bin/env python3
"""Type scale: every font-size comes from the scale, and nothing renders under 12px.

The stylesheet had grown 42 distinct font sizes. Six were under 10px and roughly forty under 12px,
which is the point where text stops being comfortably readable — the category rail was 13.8px rows
under a 10.6px heading, and the "v2 · public-signal" chip in the nav was 9.9px.

Two rules, both cheap to break by accident:

  1. Every font-size in CSS is a var(--fs-*) or one of the explicitly allowed exceptions (fluid
     clamps for display type, the 16px body root). A new hand-picked `.83rem` is how a scale rots
     back into 42 values.
  2. No scale step is under 12px, and no em-relative size can drop a step below it. `kbd` was
     .9em inside a 12px parent, rendering 10.8px — the floor has to survive nesting.

Run: python3 tests/test_type_scale.py
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "web", "css")
FLOOR_PX = 12.0

# Display type is deliberately fluid; the body root is the anchor the rem scale is built on.
ALLOWED = re.compile(r"^(var\(--fs-[a-z0-9]+\)|var\(--text-(display|h2|lead)\)|clamp\([^)]*\)|16px|inherit|1em)$")


def declarations():
    for path in sorted(glob.glob(os.path.join(CSS, "*.css"))):
        src = open(path, encoding="utf-8").read()
        for m in re.finditer(r"font-size:\s*([^;}\n]+)", src):
            line = src[:m.start()].count("\n") + 1
            yield os.path.relpath(path, ROOT), line, m.group(1).strip()


def scale_steps(src):
    return {n: float(v) * 16 for n, v in re.findall(r"--fs-([a-z0-9]+):\s*([\d.]+)rem", src)}


def undefined_tokens():
    """Every var(--x) must resolve, or the browser drops the WHOLE declaration in silence.

    Found the hard way: the spacing scale ran 1,2,3,4,6,8,12,16,24 — no step 5 — while thirteen
    rules asked for var(--sp-5). All thirteen were discarded, including `.hero__sub`'s and
    `.hero__rot`'s top margin, so the homepage subtitle sat flush against the headline. Nothing
    errors, nothing warns, and the CSS reads correctly; the only symptom is spacing that looks a
    bit off. `--line` was the same story: one border-top that never drew.

    A var() with a fallback — var(--amber, #e0a83b) — is safe by construction and would pass, but
    it is also three copies of a hex, which is how this repo's other bugs started. Define the token.
    """
    src = ""
    for path in sorted(glob.glob(os.path.join(CSS, "*.css"))):
        src += open(path, encoding="utf-8").read()
    defined = {m.group(1) for m in re.finditer(r"(--[a-z0-9-]+)\s*:", src)}
    bad = []
    for m in re.finditer(r"var\(\s*(--[a-z0-9-]+)\s*([,)])", src):
        name, nxt = m.group(1), m.group(2)
        if name not in defined and nxt == ")":
            n = len(re.findall(r"var\(\s*" + re.escape(name) + r"\s*\)", src))
            bad.append(f"var({name}) is never defined — {n} declaration(s) silently dropped")
    return sorted(set(bad))


def main():
    fail = []
    site = open(os.path.join(CSS, "site.css"), encoding="utf-8").read()

    fail.extend(undefined_tokens())

    steps = scale_steps(site)
    if not steps:
        print("  FAIL  no --fs-* scale found in site.css")
        return 1
    for name, px in sorted(steps.items(), key=lambda kv: kv[1]):
        if px < FLOOR_PX:
            fail.append(f"scale step --fs-{name} is {px:.1f}px, under the {FLOOR_PX:.0f}px floor")

    off = []
    for rel, line, val in declarations():
        if not ALLOWED.match(val):
            off.append(f"{rel}:{line}  font-size: {val}")
    # A handful of one-off display sizes predate the scale and are larger than any step, so they are
    # listed rather than silently tolerated: they are safe, but they should not multiply.
    # The boundary matters: an unanchored number matched "61rem" inside ".61rem" and waved a 9.8px
    # size through as display type — the guard reported green on exactly what it exists to catch.
    NUM = re.compile(r"(?<![.\d])(\d+\.?\d*)rem")
    big = [o for o in off if NUM.search(o) and float(NUM.search(o).group(1)) >= 1.1]
    hard = [o for o in off if o not in big]
    for o in hard:
        fail.append("off-scale font-size (add it to the scale, or use a step): " + o)

    # em-relative sizes nest, so a step can still render under the floor
    for rel, line, val in declarations():
        m = re.match(r"^([\d.]+)em$", val)
        if m and float(m.group(1)) < 1:
            fail.append(f"{rel}:{line}  font-size: {val} — em-relative, drops below its parent step "
                        f"(kbd at .9em inside a 12px parent rendered 10.8px)")

    # inline styles in hand-written pages and generators bypass the stylesheet entirely
    for f in sorted(glob.glob(os.path.join(ROOT, "web", "*.html")) +
                    glob.glob(os.path.join(ROOT, "pipeline", "*.py"))):
        for m in re.finditer(r"font-size:\s*([.\d]+)(rem|px)", open(f, encoding="utf-8").read()):
            px = float(m.group(1)) * (16 if m.group(2) == "rem" else 1)
            if px != 16:
                fail.append(f"{os.path.relpath(f, ROOT)}  inline font-size: {m.group(0)} "
                            f"({px:.1f}px) — use a var(--fs-*) step")

    if fail:
        print(f"  FAIL  {len(fail)} type-scale violation(s):")
        for f_ in fail[:25]:
            print("        " + f_)
        if len(fail) > 25:
            print(f"        … and {len(fail) - 25} more")
        return 1

    print(f"  ok    type scale: {len(steps)} steps, smallest {min(steps.values()):.0f}px, "
          f"no size under the {FLOOR_PX:.0f}px floor")
    if big:
        print(f"        ({len(big)} large one-off display size(s) tolerated: "
              + ", ".join(b.split("font-size: ")[1] for b in big) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
