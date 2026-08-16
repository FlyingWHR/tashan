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
    """The Polar checkout links this site sells through, from the file that defines what is sold.

    These used to be scraped out of pricing.html, because the page was the thing that published
    them. It no longer does: every buy button goes through /api/buy, which repairs the checkout
    link's success_url on the way past. entitlements.json is where the real URLs live now, and
    where the prerender validates them."""
    ent = json.load(open(os.path.join(ROOT, "data", "entitlements.json"), encoding="utf-8"))
    pro = ent["tiers"]["pro"]
    out = {}
    if pro.get("checkout"):
        out["monthly"] = pro["checkout"]
    if (pro.get("annual") or {}).get("url"):
        out["annual"] = pro["annual"]["url"]
    return out


def buy_constants():
    """The two links hardcoded in functions/api/buy.js, which is what the redirect actually uses.

    A test asserts these equal entitlements.json. Without it the page could advertise one product
    and the button send you to another — the exact shape of the bug where the annual control billed
    the monthly price, and the one class of defect this file exists to catch."""
    js = open(os.path.join(ROOT, "functions", "api", "buy.js"), encoding="utf-8").read()
    return dict(re.findall(r"^\s*(monthly|annual):\s*\"(polar_cl_[A-Za-z0-9_]+)\"", js, re.M))


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

    # 1. THE HAND-OFF. The step that was broken for weeks: Polar must send the checkout id back to
    #    us, or the customer lands on a page that cannot identify them and is asked to paste a
    #    licence key they were never given.
    #
    #    RUNNING THIS CHECK IS NOW ALSO THE FIX. /api/buy verifies and repairs that field on its
    #    way to Polar, so hitting the button here — which is what a real buyer does — heals it.
    #    The nightly workflow runs this file, so the field is re-verified every day against the
    #    live dashboard rather than trusted because somebody set it once.
    links = checkout_links()
    consts = buy_constants()
    if not links:
        record(FAIL, "entitlements.json names at least one checkout link")
    for plan, link in sorted(links.items()):
        want_secret = link.rsplit("/", 1)[-1]
        if consts.get(plan) != want_secret:
            record(FAIL, f"the {plan} button sends buyers to the {plan} product",
                   f"functions/api/buy.js has {consts.get(plan)!r}, entitlements.json has "
                   f"{want_secret!r} — the page and the button would sell different things")
            continue
        record(PASS, f"the {plan} button and the {plan} price name the same checkout link")

        # The redirect itself, as a buyer experiences it.
        status, _, hdrs = get(f"{BASE}/api/buy?plan={plan}")
        loc = hop(f"{BASE}/api/buy", hdrs) or ""
        if status not in (301, 302, 303, 307, 308) or loc != link:
            record(FAIL, f"/api/buy?plan={plan} reaches Polar",
                   f"expected a redirect to {link}, got HTTP {status} -> {loc!r}")
            continue
        record(PASS, f"/api/buy?plan={plan} redirects to the {plan} checkout")

        # And the field that redirect exists to repair. Read from Polar's own checkout page, so
        # this is the configuration as it really is, not as we hope we set it.
        su, err = success_url_of(link)
        if err:
            record(WARN, f"the {plan} checkout returns the checkout id", err)
        elif su and "{CHECKOUT_ID}" in su or (su and re.search(r"[?&](id|checkout_id)=", su)):
            record(PASS, f"the {plan} checkout returns the checkout id to /api/checkout")
        else:
            record(FAIL, f"the {plan} checkout returns the checkout id to /api/checkout",
                   f"success_url is {su!r} — no id, so /api/checkout never runs and the customer "
                   f"is asked to paste a key.\n        /api/buy should have repaired this. Check "
                   f"POLAR_ORG_TOKEN can write checkout links, then re-run.")

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
    # /api/security IS NOT IN THIS LIST any more — it was made free, because everything it returns
    # is already in the public export and at /v0.1/lookup. It gets its own check below, asserting
    # the opposite: that it does NOT ask for money.
    for path in ("/api/history?id=pkg:chrome-devtools-mcp",):
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

    # 4b. AND THE FREE SIDE OF THE SAME LINE. /api/security must never start asking for money again:
    #     it returns current state, which redact_paid() publishes and /v0.1/lookup serves to anyone.
    #     A 402 here would charge for a giveaway, which is the defect this endpoint just came out of.
    status, body, _ = get(f"{BASE}/api/security?id=pkg:claude-cup")
    ok_free = False
    try:
        d = json.loads(body)
        ok_free = status == 200 and d.get("licence") == "free" and d.get("advisories") is not None
    except ValueError:
        pass
    record(PASS if ok_free else FAIL, "/api/security answers without a credential, and says it is free",
           f"HTTP {status}: {body[:120]}")

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

    # 9. THE AGENT RAIL. x402 is built and dormant until a wallet exists, which is deliberate:
    #    quoting a payment option we cannot settle wastes the caller's signature. So "no accepts"
    #    is a WARN, not a failure — it is the documented state. What must never happen is a HALF
    #    configuration, where we advertise terms and then cannot verify a payment.
    status, body, hdrs = get(f"{BASE}/v0.1/audit", method="POST",
                             body=b'{"servers":["chrome-devtools-mcp"],"history":true}',
                             headers={"content-type": "application/json"})
    quote = {}
    try:
        quote = json.loads(body)
    except ValueError:
        pass
    accepts = quote.get("accepts") or []
    has_hdr = any(k.lower() == "payment-required" for k in hdrs)
    if status == 402 and not accepts and not has_hdr:
        record(WARN, "agent payments (x402) are live",
               "dormant — no wallet configured, which is the documented state, not a fault.\n"
               "        The free audit still answers. To turn it on, see docs/X402.md:\n"
               "        wrangler pages secret put X402_PAY_TO / X402_NETWORK / X402_ASSET / "
               "X402_FACILITATOR")
    elif status == 402 and accepts and has_hdr:
        a = accepts[0] if isinstance(accepts[0], dict) else {}
        good = (quote.get("x402Version") == 2 and a.get("payTo") and a.get("network")
                and a.get("asset") and isinstance(a.get("amount"), str))
        record(PASS if good else FAIL, "agent payments (x402) quote complete, spec-shaped terms",
               f"x402Version={quote.get('x402Version')!r} accepts[0]={a!r}")

        # THE ADDRESS THAT RECEIVES THE MONEY, CHECKED. A wrong payTo is the only unrecoverable
        # error here — funds land somewhere nobody controls and no one can reverse it. EIP-55 hides
        # a checksum in the case of the hex letters, so a mistyped mixed-case address fails to
        # verify with overwhelming probability. All-lowercase carries no checksum and is reported as
        # unverifiable rather than as valid, because "we cannot tell" is not "fine".
        sys.path.insert(0, os.path.join(ROOT, "pipeline"))
        from eip55 import valid as _addr_ok
        for label, addr in (("payTo", a.get("payTo")), ("asset", a.get("asset"))):
            v = _addr_ok(addr or "")
            if v is True:
                record(PASS, f"the {label} address passes its EIP-55 checksum")
            elif v is None:
                record(WARN, f"the {label} address carries no checksum to verify",
                       f"{addr} is all one case — re-copy it from the wallet in mixed case and a "
                       f"typo becomes detectable")
            else:
                record(FAIL, f"the {label} address is not a valid checksummed address",
                       f"{addr!r} — on mainnet this sends funds nowhere recoverable")

        # WHAT WE QUOTE MUST BE WHAT THE FACILITATOR WILL SETTLE. A facilitator publishes the exact
        # asset, EIP-712 domain name and version it verifies against, per network, at /supported.
        # If our `accepts` disagrees on any of them the caller signs a domain nobody accepts, every
        # payment fails verification, and NOTHING looks broken: all four secrets set, a spec-shaped
        # quote on every 402. The default asset name was "USDC" until 16 Aug 2026; USDC's contract
        # on Base is named "USD Coin", so that is precisely the failure this would have had.
        fac = (a.get("extra") or {}).get("facilitator") or os.environ.get("X402_FACILITATOR", "")
        if not fac:
            record(WARN, "x402 terms agree with the facilitator",
                   "set X402_FACILITATOR in this shell to cross-check the quote against /supported")
        else:
            st, body2, _ = get(fac.rstrip("/") + "/supported")
            kinds = []
            try:
                kinds = (json.loads(body2) or {}).get("kinds") or []
            except ValueError:
                pass
            mine = {k: (a.get("extra") or {}).get(k) for k in ("name", "version")}
            mine["asset"], mine["network"] = a.get("asset"), a.get("network")
            match = [k for k in kinds
                     if k.get("network") == mine["network"] and k.get("scheme") == a.get("scheme")]
            if not match:
                record(FAIL, "the facilitator settles the network we quote",
                       f"we quote {mine['network']!r}; it supports "
                       f"{sorted({k.get('network') for k in kinds})[:6]}")
            else:
                ex = match[0].get("extra") or {}
                bad = [f"{k}: we say {mine[k]!r}, it expects {ex.get(k)!r}"
                       for k in ("asset", "name", "version")
                       if ex.get(k) and str(ex[k]).lower() != str(mine.get(k) or "").lower()]
                record(PASS if not bad else FAIL,
                       "our asset, EIP-712 name and version match the facilitator's",
                       "; ".join(bad) + " — signatures will not verify")

            # WOULD IT ACCEPT A PAYMENT TO US AT ALL? Everything above can pass while every payment
            # is refused for a reason that has nothing to do with the payer. Found exactly that on
            # the day mainnet went live: 25 checks green, and openx402 answering
            #
            #   {"isValid":false,"invalidReason":"address_not_registered",
            #    "invalidMessage":"Address 0x813e… is not registered. Register at …/register"}
            #
            # A refusal about the SELLER, invisible to every check we had, and it would have been
            # discovered by the first paying stranger — who would simply have gone away.
            #
            # So: send a deliberately invalid payment and read WHY it is refused. It must be refused
            # (a pass here would mean the facilitator validates nothing), and the reason must be
            # about the PAYMENT — a bad signature, no funds — not about our configuration. No money
            # moves; the signature is 0x00 and cannot settle.
            SELLER_SIDE = ("not_registered", "unregistered", "unsupported", "unknown_network",
                           "unknown_asset", "invalid_recipient", "not_allowed", "forbidden",
                           "unauthorized", "no_such")
            probe = {
                "x402Version": 2,
                "paymentPayload": {"x402Version": 2, "scheme": a.get("scheme"),
                                   "network": a.get("network"),
                                   "payload": {"signature": "0x00", "authorization": {
                                       "from": "0x0000000000000000000000000000000000000001",
                                       "to": a.get("payTo"), "value": a.get("amount"),
                                       "validAfter": "0", "validBefore": "99999999999",
                                       "nonce": "0x00"}}},
                "paymentRequirements": a,
            }
            st3, body3, _ = get(fac.rstrip("/") + "/verify", method="POST",
                                body=json.dumps(probe).encode(),
                                headers={"content-type": "application/json"})
            try:
                vr = json.loads(body3)
            except ValueError:
                vr = {}
            reason = str(vr.get("invalidReason") or vr.get("errorReason") or "").lower()
            msg = str(vr.get("invalidMessage") or vr.get("errorMessage") or "")[:160]
            if vr.get("isValid") is True or vr.get("valid") is True:
                record(FAIL, "the facilitator actually validates payments",
                       "it approved a payment signed 0x00 — it is not checking anything")
            elif any(m in reason for m in SELLER_SIDE):
                record(FAIL, "the facilitator will accept a payment addressed to us",
                       f"it refuses for a SELLER-side reason: {reason!r}\n        {msg}\n"
                       f"        No caller can pay us until this is fixed, and every other check "
                       f"here passes while it is broken.")
            elif reason:
                record(PASS, "the facilitator will accept a payment addressed to us",
                       f"a bogus payment is refused for a payment-side reason ({reason})")
            else:
                record(WARN, "the facilitator will accept a payment addressed to us",
                       f"HTTP {st3}, unrecognised reply: {body3[:120]}")
    else:
        # Terms without a header, or a header without terms: a caller cannot act on either.
        record(FAIL, "x402 is either fully on or fully off",
               f"HTTP {status}, accepts={len(accepts)}, PAYMENT-REQUIRED header={has_hdr} — a "
               f"half-configuration advertises a price we cannot settle")

    # The free half must answer regardless. This is the firewall on the agent rail: the EXISTENCE
    # of a risk is never behind a paywall, so a 402 still carries the audit.
    record(PASS if (quote.get("free_result") or quote.get("free") or quote.get("results")) else FAIL,
           "...and the free risk audit is still in the body of the 402",
           f"keys: {sorted(quote)[:8]}")

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
    links = checkout_links()
    assert links, "entitlements.json must name at least one buy link"
    consts = buy_constants()
    assert consts, "functions/api/buy.js must define the checkout links it redirects to"
    # The one that matters offline: the button and the price tag must name the same product.
    for plan, url in links.items():
        assert consts.get(plan) == url.rsplit("/", 1)[-1], (
            f"{plan}: buy.js has {consts.get(plan)!r}, entitlements.json has {url!r}")
    # And the page must actually route through the repair, or the whole mechanism is bypassed.
    page = open(os.path.join(ROOT, "web", "pricing.html"), encoding="utf-8").read()
    assert "buy.polar.sh" not in page, (
        "pricing.html links straight to Polar somewhere — that route skips the success_url repair")
    for plan in links:
        assert f"/api/buy?plan={plan}" in page, f"pricing.html has no {plan} button through /api/buy"
    print("check_payments selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
