#!/usr/bin/env python3
"""tashan — the subregistry endpoint. Stop being a website; become something an agent calls.

An agent never visits a site. It calls whatever it already speaks. The MCP registry spec anticipates
exactly this: an aggregator that implements the registry's own OpenAPI shape and injects extra metadata
under `_meta`, and the spec's worked example of such metadata is literally `user_rating` and
`download_count`. So any host that already talks to registry.modelcontextprotocol.io can point at
tashan instead and get the SAME payload with a measurement attached — no integration, no SDK, no
awareness that we exist beyond one base URL.

    GET https://tashan.sh/v0.1/servers

Response is byte-compatible with the upstream registry (`servers[].server` unchanged, upstream's own
`_meta` block preserved) plus one added key per row:

    "_meta": {
      "io.modelcontextprotocol.registry/official": { ...upstream, untouched... },
      "sh.tashan/measurement": {
        "score": 71, "adoption": 65, "upkeep": 97, "freshness": 91,
        "vitality": "active", "evidence": "86,983 npm downloads/week",
        "tasks": ["web-development", "visual-design"],
        "measured_at": "…", "method": "https://tashan.sh/methodology.html"
      }
    }

Namespaced `sh.tashan/…` per the spec's reverse-DNS convention, so a consumer that does not know us
ignores it and a consumer that does needs no special-casing.

HONESTY CONSTRAINTS, because this is the surface most likely to be consumed without a human reading it:
  - Only capabilities we actually measure appear. No unrated rows padding a count.
  - `score: null` is impossible here — an unscored capability is simply absent, rather than shipping a
    zero that a machine would read as "measured, and bad".
  - The response states its own limits in `metadata` (static snapshot, single page, when it was built).
    A machine consumer cannot ask us a follow-up question, so anything it needs to interpret the number
    has to travel with the number.

Static by design: Cloudflare Pages serves this as a file. No Function, no database, no cold start —
consistent with the rest of the project, and the failure mode is a stale file rather than a 500.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "web", "data", "capabilities.json")
OUT_DIR = os.path.join(ROOT, "web", "v0.1")
BASE = "https://tashan.sh"
SCHEMA = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"


def evidence(c):
    """The raw public signal behind the score, in words a machine can pass through to a human."""
    if c.get("npm_downloads") is not None:
        return f"{c['npm_downloads']:,} npm downloads/week"
    if c.get("gh_stars") is not None:
        return f"{c['gh_stars']:,} stars on its own repository"
    if c.get("config_reach"):
        n = c["config_reach"]
        noun = ("marketplace listing" if c.get("kind") == "plugin" else "public agent config")
        return f"referenced by {n} {noun}" + ("" if n == 1 else "s")
    return "no adoption signal found"


def server_block(c):
    """The registry's own server object. Deliberately minimal: we are a measurement layer, so we do not
    invent install metadata we did not receive — a consumer wanting packages/remotes should read the
    upstream registry, and we say so in `metadata.note`."""
    s = {
        "$schema": SCHEMA,
        "name": c.get("registry_name") or c["name"],
        "description": c.get("description") or "",
        "version": "measured",
    }
    if c.get("title"):
        s["title"] = c["title"]
    if c.get("npm_pkg"):
        s["packages"] = [{"registryType": "npm", "identifier": c["npm_pkg"]}]
    if c.get("source_repo"):
        s["repository"] = {"url": "https://github.com/" + c["source_repo"], "source": "github"}
    return s


def main():
    d = json.load(open(DATA))
    gen = d.get("generated_at", "")
    rows = []
    for c in d["capabilities"]:
        if c.get("tashan_score") is None:      # measured or absent — never a zero standing in for unknown
            continue
        meta = {"sh.tashan/measurement": {
            "score": c["tashan_score"],
            "adoption": c.get("adoption"),
            "upkeep": c.get("upkeep"),
            "freshness": c.get("freshness"),
            "vitality": c.get("vitality"),
            "evidence": evidence(c),
            "expertise": c.get("expertise_verdict"),      # null where ungraded, stated as null not guessed
            "tasks": [t["t"] for t in (c.get("tasks") or [])],
            "url": BASE + "/capability/" + c["slug"] + ".html",
            "measured_at": gen,
            "method": BASE + "/methodology.html",
        }}
        # SETTLED RECEIPTS, for the consumer that cannot ask a follow-up question. Emitted only
        # when paid_seen_at says we asked the chain, so a measured zero ("this address has never
        # been paid") is never confused with silence — the same rule the rest of this file follows
        # for scores. The caveat travels with the number, because an agent has nowhere to read it.
        if c.get("paid_seen_at"):
            meta["sh.tashan/measurement"]["settled"] = {
                "usd": c.get("paid_usd"),
                "payments": c.get("paid_calls"),
                "protocol": "x402", "chain": "base", "measured_at": c["paid_seen_at"],
                "note": ("settled payments at this capability's own payment address, all time. A "
                         "zero here is measured, not missing. Deliberately NOT an input to the "
                         "score: being paid and being well made are different claims."),
            }
        if c.get("registry_status"):
            meta["io.modelcontextprotocol.registry/official"] = {"status": c["registry_status"]}
        rows.append({"server": server_block(c), "_meta": meta})

    rows.sort(key=lambda r: -r["_meta"]["sh.tashan/measurement"]["score"])
    payload = {
        "servers": rows,
        "metadata": {
            "count": len(rows),
            "generated_at": gen,
            # A machine consumer cannot ask a follow-up question, so every caveat travels with the data.
            "note": ("tashan is a measurement subregistry: it scores capabilities on public evidence and "
                     "sells, hosts and runs none of them. Only measured capabilities appear here — an "
                     "unscored capability is absent rather than scored zero. Scores live under "
                     "_meta['sh.tashan/measurement']; every input is public and linked to its source. For install metadata (packages, remotes, "
                     "environment variables) read the upstream registry at "
                     "registry.modelcontextprotocol.io — we do not restate what we did not measure."),
            "limits": ("Static snapshot, single page, no cursor. Regenerated whenever the pipeline runs. "
                       "This file is the BULK mirror and is 5.6 MB — if you are answering one question, "
                       "do not fetch it: GET /v0.1/lookup?name=<pkg> returns one record and "
                       "GET /v0.1/search?q=<query> returns ranked matches, both in a few hundred bytes."),
            "method": BASE + "/methodology.html",
            "license": "Scores CC BY 4.0 — attribute tashan (https://tashan.sh) and link the methodology.",
        },
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "servers")
    json.dump(payload, open(out, "w"), ensure_ascii=False)
    kb = os.path.getsize(out) / 1024
    print(f"subregistry: {len(rows)} measured capabilities -> /v0.1/servers ({kb:.0f} KB)")

    # A COMPACT LOOKUP, because the full mirror answers the wrong question for the common case. A host
    # mirroring the registry wants all of it; an agent about to install ONE thing wants one number, and
    # making it pull 695 KB gz to get it would mean nobody calls this at decision time. Arrays rather
    # than objects: the key names would be most of the bytes.
    #   { "<name>": [score, vitality, evidence] }
    # setdefault, NOT assignment. `rows` is sorted score-descending and 144 names collide (the same
    # product reaching us as both an npm package and a plugin listing), so plain assignment let the LAST
    # write win — the LOWEST score. chrome-devtools-mcp resolved to 20 instead of 93, and an agent asking
    # "is this any good" would have been told no. First write wins = highest score for that name.
    compact = {}
    for r in rows:
        m = r["_meta"]["sh.tashan/measurement"]
        # A FOURTH ELEMENT, APPENDED — never inserted. Every consumer reads [0], [1], [2]; adding to
        # the end cannot break one, and the slug is what turns a hit into a URL. Without it a caller
        # holding a name could not build a link, because the id it derives from is `pkg:`/`registry:`/
        # `plugin:`/`skill:`-prefixed and unrecoverable from the name alone. /v0.1/search returns it
        # so an agent can cite the page it got the number from.
        # Taken from the url _meta already carries, not stored twice: the slug is the short half and
        # repeating the whole URL 6,296 times would be most of the file.
        compact.setdefault(r["server"]["name"],
                           [m["score"], m["vitality"], m["evidence"],
                            m["url"].rsplit("/", 1)[-1][:-5]])
    small = {
        "scores": compact,
        "metadata": {
            "count": len(compact),
            "generated_at": gen,
            "format": "name -> [tashan_score 0-100, vitality, evidence, page slug]",
            "note": ("Quick lookup for 'should I install this'. Absence means unmeasured, never bad. "
                     "Full records with adoption/upkeep/freshness and task tags: /v0.1/servers. "
                     "Method: " + BASE + "/methodology.html — nothing purchasable moves a score."),
            "license": "CC BY 4.0 — attribute tashan (https://tashan.sh).",
        },
    }
    out2 = os.path.join(OUT_DIR, "scores")
    json.dump(small, open(out2, "w"), ensure_ascii=False)
    print(f"lookup:      {len(compact)} names -> /v0.1/scores ({os.path.getsize(out2)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
