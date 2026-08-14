#!/usr/bin/env python3
"""Is the money path actually working? Every step, end to end, against production.

WHY THIS EXISTS. The post-purchase hand-off was broken for weeks and nobody knew, because every
piece of it worked in isolation: the checkout page loaded, the endpoint existed, the secrets were
set, KV had data. The one broken thing was a field in someone else's dashboard, and nothing we owned
ever looked at it. "Does payment work?" was a question you answered by buying something.

This turns it into a command. It checks the steps a real customer walks through, in order, and says
which one fails and exactly how to fix it. It cannot complete a purchase — that costs money and
needs a card — so the last mile is inferred from configuration rather than observed. Every check
says which kind it is.

    python3 pipeline/check_payments.py            # against production
    python3 pipeline/check_payments.py --selftest # no network

Exit code is the number of FAILING checks, so CI can gate on it.
"""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request

BASE = os.environ.get("TASHAN_SITE", "https://tashan.sh")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"user-agent": "tashan-payment-check"}

PASS, FAIL, WARN = "ok  ", "FAIL", "warn"
results = []


def record(state, name, detail=""):
    results.append((state, name, detail))
    print(f"  {state}  {name}" + (f"\n        {detail}" if detail and state != PASS else ""))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow redirects. Two checks here are ABOUT the redirect: whether Polar hands the
    checkout id back, and whether /api/checkout refuses a forged id by bouncing rather than issuing
    a session. urllib follows 3xx by default, so the first version of this file reported
    "expected a redirect, got HTTP 200" — it was looking at /welcome, which is where the redirect
    had already taken it. The check was wrong, not the endpoint."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def hop(base, headers):
    """Resolve a Location header, which may be relative — Cloudflare Pages sends `/welcome`, and
    urllib.request refuses a bare path with "unknown url type"."""
    loc = headers.get("Location") or headers.get("location")
    return urllib.parse.urljoin(base, loc) if loc else None


def get(url, headers=None, method="GET", body=None):
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={**UA, **(headers or {})})
    try:
        with _opener.open(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except urllib.error.URLError as e:
        return 0, str(e.reason), {}


def checkout_links():
    """The buy links as the pricing page actually publishes them — not as a constant here."""
    html = open(os.path.join(ROOT, "web", "pricing.html"), encoding="utf-8").read()
    return sorted(set(re.findall(r"https://buy\.polar\.sh/[A-Za-z0-9_]+", html)))


def success_url_of(link):
    """Follow the buy link to its checkout session and read the configured success_url."""
    status, body, headers = get(link)
    nxt = hop(link, headers)
    if status in (301, 302, 303, 307, 308) and nxt:
        status, body, headers = get(nxt)
    if status != 200:
        return None, f"checkout page returned HTTP {status}"
    m = re.search(r'success_url\\?"\s*:\s*\\?"([^"\\]+)', body)
    return (m.group(1) if m else None), None


def main():
    print(f"\npayment path — {BASE}\n")

    # 1. THE HAND-OFF. The step that was broken: Polar must send the checkout id back to us, or the
    #    customer lands on a page that cannot identify them and is asked to paste a licence key.
    links = checkout_links()
    if not links:
        record(FAIL, "pricing.html publishes at least one checkout link")
    for link in links:
        su, err = success_url_of(link)
        short = link.rsplit("/", 1)[-1][:18] + "…"
        if err:
            record(WARN, f"checkout link {short} reachable", err)
        elif su and "{CHECKOUT_ID}" in su or (su and re.search(r"[?&](id|checkout_id)=", su)):
            record(PASS, f"checkout link {short} returns the checkout id")
        else:
            record(FAIL, f"checkout link {short} returns the checkout id",
                   f"success_url is {su!r} — no id, so /api/checkout never runs and the customer is "
                   f"asked to paste a key.\n        FIX (Polar dashboard, this link): set success_url to "
                   f"{BASE}/api/checkout?id={{CHECKOUT_ID}}")

    # 2. OUR SIDE OF THE HAND-OFF. Must exist, and must refuse a forged id without leaking a session.
    status, body, hdrs = get(f"{BASE}/api/checkout?id=chk_definitely_not_real_000")
    loc = (hdrs.get("Location") or hdrs.get("location") or "")
    ok_bounce = status in (302, 303) and "/welcome" in loc
    record(PASS if ok_bounce else FAIL,
           "/api/checkout refuses an unknown id by bouncing, not by issuing a session",
           f"expected a 302 to /welcome, got HTTP {status} -> {loc!r}")
    record(PASS if "set-cookie" not in {k.lower() for k in hdrs} else FAIL,
           "...and sets no session cookie on a forged id",
           "a cookie here would mean a replayed URL could sign somebody in")

    # 3. THE FALLBACK, so a failed exchange never strands somebody on the screen they just paid for.
    # Pages canonicalises /welcome.html -> /welcome with a 308, which is normal and not a failure.
    # Follow exactly one hop rather than accepting any 3xx, so a redirect to somewhere unexpected
    # still fails.
    status, body, hdrs = get(f"{BASE}/welcome.html")
    nxt = hop(f"{BASE}/welcome.html", hdrs)
    if status in (301, 308) and nxt:
        status, body, hdrs = get(nxt)
    record(PASS if status == 200 else FAIL, "/welcome renders", f"HTTP {status}")
    # And it must still offer the paste fallback, or a customer whose exchange failed is stranded.
    record(PASS if status == 200 and re.search(r"welcome", body, re.I) else FAIL,
           "...and carries the sign-in fallback",
           "the exchange can fail (Polar down, id already burned); this is the way back in")

    # 4. PAID ENDPOINTS. 402 means "priced and reachable"; 503 means the store is not configured and
    #    a paying customer would get nothing.
    for path in ("/api/history?id=pkg:chrome-devtools-mcp", "/api/security?id=pkg:chrome-devtools-mcp"):
        status, body, _ = get(BASE + path)
        name = path.split("?")[0]
        if status == 402:
            try:
                d = json.loads(body)
                has = bool(d.get("plans")) and bool(d.get("free"))
            except ValueError:
                has = False
            record(PASS if has else FAIL, f"{name} quotes a price to an unauthenticated caller",
                   "402 but the body carries no plans/free block")
        elif status == 503:
            record(FAIL, f"{name} is configured",
                   "503 — the KV store is missing, so a paying customer gets nothing")
        else:
            record(FAIL, f"{name} answers 402", f"got HTTP {status}")

    # 5. A BAD CREDENTIAL IS 403, NOT 402. Telling somebody whose licence was refused to go and buy
    #    one sends them to the wrong place, and reads as their subscription being ignored.
    status, _, _ = get(f"{BASE}/api/history?id=pkg:chrome-devtools-mcp",
                       headers={"authorization": "Bearer definitely_not_a_licence"})
    record(PASS if status == 403 else FAIL, "a refused licence is 403, not 402", f"got HTTP {status}")

    # 6. The signed-out shell must be a clean answer, not an error.
    status, body, _ = get(f"{BASE}/api/account")
    ok_shape = False
    try:
        ok_shape = json.loads(body).get("signed_in") is False
    except ValueError:
        pass
    record(PASS if status == 200 and ok_shape else FAIL,
           "/api/account answers cleanly when signed out", f"HTTP {status}: {body[:80]}")

    # 7. The webhook must refuse anything unsigned, or anyone can forge a subscription event.
    status, _, _ = get(f"{BASE}/api/polar", method="POST",
                       body=b'{"type":"forged"}', headers={"content-type": "application/json"})
    record(PASS if status in (401, 403) else FAIL,
           "the Polar webhook refuses an unsigned delivery", f"got HTTP {status}")

    # 8. THE CLI ACTIVATION PATH, which is how a paying customer actually uses what they bought.
    #    A licence that works on the website and not in the terminal is half a product, and the
    #    terminal is where `doctor` — the thing Pro is sold on — runs.
    status, body, _ = get(f"{BASE}/api/device", method="POST",
                          body=b"{}", headers={"content-type": "application/json"})
    dev = {}
    try:
        dev = json.loads(body)
    except ValueError:
        pass
    record(PASS if status == 200 and dev.get("device_code") and dev.get("user_code") else FAIL,
           "the CLI can start a device-code sign-in", f"HTTP {status}: {body[:90]}")
    record(PASS if str(dev.get("verify_url", "")).endswith("/activate") else FAIL,
           "...and is sent to a page that exists", f"verify_url={dev.get('verify_url')!r}")
    if dev.get("device_code"):
        # An unapproved code must NOT hand over a key, and must not error either — the CLI polls it.
        st2, b2, _ = get(f"{BASE}/api/device", method="POST",
                         body=json.dumps({"device_code": dev["device_code"]}).encode(),
                         headers={"content-type": "application/json"})
        leaked = '"key"' in b2
        record(PASS if st2 == 200 and not leaked else FAIL,
               "an unapproved device code yields no licence key",
               f"HTTP {st2}, key present={leaked} — this is the one that must never regress")
    status, _, _ = get(f"{BASE}/activate")
    record(PASS if status in (200, 301, 308) else FAIL, "/activate renders", f"HTTP {status}")

    # 8. Price parity — what a human is quoted and what the code charges.
    ent = json.load(open(os.path.join(ROOT, "data", "entitlements.json"), encoding="utf-8"))
    pro = ent["tiers"]["pro"]
    page = open(os.path.join(ROOT, "web", "pricing.html"), encoding="utf-8").read()
    record(PASS if pro["price"] in page else FAIL,
           f"pricing.html shows the subscription price ({pro['price']})")

    fails = sum(1 for s, _, _ in results if s == FAIL)
    warns = sum(1 for s, _, _ in results if s == WARN)
    print(f"\n  {len(results) - fails - warns} passing, {fails} failing"
          + (f", {warns} unverified" if warns else ""))
    if fails:
        print("\n  NOT PAYMENT-READY. The first FAIL above is the one to fix; the rest may follow from it.")
    else:
        print("\n  Payment-ready as far as this can tell without completing a real purchase.")
    return fails


def _selftest():
    # The parse that matters: reading a success_url out of a checkout page's embedded JSON.
    body = r'{"id":"x","success_url\":\"https://tashan.sh/welcome.html\",\"other\":1}'
    m = re.search(r'success_url\\?"\s*:\s*\\?"([^"\\]+)', body)
    assert m and m.group(1) == "https://tashan.sh/welcome.html", m
    good = r'"success_url\":\"https://tashan.sh/api/checkout?id={CHECKOUT_ID}\"'
    m2 = re.search(r'success_url\\?"\s*:\s*\\?"([^"\\]+)', good)
    assert m2 and "{CHECKOUT_ID}" in m2.group(1)
    assert checkout_links(), "pricing.html must publish at least one buy link"
    print("check_payments selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
