"""Verify that the public agent lookup serves the snapshot this run just deployed."""
import hashlib
import json
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def verify():
    root = Path(__file__).resolve().parents[1]
    with (root / 'web/data/lookup.json').open() as src:
        snapshot = json.load(src)
    record = next(r for r in snapshot['records'] if r.get('npm_pkg') and r.get('tashan_score') is not None)
    expected = snapshot['generated_at']
    url = 'https://tashan.sh/v0.1/lookup?' + urlencode({'name': record['id'], 'snapshot': expected})
    # A service-only release can keep the same data timestamp. Check a shipped
    # client asset and live Functions as well as the dated lookup.
    script = (root / 'web/js/token-preview.js').read_bytes()
    digest = hashlib.sha256(script).hexdigest()
    def read(path):
        req = Request('https://tashan.sh' + path, headers={'User-Agent': 'tashan-publication/1'})
        with urlopen(req, timeout=12) as rsp:
            return rsp.headers.get_content_type(), rsp.read()

    for attempt in range(15):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'tashan-publication/1'}), timeout=12) as rsp:
                result = json.load(rsp)
            if (result.get('generated_at') == expected and result.get('id') == record['id']
                    and result.get('tashan_score') == record['tashan_score']):
                if read('/js/token-preview.js?' + urlencode({'release': digest}))[1] != script:
                    raise ValueError("production still serves a different token preview")
                mime, dossier = read('/capability/' + record['slug'] + '.md')
                if mime != 'text/markdown' or not dossier.startswith(b'# '):
                    raise ValueError("Markdown dossier unavailable")
                if json.loads(read('/api/account')[1]).get('signed_in') is not False:
                    raise ValueError("signed-out account endpoint unavailable")
                print(f"Production serves the token preview, Markdown, signed-out account and {expected} for {record['id']}")
                return
            print(f"Waiting for {expected}, public lookup served {result.get('generated_at')}", flush=True)
        except (URLError, ValueError, TimeoutError) as exc:
            print(f'Publication check: {exc}', flush=True)
        if attempt < 14:
            time.sleep(25)
    raise SystemExit('Public lookup did not confirm the deployed snapshot')


if __name__ == '__main__':
    verify()
