// GET /.well-known/x402 — everything we sell, in one machine-readable list.
//
// WHY. This is how x402 crawlers enumerate a seller without guessing routes, and agent-tools.cloud
// probes it by name. We 404'd on it, so our first directory listing came back `health: down` and
// never appeared in the index — accepted, verified, and invisible. Listed sellers that answer it
// (stableenrich.dev, x402.twit.sh, blockrun.ai) all serve the same shape: {version, resources}.
//
// IT ENUMERATES `PRICED`, NEVER ITS OWN LIST. A second copy of "what we sell" is a second thing to
// forget: the price would drift, or a new endpoint would ship undiscoverable. Adding a priced
// resource in _x402.js now publishes it here on the same deploy.
import { PRICED } from "../api/_x402.js";

export const onRequestGet = ({ request }) => {
  const origin = new URL(request.url).origin;
  const resources = Object.values(PRICED)
    .filter((p) => p && p.path)
    .map((p) => origin + p.path);
  return new Response(JSON.stringify({ version: 1, resources }, null, 1), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      // Short cache: this changes only on deploy, but a crawler re-reading it hourly is the point.
      "cache-control": "public, max-age=3600",
      "access-control-allow-origin": "*",
    },
  });
};
