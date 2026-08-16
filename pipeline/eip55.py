#!/usr/bin/env python3
"""EIP-55 address checksums, so a mistyped wallet is caught before money moves.

WHY THIS EXISTS AND WHY IT IS HAND-ROLLED. `X402_PAY_TO` is the one value in this project where a
single wrong character sends real funds to an address nobody controls, and it is impossible to undo.
Every other config error is recoverable; this one is not.

EIP-55 encodes a checksum in the CASE of the hex letters, so a typo in a mixed-case address fails to
verify with overwhelming probability. Checking it needs keccak-256 — which is NOT hashlib's
sha3_256; they differ in the padding byte (0x01 vs 0x06) and produce entirely different digests. The
project has no pip dependencies by rule, so keccak is implemented here and pinned to the canonical
empty-string vector plus all four worked examples published in EIP-55 itself. If the implementation
were subtly wrong those assertions fail; a wrong implementation that still passes them is not a
thing that happens by accident.

    python3 pipeline/eip55.py --selftest
    python3 pipeline/eip55.py 0x813e...9fC1        # verdict for one address
"""
RC = [0x0000000000000001,0x0000000000008082,0x800000000000808A,0x8000000080008000,
      0x000000000000808B,0x0000000080000001,0x8000000080008081,0x8000000000008009,
      0x000000000000008A,0x0000000000000088,0x0000000080008009,0x000000008000000A,
      0x000000008000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,
      0x8000000000008002,0x8000000000000080,0x000000000000800A,0x800000008000000A,
      0x8000000080008081,0x8000000000008080,0x0000000080000001,0x8000000080008008]
ROT = [[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],[28,55,25,21,56],[27,20,39,8,14]]
M = (1 << 64) - 1
def rol(x, n): return ((x << n) | (x >> (64 - n))) & M
def keccak_f(a):
    for rnd in range(24):
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5): a[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = rol(a[x][y], ROT[x][y])
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y] & M) & b[(x + 2) % 5][y])
        a[0][0] ^= RC[rnd]
    return a
def keccak256(data: bytes) -> bytes:
    rate = 136
    p = bytearray(data) + b"\x01"
    while len(p) % rate != 0: p.append(0)
    p[-1] ^= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(p), rate):
        blk = p[off:off + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(blk[i*8:i*8+8], "little")
            a[i % 5][i // 5] ^= lane
        a = keccak_f(a)
    out = b""
    for i in range(4): out += a[i % 5][i // 5].to_bytes(8, "little")
    return out[:32]
def to_checksum(addr: str) -> str:
    a = addr.lower().replace("0x", "")
    h = keccak256(a.encode()).hex()
    return "0x" + "".join(c.upper() if c.isalpha() and int(h[i], 16) >= 8 else c
                          for i, c in enumerate(a))
def valid(addr: str) -> bool:
    a = addr.strip()
    if not (a.startswith("0x") and len(a) == 42): return False
    try: int(a[2:], 16)
    except ValueError: return False
    if a[2:].islower() or a[2:].isupper(): return None   # no checksum to verify
    return to_checksum(a) == a


def _selftest():
    assert keccak256(b"").hex() == \
        "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470", "not keccak-256"
    assert keccak256(b"abc").hex() == \
        "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    for a in ("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
              "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
              "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
              "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb"):
        assert to_checksum(a) == a, a
        assert valid(a) is True, a
    # One flipped character must be rejected — the whole point.
    assert valid("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAee") is False
    # All-lowercase carries no checksum: unknowable, never "valid".
    assert valid("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed") is None
    assert valid("0xnope") is False and valid("") is False
    print("eip55 selftest ok")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    for a in sys.argv[1:]:
        v = valid(a)
        print(f"  {a}  {'VALID' if v is True else ('NO CHECKSUM (all one case)' if v is None else 'CHECKSUM FAILS')}")
        if v is False and len(a) == 42:
            print(f"    expected: {to_checksum(a)}")
