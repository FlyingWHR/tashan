#!/usr/bin/env python3
"""tashan — read our own subgraph THROUGH The Graph's Subgraph MCP server.

WHY NOT JUST CALL THE GATEWAY. paid_demand.py can POST GraphQL straight at a query URL, and it still
can. This path exists because it composes two of The Graph's products instead of one: the subgraph is
published to Subgraph Studio and served by The Graph Network, and it is READ through The Graph's own
Subgraph MCP server (https://subgraphs.mcp.thegraph.com/sse) — the same interface an agent would use.

That is not a checkbox. It means the number tashan publishes about paid demand is fetched over the
public, standardised path any agent can reproduce: same server, same tool, same arguments. An
evidence product should be reachable the way it asks others to be reachable, and "you can verify this
yourself with two lines of config" is a stronger claim than "trust our exporter".

    export GRAPH_API_KEY=<gateway api key>      # thegraph.com/studio -> API keys. That is ALL.
    python3 pipeline/subgraph_mcp.py --probe    # proves the whole hop against the index we read
    python3 pipeline/subgraph_mcp.py --selftest # no network, no key
    export TASHAN_SUBGRAPH_ID=<subgraph id>     # point it at ours once that one is published

NO DEPENDENCIES, ON PURPOSE. There is a Node bridge (`npx mcp-remote`) in The Graph's own docs and an
official Python SDK; both would be the third way this repo reaches a network. The MCP SSE transport
is a GET that streams events plus a POST for each JSON-RPC request, which is ~100 lines of urllib —
and the parser is the only part that can be wrong, so that is the part with an offline test.
"""
import json, os, sys, urllib.error, urllib.request

SSE_URL = os.environ.get("GRAPH_MCP_URL", "https://subgraphs.mcp.thegraph.com/sse")
API_KEY = os.environ.get("GRAPH_API_KEY", "")
# Defaults to the x402 settlement index that paid_demand.py actually reads, so `--probe` proves the
# whole hop — client, transport, gateway, subgraph — with nothing but a gateway key. Point it at our
# own subgraph with TASHAN_SUBGRAPH_ID once that is published.
X402_SUBGRAPH = "Cb56epg3EvQ6JRpPfknbkM54QxpzTvLa7mwKNQQfUyoj"
SUBGRAPH_ID = os.environ.get("TASHAN_SUBGRAPH_ID") or os.environ.get("X402_SUBGRAPH_ID") or X402_SUBGRAPH
UA = "tashan/subgraph-mcp (+https://tashan.sh)"
PROTOCOL = "2024-11-05"      # the revision that defines this HTTP+SSE transport


class McpError(RuntimeError):
    """A transport or protocol failure. Never swallowed: a silent no-op here would publish zero
    paid demand and zero is a number people would read as 'nothing has been paid'."""


def sse_events(stream):
    """Yield (event, data) pairs off an SSE byte stream.

    The whole transport hangs on this, so it is written to the spec rather than to the one server we
    happen to be talking to: fields accumulate until a BLANK line dispatches the event, `data:` lines
    concatenate with newlines, a missing `event:` defaults to "message", and a leading space after
    the colon is stripped (exactly one — SSE says so, and a JSON body does not care but an endpoint
    URL would). Comment lines beginning ':' are keep-alives and must be ignored, not parsed.
    """
    event, data = None, []
    for raw in stream:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line == "":
            if data or event:
                yield (event or "message", "\n".join(data))
            event, data = None, []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
    if data or event:
        yield (event or "message", "\n".join(data))


def _absolute(base, endpoint):
    """The endpoint event carries a path, not a URL. Join it to the origin, not to the /sse path."""
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    scheme, _, rest = base.partition("://")
    origin = scheme + "://" + rest.split("/", 1)[0]
    return origin + ("" if endpoint.startswith("/") else "/") + endpoint


class Session:
    """One MCP session over HTTP+SSE: a long-lived GET for replies, a POST per request.

    Single-threaded on purpose. Each POST returns 202 with an empty body and the answer arrives on
    the GET stream, so "send, then read until the id comes back" is the whole loop — no queue, no
    background thread, and nothing to leak if a call raises.
    """

    def __init__(self, url=SSE_URL, key=API_KEY, timeout=45):
        if not key:
            raise McpError("GRAPH_API_KEY is not set — get a gateway key at thegraph.com/studio")
        self.url, self.key, self.timeout, self._id = url, key, timeout, 0
        self.stream = None
        self.post_url = None

    def _headers(self, accept):
        return {"authorization": "Bearer " + self.key, "accept": accept, "user-agent": UA}

    def open(self):
        req = urllib.request.Request(self.url, headers=self._headers("text/event-stream"))
        try:
            self.stream = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            raise McpError(f"{self.url} answered {e.code} — an invalid gateway key answers 401") from e
        self.events = sse_events(self.stream)
        for event, data in self.events:
            if event == "endpoint":
                self.post_url = _absolute(self.url, data.strip())
                break
        if not self.post_url:
            raise McpError("the server never sent an endpoint event; transport is not HTTP+SSE")
        self.request("initialize", {
            "protocolVersion": PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "tashan", "version": "0.1"},
        })
        self.notify("notifications/initialized")
        return self

    def _post(self, body):
        req = urllib.request.Request(
            self.post_url, data=json.dumps(body).encode(),
            headers={**self._headers("application/json"), "content-type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=self.timeout).read()
        except urllib.error.HTTPError as e:
            raise McpError(f"POST {self.post_url} -> {e.code}") from e

    def notify(self, method, params=None):
        self._post({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(self, method, params=None):
        self._id += 1
        want = self._id
        self._post({"jsonrpc": "2.0", "id": want, "method": method, "params": params or {}})
        for event, data in self.events:
            if event != "message" or not data:
                continue
            try:
                msg = json.loads(data)
            except ValueError:
                continue
            if msg.get("id") != want:
                continue                       # a server-initiated request or another reply
            if "error" in msg:
                raise McpError(f"{method}: {msg['error'].get('message', msg['error'])}")
            return msg.get("result", {})
        raise McpError(f"{method}: the stream closed before the reply arrived")

    def call_tool(self, name, arguments):
        return unwrap(self.request("tools/call", {"name": name, "arguments": arguments}))

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *_):
        self.close()


def unwrap(result):
    """MCP tool results are content blocks; a GraphQL answer arrives as TEXT that happens to be JSON.

    Parsed when it parses and returned as a string when it does not, because an error message is also
    a legitimate text block and must not be turned into a crash three frames away from its cause.
    """
    if result.get("isError"):
        raise McpError(str(result.get("content")))
    parts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
    text = "\n".join(p for p in parts if p)
    try:
        return json.loads(text)
    except ValueError:
        return text


def query(graphql, subgraph_id=None, url=SSE_URL, key=API_KEY):
    """Run a GraphQL query against our subgraph, through The Graph's Subgraph MCP.

    Returns the `data` object, so callers are identical whether they went over MCP or straight HTTP.
    """
    sid = subgraph_id or SUBGRAPH_ID
    if not sid:
        raise McpError("TASHAN_SUBGRAPH_ID is not set — publish the subgraph first")
    with Session(url, key) as s:
        out = s.call_tool("execute_query_by_subgraph_id",
                          {"subgraph_id": sid, "query": graphql})
    if isinstance(out, dict):
        if out.get("errors"):
            raise McpError(f"subgraph returned errors: {out['errors']}")
        return out.get("data", out)
    raise McpError(f"unexpected tool payload: {str(out)[:200]}")


def query_counts(ipfs_hash, url=SSE_URL, key=API_KEY):
    """30-day query volume for a deployment — The Graph's own demand signal, not ours."""
    with Session(url, key) as s:
        return s.call_tool("get_deployment_30day_query_counts", {"ipfs_hashes": [ipfs_hash]})


def _selftest():
    """The parser and the unwrapper, against a canned stream. No network, no key, no subgraph."""
    import io
    raw = (b": keep-alive\r\n"
           b"event: endpoint\r\n"
           b"data: /message?sessionId=abc123\r\n"
           b"\r\n"
           b"event: message\r\n"
           b'data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}\r\n'
           b"\r\n"
           b"data: {\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"content\":[{\"type\":\"text\",\r\n"
           b'data: "text":"{\\"data\\":{\\"receivers\\":[{\\"id\\":\\"0xabc\\",\\"totalPaid\\":\\"2500000\\"}]}}"}]}}\r\n'
           b"\r\n")
    events = list(sse_events(io.BytesIO(raw)))
    assert events[0] == ("endpoint", "/message?sessionId=abc123"), events[0]
    assert events[1][0] == "message" and json.loads(events[1][1])["id"] == 1
    # A data field split across two lines must rejoin with a newline, or the JSON is truncated —
    # and an event with no `event:` line defaults to "message".
    assert events[2][0] == "message", events[2]
    payload = json.loads(events[2][1])
    assert payload["id"] == 2, payload
    inner = unwrap(payload["result"])
    assert inner["data"]["receivers"][0]["totalPaid"] == "2500000", inner
    print("  ok — SSE framing: keep-alives ignored, multi-line data rejoined, default event name")

    # The endpoint event carries a PATH. Joining it to the /sse url instead of the origin sends every
    # POST to /sse/message?... which 404s, and the reply never comes — a hang, not an error.
    assert _absolute("https://subgraphs.mcp.thegraph.com/sse", "/message?sessionId=x") == \
        "https://subgraphs.mcp.thegraph.com/message?sessionId=x"
    assert _absolute("https://x.dev/sse", "https://y.dev/m") == "https://y.dev/m"
    print("  ok — the POST endpoint resolves against the origin, not the /sse path")

    # An error block must raise where it happened, not parse into a value a caller would publish.
    try:
        unwrap({"isError": True, "content": [{"type": "text", "text": "bad subgraph id"}]})
        raise AssertionError("an isError result was swallowed")
    except McpError:
        pass
    assert unwrap({"content": [{"type": "text", "text": "not json"}]}) == "not json"
    print("  ok — tool errors raise, non-JSON text passes through")

    # No key must fail loudly at construction. A client that quietly returns nothing would publish
    # "no payments observed", which is a claim about the world rather than about our configuration.
    try:
        Session(key="")
        raise AssertionError("a missing gateway key was accepted")
    except McpError:
        pass
    print("  ok — a missing gateway key is refused, not treated as an empty result")


def main():
    if "--selftest" in sys.argv:
        _selftest()
        return 0
    if "--probe" in sys.argv:
        if not API_KEY:
            print("GRAPH_API_KEY is not set. thegraph.com/studio -> API keys.")
            return 1
        with Session() as s:
            schema = s.call_tool("get_schema_by_subgraph_id", {"subgraph_id": SUBGRAPH_ID})
            print("schema via Subgraph MCP:", str(schema)[:400])
        data = query("{ x402DailyStats_collection(first: 1, orderBy: date, orderDirection: desc)"
                     " { date totalPayments totalVolumeDecimal } }")
        print("latest day via Subgraph MCP:", json.dumps(data)[:300])
        return 0
    print(__doc__.strip().splitlines()[0])
    print("  --probe     query the published subgraph through The Graph's MCP server")
    print("  --selftest  parser + error handling, no network")
    return 0


if __name__ == "__main__":
    sys.exit(main())
