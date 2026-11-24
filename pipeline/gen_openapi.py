#!/usr/bin/env python3
"""/openapi.json — the public API described in the one format every gateway reads.

    python3 pipeline/gen_openapi.py
    python3 pipeline/gen_openapi.py --selftest

WHY THIS EXISTS. Our agent endpoints have been live and free for months and were documented only in
prose on /for-hosts.html, which is a page for a human who has already found us. Every gateway,
client generator and agent platform in this space onboards an API the same way: give us an OpenAPI
document and we will do the rest. Bazantic's `baz gateway add --spec-url …` is exactly that, and
without a spec the answer to "can an agent use your project without you there to explain it" is no
— which is, word for word, the question that prize asks.

DERIVED, NOT TYPED. The counts and the prices come from the same files the site and the paywall read
(`web/data/index.json`, `data/entitlements.json`), so a spec cannot promise a price we do not charge
or a corpus size we do not have. The paths themselves are hand-written because they are a contract:
they change when we decide they change, not when a file moves.

WHAT IT DELIBERATELY DOES NOT DO. It documents only the free-to-ask surface plus the two endpoints
that answer 402 with their terms in the body. The licence-gated /api/* endpoints are not in here:
they need an account, and an agent discovering us through a gateway has none. Publishing them would
advertise a door that answers 401 to every reader of this document.
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://tashan.sh"


def facts():
    """Corpus size and the two per-call prices, read from what actually serves them."""
    out = {"measured": None, "kit_usd": None, "audit_usd": None}
    p = os.path.join(ROOT, "web", "data", "index.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                out["measured"] = (json.load(fh) or {}).get("measured")
        except (OSError, ValueError):
            pass
    # The prices live in the Functions that charge them; reading the source keeps the document and
    # the paywall from drifting the way the pricing page and the code once did.
    with open(os.path.join(ROOT, "functions", "api", "_x402.js"), encoding="utf-8") as source:
        prices = source.read()
    for key, resource in (("kit_usd", "capability-kit"), ("audit_usd", "config-audit")):
        match = re.search(r'"' + resource + r'":\s*\{.*?\busd:\s*([0-9.]+),', prices, re.S)
        if not match:
            raise ValueError(f"Missing public price for {resource}")
        out[key] = match[1]
    return out


def spec():
    f = facts()
    n = f"{f['measured']:,}" if f["measured"] else "every measured"
    kit = f["kit_usd"]
    aud = f["audit_usd"]
    cap = {"type": "object", "properties": {
        "id": {"type": "string", "example": "pkg:tavily-mcp"},
        "name": {"type": "string"},
        "generated_at": {"type": ["string", "null"], "format": "date-time"},
        "measured": {"type": "boolean"},
        "url": {"type": ["string", "null"], "format": "uri"},
        "markdown": {"type": ["string", "null"], "format": "uri"},
        "tashan_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100,
                         "description": "Absent when unmeasured. Never 0 to mean unknown."},
        "vitality": {"type": ["string", "null"], "enum": ["active", "stable", "abandoned", None]},
        "expertise": {"type": ["string", "null"], "enum": ["deep", "solid", "thin", None]},
        "evidence": {"type": "string", "example": "32,517 npm downloads/week"},
    }}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "tashan",
            "summary": "Measurements of the tools and skills you can give an AI agent.",
            "description":
                f"Ask anything about a capability and the answer is free: {n} MCP servers, agent "
                "skills and plugins, scored on upkeep, freshness and real adoption, and audited "
                "against OSV at the version you would install today.\n\n"
                "**Asking is free. Assembling is paid.** Every score and every risk finding is "
                "free with no key and no quota. The two endpoints that do work for you — pinning a "
                "kit to versions the scan cleared, and returning the history behind a row — answer "
                "HTTP 402 with their terms in the body, payable per call over x402 on Base.\n\n"
                "**Not a security audit.** We read public evidence. We do not run the server, read "
                "its source, or test it for prompt injection. A clean result means nothing *known* "
                "is wrong, and a capability we have never measured is reported as unmeasured — "
                "never as safe.\n\n"
                "**Nobody can buy a rank.** Enforced by a test that reads the scorer's source: "
                "https://tashan.sh/methodology.html",
            "version": "0.1.0",
            "license": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
            "contact": {"name": "tashan", "url": SITE, "email": "hello@tashan.sh"},
        },
        "servers": [{"url": SITE}],
        "paths": {
            "/v0.1/lookup": {"get": {
                "operationId": "lookupCapability",
                "summary": "Everything we hold about one capability, by name",
                "description":
                    "The cheapest complete answer: score, health, documentation grade, and every "
                    "security finding — which advisory, its severity, the version that fixes it, "
                    "and the exact command the package runs at install time. Free.\n\n"
                    "A name we have never seen returns `measured: false`. That means unmeasured, "
                    "not unsafe — do not present absence as a warning.",
                "parameters": [{"name": "name", "in": "query", "required": True,
                                "schema": {"type": "string"}, "example": "tavily-mcp",
                                "description": "npm package, capability name or slug"}],
                "responses": {"200": {"description": "The measurement, or measured:false",
                                      "content": {"application/json": {"schema": cap}}}}}},
            "/v0.1/search": {"get": {
                "operationId": "searchCapabilities",
                "summary": "Ranked search across the measured corpus",
                "parameters": [
                    {"name": "q", "in": "query", "required": True, "schema": {"type": "string"},
                     "example": "postgres"},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}}],
                "responses": {"200": {"description": "Ranked matches", "content": {
                    "application/json": {"schema": {"type": "object", "properties": {
                        "results": {"type": "array", "items": cap}}}}}}}}},
            "/v0.1/scores": {"get": {
                "operationId": "allScores",
                "summary": "Every score in one file",
                "description": "A flat map of name to [score, vitality, evidence]. Fetch once and "
                               "decide locally instead of asking per package.",
                "responses": {"200": {"description": "name -> [score, vitality, evidence]",
                                      "content": {"application/json": {"schema": {"type": "object"}}}}}}},
            "/v0.1/servers": {"get": {
                "operationId": "subregistry",
                "summary": "The MCP registry shape, with a measurement attached",
                "description": "Byte-compatible with registry.modelcontextprotocol.io. Each entry "
                               "keeps its shape and gains one namespaced block, `sh.tashan/"
                               "measurement`, so nothing you already parse changes. Unscored "
                               "servers are absent rather than zero.",
                "responses": {"200": {"description": "Registry-shaped records",
                                      "content": {"application/json": {"schema": {"type": "object"}}}}}}},
            "/v0.1/kit": {"post": {
                "operationId": "kitForTask",
                "summary": "Name a job, get something that runs",
                "description":
                    "The free shortlist reports exclusions and counts.verified_installs. When possible it reserves "
                    "one place for a runnable package with an advisory-free scan of its current version within seven days. "
                    f"With kit=true, ${kit} buys verified version pins and a host configuration. "
                    "If no package qualifies, the paid request returns 422 without quoting a charge.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object", "anyOf": [{"required": ["task"]}, {"required": ["goal"]}], "properties": {
                        "goal": {"type": "string", "minLength": 1, "example": "I need to scrape websites"},
                        "task": {"type": "string", "example": "web-scraping"},
                        "client": {"type": "string",
                                   "enum": ["claude-code", "claude-desktop", "cursor", "vscode", "windsurf"]},
                        "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 8},
                        "kit": {"type": "boolean", "default": False,
                                "description": f"Assemble it. Paid: ${kit} per call."}}}}}},
                "responses": {
                    "200": {"description": "The shortlist, or the assembled kit when paid"},
                    "422": {"description": "The shortlist has no current, verified npm pins. No payment is requested."},
                    "402": {"description": f"Payment required (${kit}). The body carries the price, "
                                           "a checkout link, and the free endpoints that answer the "
                                           "same question."}}}},
            # THE ONE NOBODY ELSE HAS. Everything above measures a proxy for demand; this measures
            # money. It was reachable only as a static file and as a tool on our own MCP server,
            # which means an agent had to already know we existed to ask. Describing it here is what
            # makes it an API rather than a download.
            "/data/demand.json": {"get": {
                "operationId": "paidDemand",
                "summary": "Base USDC payment observations",
                "description": "Coinbase Bazaar, PayAI and MPP directory coverage, plus indexed receipts at sampled Base receiver addresses. `directory` gives the directory harvest date, eligible resources and reported 30-day activity. `measured_at`, `cohort_date` and `indexed_block` distinguish the chain query time, its sample and the latest indexed block. A shared receiver is excluded from catalog attribution. An address balance or payment count does not establish sales by an individual service. Payment is not an input to any score.",
                "responses": {"200": {"description": "The market, and the rows behind it",
                                      "content": {"application/json": {"schema": {
                    "type": "object", "properties": {
                        "providers": {"type": "object", "description": "Per-source resource or service counts, exact x402 URL overlap and MPP payment methods. Directory units are not additive."},
                        "directory": {"type": "object", "description": "Coinbase Bazaar resource counts, coverage and harvest date"},
                        "measured_at": {"type": ["string", "null"]},
                        "cohort_date": {"type": "string"},
                        "indexed_block": {"type": ["object", "null"], "description": "Fixed Base block number and UTC timestamp"},
                        "economy": {"type": ["object", "null"], "properties": {
                            "paid_usd": {"type": "number"},
                            "calls": {"type": "integer"},
                            "receivers_paid": {"type": "integer"},
                            "receivers_never_paid": {"type": "integer"},
                            "median_usd": {"type": "number"},
                            "top1_share": {"type": "number"}}},
                        "records": {"type": "array", "items": {"type": "object", "properties": {
                            "address": {"type": "string"},
                            "hosts": {"type": "array", "items": {"type": "string"}},
                            "capabilities": {"type": "array", "items": {"type": "string"}},
                            "shared": {"type": "boolean",
                                       "description": "True when several services publish this "
                                                      "address. Never attributed to one project."},
                            "paid_usd": {"type": "number"},
                            "calls": {"type": "integer"}}}}}}}}}}}},
            "/v0.1/audit": {"post": {
                "operationId": "auditConfig",
                "summary": "Hand over a config, get back what is rotting",
                "description":
                    "Free: every risk we hold about every capability you name — advisories at the "
                    "version you would install today, deprecation, archived repos, one maintainer "
                    f"left.\n\n${aud} with `history: true`: the score series behind each row and "
                    "its direction of travel. Direction is the one thing a static index cannot "
                    "tell you.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object", "anyOf": [{"required": ["servers"]}, {"required": ["history", "count"],
                        "properties": {"history": {"const": True}}, "not": {"required": ["servers"]}}], "properties": {
                        "count": {"type": "integer", "minimum": 1, "description": "Quote history without transmitting package names."},
                        "servers": {"type": "array", "minItems": 1, "description": "The first 200 names are audited.", "items": {"type": "string"},
                                    "example": ["tavily-mcp", "firecrawl-mcp"]},
                        "history": {"type": "boolean", "default": False,
                                    "description": f"Add the series. Paid: ${aud} per call."}}}}}},
                "responses": {
                    "200": {"description": "Findings per named capability"},
                    "402": {"description": f"Payment required (${aud}), terms in the body."}}}},
        },
        "externalDocs": {"description": "How every number is derived",
                         "url": f"{SITE}/methodology.html"},
    }


def _selftest():
    s = spec()
    assert s["openapi"].startswith("3.1")
    paths = s["paths"]
    assert set(paths) == {"/v0.1/lookup", "/v0.1/search", "/v0.1/scores", "/v0.1/servers",
                          "/v0.1/kit", "/v0.1/audit", "/data/demand.json"}, sorted(paths)
    # The money signal must keep its caveats wherever it is described. An agent reading only this
    # document must not come away thinking unpaid means bad.
    pd = paths["/data/demand.json"]["get"]["description"]
    assert "shared receiver is excluded" in pd and "does not establish sales" in pd and "indexed_block" in pd
    ids = [op["operationId"] for p in paths.values() for op in p.values()]
    assert len(ids) == len(set(ids)), f"duplicate operationId: {ids}"
    # THE PAID ENDPOINTS MUST DOCUMENT THE 402. A gateway that does not know a route can answer 402
    # treats it as an outage and stops calling — which would silently delete our only per-call
    # revenue path from every agent that onboarded through a spec.
    for p in ("/v0.1/kit", "/v0.1/audit"):
        assert "402" in paths[p]["post"]["responses"], f"{p} hides its price from the gateway"
    # A LICENCE-GATED ROUTE MUST NEVER APPEAR. It answers 401 to every reader of this document.
    assert not [p for p in paths if p.startswith("/api/")], "licence-gated routes leaked into the spec"
    # The caveats are the product. A spec that drops them sells a claim we refuse to make.
    d = s["info"]["description"]
    for must in ("Not a security audit", "never as safe", "Nobody can buy a rank", "Asking is free"):
        assert must in d, f"the spec dropped: {must}"
    assert json.dumps(s), "spec must be JSON-serialisable"
    print("ok — openapi: 7 paths, prices declared, 402 documented, no gated route, caveats intact")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    out = os.path.join(ROOT, "web", "openapi.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(spec(), fh, indent=1, ensure_ascii=False)
    print(f"openapi: {len(spec()['paths'])} paths -> web/openapi.json  ({SITE}/openapi.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
