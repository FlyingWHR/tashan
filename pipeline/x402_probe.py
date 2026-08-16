#!/usr/bin/env python3
"""Would this facilitator actually take a payment addressed to us? Ask it, before switching to it.

    python3 pipeline/x402_probe.py https://facilitator.openx402.ai
    python3 pipeline/x402_probe.py https://facilitator.xpay.sh --network eip155:8453
    python3 pipeline/x402_probe.py --selftest

WHY THIS EXISTS. On the day mainnet went live, check_payments reported 25 passing and no caller
could have paid us. Every secret was right, the quote was spec-shaped, the asset and EIP-712 domain
matched the facilitator's own /supported, and both addresses passed their checksums — and the
facilitator answered every payment with:

    {"isValid":false,"invalidReason":"address_not_registered", …}

A refusal about the SELLER, invisible to everything we had, discoverable only by the first paying
stranger, who would simply have left. check_payments now catches that against whatever is deployed.
This is the other half: evaluating a CANDIDATE facilitator without deploying it first, so choosing
one is not a guess followed by a redeploy.

NO MONEY MOVES. The probe signs with 0x00, which cannot settle. A facilitator that says that payment
is VALID is failing open, and that is reported as the worst possible result rather than a pass.

Three things are worth knowing about a facilitator, and it answers all three:
  1. does it settle the network we sell on
  2. does it agree with us about the asset and the EIP-712 domain (name/version)
  3. would it accept a payment addressed to OUR wallet, or does it whitelist
"""
import json, os, sys, urllib.error, urllib.request

# Refusals that are about US, not about the payer. A payment-side refusal (bad signature, no funds)
# means the facilitator works and would take a real payment; a seller-side one means it never will.
SELLER_SIDE = ("not_registered", "unregistered", "unsupported", "unknown_network", "unknown_asset",
               "invalid_recipient", "not_allowed", "forbidden", "unauthorized", "no_such")

USDC = {
    "eip155:8453":  ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "Base mainnet"),
    "eip155:84532": ("0x036CbD53842c5426634e7929541eC2318f3dCF7e", "Base Sepolia"),
}


def post(url, body, timeout=25):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json",
                                          "user-agent": "tashan-x402-probe"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace") or "{}")
        except ValueError:
            return e.code, {}
    except Exception as e:
        return 0, {"_error": str(e)}


def get(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"user-agent": "tashan-x402-probe"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace") or "{}")
    except Exception:
        return {}


def requirements(pay_to, network, amount="50000"):
    asset, _ = USDC.get(network, (None, None))
    return {"scheme": "exact", "network": network, "amount": amount, "asset": asset,
            "payTo": pay_to, "maxTimeoutSeconds": 60,
            "resource": "https://tashan.sh/v0.1/audit",
            "extra": {"name": "USD Coin", "version": "2"}}


def bogus_payment(req):
    """A structurally complete payment that cannot possibly settle: the signature is 0x00."""
    return {"x402Version": 2, "scheme": req["scheme"], "network": req["network"],
            "payload": {"signature": "0x00", "authorization": {
                "from": "0x0000000000000000000000000000000000000001",
                "to": req["payTo"], "value": req["amount"],
                "validAfter": "0", "validBefore": "99999999999", "nonce": "0x00"}}}


def classify(reply):
    """-> (verdict, reason, message).

    verdict in {accepts, seller-blocked, incompatible, fails-open, unclear}.

    A KNOWN payment-side reason is required to say "accepts" — anything unrecognised is `unclear`,
    never a pass. The first version did the opposite: any reason that was not seller-side counted as
    working, which labelled two facilitators USABLE when what they had actually said was that they
    could not PARSE our request ("Cannot read properties of undefined (reading 'scheme')",
    "expected object, received undefined"). Recommending one of those would have moved the money
    path to a facilitator that never understood a single call. Same discipline as charge(): an
    explicit yes, or nothing.
    """
    if not isinstance(reply, dict):
        return "unclear", "", ""
    if reply.get("isValid") is True or reply.get("valid") is True:
        return "fails-open", "", "it approved a payment signed 0x00"
    reason = str(reply.get("invalidReason") or reply.get("errorReason") or "").lower()
    msg = str(reply.get("invalidMessage") or reply.get("errorMessage") or reply.get("error") or "")
    blob = (reason + " " + msg).lower()
    if any(m in reason for m in SELLER_SIDE) or "not registered" in blob:
        return "seller-blocked", reason, msg
    # It could not read what we sent. Not a payment judgement at all — the integration is broken.
    if any(m in blob for m in ("invalid_payload", "unexpected_error", "malformed", "bad_request",
                               "cannot read properties", "expected object", "unmarshal",
                               "parse", "missing required", "schema")):
        return "incompatible", reason, msg
    # The facilitator read the request and judged the PAYMENT. That is a working facilitator.
    if any(m in reason for m in ("signature", "funds", "balance", "amount", "expired", "nonce",
                                 "authorization", "insufficient", "invalid_exact", "deadline",
                                 "allowance", "recover")):
        return "accepts", reason, msg
    return "unclear", reason, msg


def probe(base, pay_to, network):
    base = base.rstrip("/")
    out = {"facilitator": base, "network": network}
    sup = get(base + "/supported")
    kinds = sup.get("kinds") or []
    mine = [k for k in kinds if k.get("network") == network and k.get("scheme") == "exact"]
    out["settles_this_network"] = bool(mine)
    out["networks"] = sorted({k.get("network") for k in kinds if k.get("network")})[:8]
    if mine:
        ex = mine[0].get("extra") or {}
        want_asset = USDC.get(network, (None,))[0]
        out["asset_agrees"] = (not ex.get("asset")) or ex["asset"].lower() == (want_asset or "").lower()
        out["domain"] = {"name": ex.get("name"), "version": ex.get("version")}
    req = requirements(pay_to, network)
    st, reply = post(base + "/verify", {"x402Version": 2, "paymentPayload": bogus_payment(req),
                                        "paymentRequirements": req})
    out["http"], out["reply"] = st, reply
    out["verdict"], out["reason"], out["message"] = classify(reply)
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    network = "eip155:8453"
    if "--network" in argv:
        network = argv[argv.index("--network") + 1]
    pay_to = os.environ.get("X402_PAY_TO", "")
    if "--pay-to" in argv:
        pay_to = argv[argv.index("--pay-to") + 1]
    if not pay_to:
        # Read it off our own live 402 rather than asking for it twice. THE ANSWER IS THE ERROR:
        # /v0.1/audit replies 402, and urlopen raises HTTPError on any 4xx — so the first version of
        # this caught the exception and reported "could not determine payTo" while holding the
        # response that contained it.
        try:
            req = urllib.request.Request(
                "https://tashan.sh/v0.1/audit", method="POST",
                data=b'{"servers":["chrome-devtools-mcp"],"history":true}',
                # AND A USER-AGENT. Cloudflare refuses the literal string "Python-urllib" wherever it
                # sits in front — docs/DO-THIS-NEXT.md §1 documents two days lost to exactly this,
                # and this call answered 403 while every other request in this file worked, because
                # they set one and it did not.
                headers={"content-type": "application/json", "user-agent": "tashan-x402-probe"})
            try:
                body = urllib.request.urlopen(req, timeout=25).read()
            except urllib.error.HTTPError as e:
                body = e.read()
            pay_to = ((json.loads(body).get("accepts") or [{}])[0]).get("payTo", "")
        except Exception:
            pass
    if not args:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    if not pay_to:
        print("  could not determine payTo — pass --pay-to 0x… or set X402_PAY_TO")
        return 2

    print(f"\n  payTo {pay_to}   network {network} ({USDC.get(network, ('', '?'))[1]})\n")
    worst = 0
    for base in args:
        r = probe(base, pay_to, network)
        v = r["verdict"]
        mark = {"accepts": "USABLE      ", "seller-blocked": "BLOCKED     ",
                "incompatible": "INCOMPATIBLE", "fails-open": "DANGEROUS   ",
                "unclear": "UNCLEAR     "}[v]
        print(f"  {mark} {r['facilitator']}")
        print(f"      settles {network}: {r['settles_this_network']}"
              + (f"   domain {r.get('domain')}" if r.get("domain") else ""))
        if not r["settles_this_network"] and r["networks"]:
            print(f"      it lists: {', '.join(r['networks'])}")
        if v == "accepts":
            print(f"      refuses a bogus payment for a PAYMENT-side reason ({r['reason']}) — "
                  f"a real one would be judged on its merits")
        elif v == "seller-blocked":
            print(f"      refuses payments TO US: {r['reason'] or 'see message'}")
            print(f"      {r['message'][:150]}")
            worst = max(worst, 1)
        elif v == "incompatible":
            print(f"      it could not PARSE our request — this is not a payment judgement: "
                  f"{r['reason'] or 'see message'}")
            print(f"      {r['message'][:150]}")
            worst = max(worst, 1)
        elif v == "fails-open":
            print(f"      IT APPROVED A PAYMENT SIGNED 0x00. Do not use it: it validates nothing.")
            worst = max(worst, 2)
        else:
            print(f"      HTTP {r['http']}, unrecognised reply: {json.dumps(r['reply'])[:140]}")
            worst = max(worst, 1)
        print()
    return worst


def _selftest():
    r = requirements("0xabc", "eip155:8453")
    assert r["asset"] == USDC["eip155:8453"][0] and r["extra"]["name"] == "USD Coin"
    assert bogus_payment(r)["payload"]["signature"] == "0x00", "the probe must not be able to settle"
    # A facilitator that approves an unsigned payment is the worst outcome, not a pass.
    assert classify({"isValid": True})[0] == "fails-open"
    assert classify({"valid": True})[0] == "fails-open"
    # Seller-side refusals, the case this file exists for.
    assert classify({"isValid": False, "invalidReason": "address_not_registered"})[0] == "seller-blocked"
    assert classify({"isValid": False, "invalidReason": "x",
                     "invalidMessage": "Address 0x1 is not registered. Register at …"})[0] == "seller-blocked"
    # Payment-side refusals mean the facilitator works.
    assert classify({"isValid": False, "invalidReason": "invalid_signature"})[0] == "accepts"
    assert classify({"isValid": False, "invalidReason": "insufficient_funds"})[0] == "accepts"
    assert classify({})[0] == "unclear" and classify(None)[0] == "unclear"
    # A PARSE FAILURE IS NOT A PAYMENT JUDGEMENT. Both live alternatives answered this way, and the
    # first version of classify() called them USABLE — which would have moved the money path to a
    # facilitator that never understood a single request.
    assert classify({"isValid": False, "invalidReason": "invalid_payload",
                     "invalidMessage": "accepted: Invalid input: expected object, received undefined"
                     })[0] == "incompatible"
    assert classify({"isValid": False, "invalidReason": "unexpected_error",
                     "invalidMessage": "Cannot read properties of undefined (reading 'scheme')"
                     })[0] == "incompatible"
    # An unrecognised reason is never a pass.
    assert classify({"isValid": False, "invalidReason": "something_new"})[0] == "unclear"
    print("x402_probe selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main(sys.argv[1:]))
