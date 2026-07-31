#!/usr/bin/env python3
"""tashan — local preview that cannot serve you a stale page.

    python3 pipeline/serve.py          # -> http://localhost:4173
    python3 pipeline/serve.py 8080

WHY THIS EXISTS. `python3 -m http.server` sends no Cache-Control at all — only Last-Modified — so
browsers apply a HEURISTIC freshness lifetime and reuse index.html and /data/*.json without ever
revalidating. Production is fine (web/_headers sets `no-cache` on /css, /js and /data), but the preview
lies, and it has lied expensively twice: once as "my CSS fix didn't apply" (the cached HTML still
pointed at the previous ?v=), and once as a hero stat frozen at 757 capabilities long after the export
said 4,852. Both times the pipeline was correct and the browser was the bug.

`no-store` is the fix: not merely "revalidate" but "never write this to disk". One flag, and every
number on screen is the number in web/data.

It also sends production's Content-Security-Policy, for the same reason and at the cost of one grep.
Not sending it lied a third and much larger time: `style-src 'self'` blocks every inline style
ATTRIBUTE, so ~33,000 of them across the site — including every score bar on the board and on all 15
category hubs — were dead on tashan.sh while rendering perfectly here. A preview that is permissive
where production is strict cannot show you the bug; it can only show you the version that works.

ponytail: only the CSP line is read from _headers — the caching rules are deliberately overridden by
no-store above, and TLS/compression are production's job. If it ever needs more, use the real thing.
"""
import functools, http.server, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


def csp():
    """The one production header whose absence changes what RENDERS, read from the real _headers."""
    try:
        src = open(os.path.join(ROOT, "_headers"), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"^\s*Content-Security-Policy:\s*(.+)$", src, re.M)
    return m.group(1).strip() if m else None


CSP = csp()


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        if CSP:                                    # production applies it to /* — so does this
            self.send_header("Content-Security-Policy", CSP)
        super().end_headers()

    def log_message(self, fmt, *a):
        if not self.path.startswith(("/assets/", "/css/", "/js/")):   # keep the log about pages and data
            super().log_message(fmt, *a)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4173
    handler = functools.partial(Handler, directory=ROOT)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"tashan preview  ->  http://localhost:{port}   (no-store: what you see is what is on disk)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    main()
