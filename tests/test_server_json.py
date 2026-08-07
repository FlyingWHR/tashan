#!/usr/bin/env python3
"""server.json must satisfy the MCP registry's schema — constraints included, not just field names.

WHY THIS EXISTS AS ITS OWN FILE. tests/test_agent_surface.py already checked server.json and said it
was valid. It was not. It verified that required fields were present, that key names were known, and
that the reverse-DNS name matched its pattern — and never looked at a single length constraint. The
publish came back:

    422 Unprocessable Entity
    {"message":"expected length <= 100","location":"body.description","value":"Score MCP servers…"}

184 characters against a documented maximum of 100. A validator that reports "valid" for a document
the server rejects is worse than no validator: it is the reason nobody checked by hand.

So this reads the constraints OUT OF THE SCHEMA rather than restating them — maxLength, minLength,
pattern, enum, resolved through $ref and allOf — and applies every one it finds. A limit the registry
adds later is enforced here the day it appears, without anyone editing this file.

Network test: skips (does not fail) when the schema is unreachable, so an offline run is not a red
build. The offline half still checks the things we can know locally.

Run: python3 tests/test_server_json.py
"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "server.json")
fail = 0


def ok(name, cond, detail=""):
    global fail
    if not cond:
        fail = 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + detail) if detail and not cond else ""))


if not os.path.exists(SERVER):
    print("  -- no server.json, nothing to validate")
    sys.exit(0)
doc = json.load(open(SERVER, encoding="utf-8"))

print("# offline: the manifest agrees with what we publish")
cli = json.load(open(os.path.join(ROOT, "cli", "package.json"), encoding="utf-8"))
pkg = (doc.get("packages") or [{}])[0]
ok("mcpName in package.json equals the manifest name", cli.get("mcpName") == doc.get("name"),
   f"{cli.get('mcpName')!r} vs {doc.get('name')!r} — the registry rejects a publish where these differ")
ok("versions agree across manifest, package entry and package.json",
   doc.get("version") == pkg.get("version") == cli.get("version"),
   f"{doc.get('version')} / {pkg.get('version')} / {cli.get('version')}")
ok("the package identifier is the package we publish", pkg.get("identifier") == cli.get("name"))

url = doc.get("$schema")
ok("the manifest declares which schema version it targets", bool(url))
if not url:
    print("\nSERVER.JSON FAILED")
    sys.exit(1)

try:
    schema = json.load(urllib.request.urlopen(url, timeout=20))
except Exception as e:
    print(f"\n  -- schema unreachable ({type(e).__name__}), skipping the constraint pass")
    print("SERVER.JSON OK (offline)" if not fail else "SERVER.JSON FAILED")
    sys.exit(fail)

defs = schema.get("definitions") or schema.get("$defs") or {}
root = defs[schema["$ref"].split("/")[-1]] if "$ref" in schema else schema


def constraints(node, path=""):
    """Every constraint the schema imposes, resolved through $ref and allOf.

    Read from the schema rather than restated here, so a limit the registry adds later is enforced
    the day it appears instead of the day someone remembers to copy it.
    """
    out = {}
    if "$ref" in node:
        return constraints(defs[node["$ref"].split("/")[-1]], path)
    for sub in node.get("allOf", []):
        out.update(constraints(sub, path))
    for k, v in (node.get("properties") or {}).items():
        c = {x: v[x] for x in ("maxLength", "minLength", "pattern", "enum") if x in v}
        if c:
            out[path + k] = c
        if "$ref" in v or v.get("type") == "object" or "properties" in v:
            out.update(constraints(v, path + k + "."))
        if v.get("type") == "array" and isinstance(v.get("items"), dict):
            out.update(constraints(v["items"], path + k + "[]."))
    return out


def walk(node, path=""):
    """Flatten the document to the same dotted paths the constraint map uses."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}{k}." if isinstance(v, (dict, list)) else f"{path}{k}")
            if not isinstance(v, (dict, list)):
                yield f"{path}{k}", v
    elif isinstance(node, list):
        for item in node:
            yield from walk(item, path[:-1] + "[].")


cons = constraints(root)
print()
print(f"# schema constraints, applied ({len(cons)} declared in {url.rsplit('/', 2)[-2]})")
checked = 0
for path, value in walk(doc):
    c = cons.get(path)
    if not c or not isinstance(value, str):
        continue
    checked += 1
    if "maxLength" in c:
        ok(f"{path} within maxLength {c['maxLength']} (is {len(value)})", len(value) <= c["maxLength"],
           f"{len(value)} chars — the registry answers 422 for this")
    if "minLength" in c:
        ok(f"{path} meets minLength {c['minLength']}", len(value) >= c["minLength"])
    if "pattern" in c:
        ok(f"{path} matches {c['pattern']}", re.fullmatch(c["pattern"], value) is not None, repr(value))
    if "enum" in c:
        ok(f"{path} is one of {c['enum']}", value in c["enum"], repr(value))
ok(f"the constraint pass actually inspected fields ({checked})", checked > 0,
   "nothing matched the constraint map — the schema shape changed, fix this test")

req = root.get("required") or []
ok(f"every required field is present ({', '.join(req)})", all(r in doc for r in req),
   str([r for r in req if r not in doc]))
unknown = [k for k in doc if k not in (root.get("properties") or {})]
ok("no unknown top-level field", not unknown, str(unknown))

print()
print("SERVER.JSON OK" if not fail else "SERVER.JSON FAILED")
sys.exit(fail)
