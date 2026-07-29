// tashan — shared, on every page: active-nav marking + first-party analytics.
(function () {
  "use strict";

  // ---- active nav link ----
  var path = location.pathname.replace(/index\.html$/, "") || "/";
  document.querySelectorAll(".nav__links a").forEach(function (a) {
    var href = a.getAttribute("href").replace(/index\.html$/, "") || "/";
    if (href === path) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });

  // ---- analytics: first-party, cookieless, CSP-clean (same-origin beacon to /api/e) ----
  // No cookies, no localStorage, no fingerprint, no third-party script. Honors Do-Not-Track /
  // Global-Privacy-Control. Session id is a random in-memory value (this tab only) purely to stitch a
  // funnel within one visit; it is never persisted, so nobody is tracked across sessions. Silent-fail:
  // if the collector isn't deployed (local dev), beacons no-op and never touch the page.
  var DNT = navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true;
  var sid = Math.random().toString(36).slice(2, 10);
  var host = location.hostname;

  function send(ev, props) {
    if (DNT) return;
    var body = {
      e: ev,
      p: path,                                   // page path (no query, no hash — no PII)
      r: document.referrer ? hostOf(document.referrer) : "",   // referrer HOST only
      s: sid,
      w: window.innerWidth < 700 ? "sm" : window.innerWidth < 1100 ? "md" : "lg"  // coarse viewport bucket
    };
    if (props) for (var k in props) if (props[k] != null) body[k] = props[k];
    try {
      var payload = JSON.stringify(body);
      if (navigator.sendBeacon) { navigator.sendBeacon("/api/e", payload); return; }
      fetch("/api/e", { method: "POST", body: payload, keepalive: true, headers: { "Content-Type": "application/json" } }).catch(function () {});
    } catch (e) { /* analytics must never break the page */ }
  }
  function hostOf(u) { try { return new URL(u).hostname; } catch (e) { return ""; } }

  // public hook so other scripts (⌘K search, etc.) can record events
  window.t = { track: send };

  // page view
  send("pageview");

  // one delegated listener captures the PLG-relevant interactions without per-page wiring
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    var btn = e.target.closest && e.target.closest("[data-copy], .install__copy, .embed__copy");
    if (btn) {
      var what = btn.className.indexOf("embed") >= 0 ? "badge"
               : btn.className.indexOf("install") >= 0 ? "install"
               : (btn.getAttribute("data-copy-label") || "copy");
      send("copy", { k: what });
      return;
    }
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (/^https?:\/\//.test(href)) {
      var h = hostOf(href);
      if (h && h !== host) send("outbound", { k: h, v: a.getAttribute("data-src") || "" });   // registry / repo / community
    } else if (href.indexOf("mailto:") === 0) {
      // THE ONLY CONVERSION EVENT ON THE SITE. Every paid-intent CTA is a mailto — the Pro waitlist
      // and the "embedding tashan in your product" contact — because there is no checkout yet. The
      // outbound branch above only matches ^https?://, so all of it recorded nothing, and the pricing
      // page's entire job (find out which part people would pay for) was unmeasurable. The subject
      // line distinguishes waitlist from teams from product enquiry, so key on that, not the address.
      var subj = (href.split("subject=")[1] || "").split("&")[0];
      send("intent", { k: decodeURIComponent(subj) || "email", v: location.pathname });
    } else if (href.indexOf("/capability/") === 0) {
      send("conav", { k: href.slice(12).replace(/\.html$/, "") });                              // graph traversal (co-use / board)
    }
  }, true);
})();
