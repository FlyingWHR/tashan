#!/usr/bin/env python3
"""What actually arrived on Base — the only settlement number we do not have to trust ourselves for.

    python3 pipeline/onchain.py              # balance + every USDC transfer in
    python3 pipeline/onchain.py --selftest   # no network

WHY THIS EXISTS. Everything else that says "settled" is our own software agreeing with itself: the
Worker asks a facilitator, the facilitator answers, we write a row. Until 21 Aug the settle path
accepted `{}` as success, so we would have recorded settlements, served the paid content, and moved
no money — and every downstream number would have agreed with us. The chain does not care what we
recorded. `payTo` either received USDC or it did not.

The Worker now refuses a settlement that carries no transaction hash and puts that hash in the
event, so a recorded settle can be pointed at a block. This script is the other half: it reads the
chain directly and says what is there, so the two can be compared instead of assumed equal.

WHY BALANCE IS THE HEADLINE. This address only ever receives — it has never sent a transaction, and
nothing in this repo can make it send one. So while that holds, balance IS lifetime revenue, and it
needs one RPC call and no indexer. The transfer log below is the detail; the balance is the fact.
If a withdrawal ever happens, that stops being true and this docstring is the thing to fix first.

Stdlib only, public RPC, no key. Never fatal: a report about money must not be able to fail a
pipeline whose job is measurement.
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RPCS = ("https://mainnet.base.org", "https://base.llamarpc.com", "https://base-rpc.publicnode.com")
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"          # Base mainnet USDC, 6 decimals
DECIMALS = 10 ** 6
# keccak256("Transfer(address,address,uint256)") — the ERC-20 log topic every transfer carries.
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
OUT = os.path.join(ROOT, "data", "onchain.json")


def pay_to():
    """The receiving address, read from the same place the Worker quotes it from where possible.

    Falls back to the published constant: this address appears in every live 402, so it is not a
    secret and hard-coding it here cannot leak anything. It IS worth keeping in step — a report
    about an address we no longer use would be reassuring and wrong.
    """
    return (os.environ.get("X402_PAY_TO")
            or "0x813e91688330cB03BD9F4e710A28C4B6207e9fC1")


def rpc(method, params, urls=RPCS, post=None):
    """First RPC that answers wins. Public endpoints rate-limit and go down; one being unreachable
    is not a finding about our revenue."""
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    last = None
    for u in urls:
        try:
            if post:
                return post(u, body)
            req = urllib.request.Request(u, data=json.dumps(body).encode(),
                                         headers={"content-type": "application/json",
                                                  "user-agent": "tashan-selfcheck/onchain"})
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.load(r)
            if "error" in d:
                last = d["error"]
                continue
            return d.get("result")
        except Exception as e:                                    # noqa: BLE001
            last = e
    raise RuntimeError(f"no RPC answered: {last}")


def balance(addr, **kw):
    """USDC held, in whole units. balanceOf(address) is selector 0x70a08231."""
    data = "0x70a08231" + "0" * 24 + addr[2:].lower()
    r = rpc("eth_call", [{"to": USDC, "data": data}, "latest"], **kw)
    return int(r, 16) / DECIMALS if r and r != "0x" else 0.0


def transfers_in(addr, from_block=0, **kw):
    """[(tx_hash, from_addr, amount)] for USDC transfers INTO addr.

    topic0 pins the event, topic2 pins the recipient — indexed args are topics, so this filters at
    the node rather than pulling every USDC transfer on Base and sifting locally.
    """
    topic_to = "0x" + "0" * 24 + addr[2:].lower()
    logs = rpc("eth_getLogs", [{"address": USDC, "fromBlock": hex(from_block), "toBlock": "latest",
                                "topics": [TRANSFER, None, topic_to]}], **kw) or []
    out = []
    for lg in logs:
        topics = lg.get("topics") or []
        frm = "0x" + topics[1][-40:] if len(topics) > 1 else "?"
        raw = lg.get("data") or "0x0"
        try:
            amt = int(raw, 16) / DECIMALS
        except ValueError:
            amt = 0.0
        out.append((lg.get("transactionHash"), frm, amt))
    return out


def report(addr, bal, txs):
    L = [f"ON-CHAIN — {addr}", "", f"  USDC received (balance)   {bal:,.4f}"]
    if txs:
        L.append(f"  payments in               {len(txs)}")
        L.append("")
        for h, frm, amt in txs[-10:]:
            L.append(f"    {amt:>10,.4f} USDC  from {frm[:12]}…  {str(h)[:18]}…")
    else:
        L += ["  payments in               0", "",
              "  No settlement has ever reached this address. Everything upstream that says",
              "  'settled' is our software agreeing with itself until this number moves.",
              "",
              "  The first one cannot arrive on its own: the x402 Bazaar is the only discovery",
              "  index agents use, and it indexes a seller only AFTER a settle clears. Nothing",
              "  in this repo can break that circle — it needs a funded wallet once."]
    return "\n".join(L)


def _selftest():
    calls = {}

    def fake(_u, body):
        calls[body["method"]] = body["params"]
        if body["method"] == "eth_call":
            return int(2_500_000).to_bytes(32, "big").hex()          # 2.5 USDC
        return [{"transactionHash": "0xaaa", "data": hex(1_000_000),
                 "topics": [TRANSFER, "0x" + "0" * 24 + "b" * 40, "0x" + "0" * 24 + "c" * 40]}]

    addr = "0x813e91688330cB03BD9F4e710A28C4B6207e9fC1"
    b = balance(addr, post=lambda u, body: "0x" + fake(u, body))
    assert abs(b - 2.5) < 1e-9, b
    # The recipient must be pinned by TOPIC, not filtered after the fact: topics[2] is `to`.
    t = transfers_in(addr, post=fake)
    got = calls["eth_getLogs"][0]["topics"]
    assert got[0] == TRANSFER and got[1] is None, got
    assert got[2].endswith(addr[2:].lower()), got
    assert t == [("0xaaa", "0x" + "b" * 40, 1.0)], t

    # An empty chain must read as "nothing has happened", never as a failure to look.
    r = report(addr, 0.0, [])
    assert "payments in               0" in r and "has ever reached this address" in r, r
    assert "agreeing with itself" in r, "the point of the file must survive in its output"
    r2 = report(addr, 2.5, t)
    assert "2.5000" in r2 and "0xaaa" in r2, r2
    print("onchain selftest ok")
    return 0


def main():
    addr = pay_to()
    try:
        bal = balance(addr)
        try:
            txs = transfers_in(addr)
        except Exception:
            txs = []                                   # getLogs is the flaky one; balance is enough
    except Exception as e:                             # noqa: BLE001
        print(f"onchain: no RPC reachable ({e}) — reporting nothing rather than zero, which would "
              f"be a claim we did not verify.")
        return 0
    print(report(addr, bal, txs))
    json.dump({"address": addr, "usdc_received": bal, "payments": len(txs)},
              open(OUT, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
