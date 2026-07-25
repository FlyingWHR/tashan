#!/usr/bin/env python3
"""tashan — generate the social share card (web/assets/og.png, 1200x630) from the product screenshot.

Why this exists: every page had og:title/og:description but NO og:image, so shared links rendered as a
bare text stub on X/Slack/LinkedIn/Discord and Google had no image to pull. An SVG won't do — the social
crawlers don't rasterise SVG — so this needs a real PNG.

Why hand-rolled: the project is stdlib-only by design (no pip, no Pillow). PNG is tractable: zlib for the
pixel stream + the five per-scanline filter types. This decodes the screenshot, crops a window, and
re-encodes with filter type 0. Truthful by construction — it's an actual screenshot of the product, not
a mocked-up card.

Usage:  python3 pipeline/gen_og.py [--src FILE] [--top N]
        --top is the y offset of the crop window (default picks the hero band).
Only supports what we feed it: 8-bit colour type 2 (RGB) or 6 (RGBA), non-interlaced.
"""
import os, struct, sys, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "brand", "screens", "home.png")
OUT = os.path.join(ROOT, "web", "assets", "og.png")
OG_W, OG_H = 1200, 630


def read_png(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("not a PNG: " + path)
    pos, idat, hdr = 8, [], None
    while pos < len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif typ == b"IDAT":
            idat.append(body)
        elif typ == b"IEND":
            break
        pos += 12 + ln                       # len + type + body + crc
    w, h, depth, ctype, comp, filt, interlace = hdr
    if depth != 8 or ctype not in (2, 6) or interlace != 0:
        raise SystemExit(f"unsupported PNG (depth={depth} colortype={ctype} interlace={interlace})")
    nch = 3 if ctype == 2 else 4
    raw = zlib.decompress(b"".join(idat))
    stride = w * nch
    rows, prev, p = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        # undo the per-scanline filter (PNG spec 9.2); a=left, b=up, c=up-left
        if f == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                c = prev[i - nch] if i >= nch else 0
                b = prev[i]
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif f != 0:
            raise SystemExit("bad filter type %d" % f)
        rows.append(line); prev = line
    return w, h, nch, rows


def write_png(path, w, h, rows_rgb):
    def chunk(typ, body):
        return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(r) for r in rows_rgb)      # filter type 0 on every scanline
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    open(path, "wb").write(png)
    return len(png)


def main():
    src, top = SRC, None
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--src" and i + 1 < len(a): src = a[i + 1]
        if x == "--top" and i + 1 < len(a): top = int(a[i + 1])
    w, h, nch, rows = read_png(src)
    # crop window: centred horizontally, hero band vertically
    x0 = max(0, (w - OG_W) // 2)
    y0 = top if top is not None else 40
    if y0 + OG_H > h:
        y0 = max(0, h - OG_H)
    out = []
    for y in range(y0, min(y0 + OG_H, h)):
        line = rows[y]
        px = bytearray()
        for x in range(x0, min(x0 + OG_W, w)):
            i = x * nch
            px += line[i:i + 3]                                # drop alpha if present
        out.append(px)
    cw = len(out[0]) // 3
    size = write_png(OUT, cw, len(out), out)
    print(f"og card: {cw}x{len(out)} from {os.path.relpath(src, ROOT)} "
          f"(crop x={x0} y={y0}) -> {os.path.relpath(OUT, ROOT)} ({size // 1024} KB)")


if __name__ == "__main__":
    main()
