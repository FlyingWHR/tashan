"""Verify that the public agent lookup serves the snapshot this run just deployed."""
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
    for attempt in range(15):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'tashan-publication/1'}), timeout=12) as rsp:
                result = json.load(rsp)
            if (result.get('generated_at') == expected and result.get('id') == record['id']
                    and result.get('tashan_score') == record['tashan_score']):
                print(f"Production serves {expected} for {record['id']}")
                return
            print(f"Waiting for {expected}, public lookup served {result.get('generated_at')}", flush=True)
        except (URLError, ValueError, TimeoutError) as exc:
            print(f'Lookup unavailable: {exc}', flush=True)
        if attempt < 14:
            time.sleep(25)
    raise SystemExit('Public lookup did not confirm the deployed snapshot')


if __name__ == '__main__':
    verify()
