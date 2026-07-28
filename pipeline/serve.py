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

ponytail: no _headers parsing, no TLS, no compression — production serves those, this only has to stop
lying. It is a preview server; if it ever needs more, use the real thing.
"""
import functools, http.server, os, sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
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
