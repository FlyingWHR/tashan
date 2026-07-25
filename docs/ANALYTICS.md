# tashan — analytics (first-party, privacy-first, PLG-ready)

> A cookieless, CSP-clean event pipeline that ships with the site. No third-party script, no consent
> banner needed (nothing to consent to — no cookies, no cross-site identifiers, no IP stored). It costs
> **$0** on Cloudflare's free Analytics Engine and is **SQL-queryable** for product-led-growth funnels.

## How it works

```
browser (web/js/site.js)  ──sendBeacon──►  /api/e  (functions/api/e.js)  ──writeDataPoint──►  Analytics Engine
  cookieless, honors DNT/GPC              same-origin, CSP-clean            free, SQL-queryable dataset
```

- **Client** (`web/js/site.js`, on every page): fires a `pageview` on load and captures the PLG-relevant
  interactions via one delegated listener — **copy** (install snippet / badge), **outbound** (registry /
  repo / community links, keyed by host), **conav** (co-use / board → capability, the graph traversal).
  Other scripts can record anything via `window.t.track(event, props)`.
- **Privacy:** no cookies, no `localStorage`, no fingerprint. Honors `Do-Not-Track` and
  `Global-Privacy-Control` (beacons suppressed entirely). The session id is a random **in-memory** value
  for *this tab only* — never persisted, so no one is tracked across visits. Only a coarse viewport
  bucket, referrer **host** (not full URL), and CF **country** (no IP) are recorded.
- **CSP-clean:** the beacon POSTs to same-origin `/api/e`, already allowed by `connect-src 'self'` in
  `web/_headers`. **No CSP change, no third-party origin.**
- **Silent-fail:** if the collector isn't deployed (local `python3 -m http.server`), beacons no-op —
  analytics never touches the page or throws.

## Activation (one step, ~2 minutes, in the Cloudflare dashboard)

The client and Function already ship. To start collecting once deployed to Cloudflare Pages:

1. **Enable Analytics Engine** for the account (Workers & Pages → Analytics Engine — free tier).
2. **Bind the dataset** to the Pages project: *Settings → Functions → Analytics Engine bindings* →
   Variable name `TASHAN_AE`, dataset name `tashan_events` (any name; the code reads the **binding**,
   `env.TASHAN_AE`). Or in `wrangler.toml`:
   ```toml
   [[analytics_engine_datasets]]
   binding = "TASHAN_AE"
   dataset = "tashan_events"
   ```
3. **Redeploy.** Done — every page view and event now lands in the dataset. (Until the binding exists,
   `/api/e` still returns 204; nothing errors.)

## Querying (PLG funnels)

Analytics Engine is queryable with SQL over the account's API token
([API docs](https://developers.cloudflare.com/analytics/analytics-engine/sql-api/)). Blob columns map
as: `blob1` event · `blob2` path · `blob3` referrer host · `blob4` context key · `blob5` value ·
`blob6` viewport · `blob7` country · `blob8` session.

```sql
-- top capabilities by detail-page views (last 7 days)
SELECT blob2 AS path, SUM(_sample_interval) AS views
FROM tashan_events
WHERE blob1 = 'pageview' AND blob2 LIKE '/capability/%' AND timestamp > NOW() - INTERVAL '7' DAY
GROUP BY path ORDER BY views DESC LIMIT 25;

-- the money funnel: which capabilities convert a view into an install-snippet copy
SELECT blob2 AS path,
       SUM(IF(blob1='pageview',_sample_interval,0)) AS views,
       SUM(IF(blob1='copy',_sample_interval,0))     AS install_copies
FROM tashan_events
WHERE blob2 LIKE '/capability/%' AND timestamp > NOW() - INTERVAL '30' DAY
GROUP BY path ORDER BY install_copies DESC LIMIT 25;

-- where trust flows OUT to (registries, repos, community) — the "neutral instrument points outward" signal
SELECT blob4 AS outbound_host, SUM(_sample_interval) AS clicks
FROM tashan_events
WHERE blob1 = 'outbound' AND timestamp > NOW() - INTERVAL '7' DAY
GROUP BY outbound_host ORDER BY clicks DESC LIMIT 20;

-- acquisition: which referrers send traffic
SELECT blob3 AS referrer, SUM(_sample_interval) AS sessions
FROM tashan_events
WHERE blob1 = 'pageview' AND blob3 != '' AND timestamp > NOW() - INTERVAL '7' DAY
GROUP BY referrer ORDER BY sessions DESC LIMIT 20;
```

## Events

| event | fired when | context (`k`) |
|---|---|---|
| `pageview` | every page load | — |
| `copy` | install snippet / badge copy | `install` \| `badge` \| custom |
| `outbound` | click to an external host | the host (registry / repo / community) |
| `conav` | click into a `/capability/<slug>` page | the destination slug |
| *custom* | `window.t.track("name", {k, v})` from any script | anything |

## Not this

- **Cloudflare Web Analytics** (the `beacon.min.js` product) would need its script from
  `static.cloudflareinsights.com` — a third-party origin that violates our strict `script-src 'self'` /
  `connect-src 'self'` — and only counts page views (no PLG event funnels). The first-party pipeline
  above is CSP-clean, event-capable, and equally free. That's why we built it.
