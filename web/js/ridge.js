// tashan — hero 山水, rendered as "variable typographic ASCII" (after chenglou's pretext technique):
// a SMOOTH grayscale field — layered mountain silhouettes (前 near-bright/low → 后 far-dim/high), drifting
// mist, and the day/night key light — is painted to a tiny offscreen canvas, read back per cell, and drawn
// as glyphs from a density ramp at a CONTINUOUS font-weight (light→bold). Tone comes from typography, not
// directional /\ hatching — so no scratch, no banding, no dash runs. Self-hosted, strict-CSP-safe (own
// canvas, no external image → getImageData isn't tainted). Pauses when hidden; one static frame under
// prefers-reduced-motion.
(function () {
  "use strict";
  var cv = document.getElementById("ridge");
  if (!cv || !cv.getContext) return;
  var ctx = cv.getContext("2d", { alpha: true });
  var pre = document.querySelector(".ascii-range");
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  var FONT_PX = 15, LINE = 17, CELLW = 9;
  var RAMP = " .-:=+ic*oaeznxsuQO08B#%@";        // light → heavy ink coverage (ASCII-only: no missing-glyph tofu)
  var SKY = 0.40;                                 // upper band kept clear (the headline lives there)
  var DAY_MS = 240000;                            // a full day↔night in ~4 min

  var W = 0, H = 0, cols = 0, rows = 0, running = true, prev = 0, t0 = 0, resolveStart = 0, dayStart = 0, curWind = 0.5;
  var layers = [], mist = [];
  var fcv = document.createElement("canvas"), fctx = fcv.getContext("2d", { willReadFrequently: true });

  // ---------- day/night: key-light tint + ambient + sun/moon phase (sky itself isn't drawn) ----------
  var SKYK = [
    { p: 0.00, lit: [225, 165, 95],  amb: 0.80, orb: 1 },   // dawn (amber)
    { p: 0.25, lit: [110, 235, 175], amb: 1.00, orb: 1 },   // noon (jade day)
    { p: 0.50, lit: [230, 130, 80],  amb: 0.82, orb: 1 },   // dusk (orange)
    { p: 0.75, lit: [140, 175, 230], amb: 0.66, orb: 0 },   // night (moonlit blue)
    { p: 1.00, lit: [225, 165, 95],  amb: 0.80, orb: 1 }
  ];
  function lerp(a, b, t) { return a + (b - a) * t; }
  function rgb(a, b, t) { return [Math.round(lerp(a[0], b[0], t)), Math.round(lerp(a[1], b[1], t)), Math.round(lerp(a[2], b[2], t))]; }
  function daySample(dp) {
    for (var i = 0; i < SKYK.length - 1; i++) {
      if (dp >= SKYK[i].p && dp < SKYK[i + 1].p) {
        var t = (dp - SKYK[i].p) / (SKYK[i + 1].p - SKYK[i].p);
        return { lit: rgb(SKYK[i].lit, SKYK[i + 1].lit, t), amb: lerp(SKYK[i].amb, SKYK[i + 1].amb, t), orb: lerp(SKYK[i].orb, SKYK[i + 1].orb, t) };
      }
    }
    return { lit: SKYK[0].lit, amb: SKYK[0].amb, orb: SKYK[0].orb };
  }

  // ---------- geometry: three rolling ridgelines, seeded fresh each visit ----------
  function makeHill(seed, freq, base, amp) {
    var P = [];
    for (var k = 0; k < 4; k++) P.push({ f: (k + 1) * freq, a: amp / (k + 1.4), ph: seed * (k + 1) * 1.7 });
    return function (c) { var y = base; for (var i = 0; i < P.length; i++) y += P[i].a * Math.sin(c * 0.03 * P[i].f + P[i].ph); return y; };
  }
  function env(c) { var x = c / cols; return x * x * (3 - 2 * x); }
  function reseed() {
    var s = 1 + Math.random() * 90;
    // val = field brightness of the layer: 近山 bright & low (front) → 远山 dim & high (misty distance)
    layers = [
      { crest: makeHill(s + 3, 0.9, 0.62, 0.055), lift: 0.08, val: 0.34 },   // 远山
      { crest: makeHill(s + 7, 1.1, 0.75, 0.075), lift: 0.13, val: 0.60 },   // 中景
      { crest: makeHill(s + 1, 1.3, 0.88, 0.100), lift: 0.18, val: 1.00 }    // 近山
    ];
    // drifting mist wisps (soft additive blobs) — the living 云雾 of the scene
    mist = [];
    for (var i = 0; i < 7; i++) mist.push({ x: Math.random(), y: 0.74 + Math.random() * 0.16, r: 0.10 + Math.random() * 0.14, ph: Math.random() * 6.28, sp: 0.5 + Math.random() * 0.9 });
    var hr = new Date().getHours() + new Date().getMinutes() / 60;    // grounded in the visitor's real time-of-day
    dayStart = ((hr - 6 + 24) % 24) / 24;
  }
  function windAt(now) {   // slow, organic breeze (drives the mist drift)
    var w = 0.5 + 0.30 * Math.sin(now * 0.00003) + 0.17 * Math.sin(now * 0.0001 + 1.3) + 0.11 * Math.sin(now * 0.00025 + 2.1);
    return w < 0.05 ? 0.05 : w;
  }

  // ---------- paint the smooth grayscale FIELD, return its pixels ----------
  function paintField(now, sky, dp, wind) {
    var fw = cols, fh = rows;
    fctx.globalCompositeOperation = "source-over";
    fctx.fillStyle = "#000"; fctx.fillRect(0, 0, fw, fh);
    // mountains far→near (near paints over far = clean 前后 occlusion). Painted PER COLUMN so EACH column's
    // crest is the bright lit edge — a clear ridgeline — fading down to a dark valley base (contrast = shape).
    for (var li = 0; li < layers.length; li++) {
      var L = layers[li], peak = Math.min(1, 0.62 + 0.38 * L.val);
      for (var c = 0; c < fw; c++) {
        var y0 = (L.crest(c) - L.lift * env(c)) * fh;
        if (y0 >= fh - 0.5) continue;
        var g = fctx.createLinearGradient(0, y0, 0, fh);
        g.addColorStop(0, "rgba(255,255,255," + peak.toFixed(3) + ")");
        g.addColorStop(0.4, "rgba(255,255,255," + (peak * 0.42).toFixed(3) + ")");
        g.addColorStop(1, "rgba(255,255,255,0.02)");
        fctx.fillStyle = g; fctx.fillRect(c, y0, 1.02, fh - y0);
      }
    }
    fctx.globalCompositeOperation = "lighter";
    // key light: brighten the lit (sun/moon) side, ambient-scaled — this is what shifts with day/night
    var prog = dp < 0.5 ? dp / 0.5 : (dp - 0.5) / 0.5;
    var ox = prog * fw, oy = fh * (0.30 - 0.18 * Math.sin(prog * Math.PI));
    var lg = fctx.createRadialGradient(ox, oy, 0, ox, oy, fw * 0.75);
    lg.addColorStop(0, "rgba(255,255,255," + (0.20 * sky.amb).toFixed(3) + ")"); lg.addColorStop(1, "rgba(255,255,255,0)");
    fctx.fillStyle = lg; fctx.fillRect(0, 0, fw, fh);
    // mist: soft radial wisps drifting on the wind (additive → they read as brighter glyph clouds)
    for (var i = 0; i < mist.length; i++) {
      var m = mist[i];
      var mx = (((m.x + now * 0.0000045 * m.sp * (0.5 + wind)) % 1.16) - 0.08) * fw;
      var my = (m.y + 0.014 * Math.sin(now * 0.00003 * m.sp + m.ph)) * fh;
      var mr = m.r * fw;
      var mg = fctx.createRadialGradient(mx, my, 0, mx, my, mr);
      mg.addColorStop(0, "rgba(255,255,255,0.13)"); mg.addColorStop(0.6, "rgba(255,255,255,0.05)"); mg.addColorStop(1, "rgba(255,255,255,0)");
      fctx.fillStyle = mg; fctx.fillRect(mx - mr, my - mr, mr * 2, mr * 2);
    }
    fctx.globalCompositeOperation = "source-over";
    return fctx.getImageData(0, 0, fw, fh).data;
  }

  // stone (dim) → time-of-day key light (bright), by brightness
  function tint(b, sky) {
    var base = [72, 74, 70], lit = sky.lit, t = Math.max(0, Math.min(1, (b - 0.12) / 0.88));
    return "rgb(" + Math.round(base[0] + (lit[0] - base[0]) * t) + "," + Math.round(base[1] + (lit[1] - base[1]) * t) + "," + Math.round(base[2] + (lit[2] - base[2]) * t) + ")";
  }

  function frame(now, ease) {
    var dp = ((now - t0) / DAY_MS + dayStart) % 1;
    var sky = daySample(dp);
    var wind = curWind = windAt(now);
    ctx.clearRect(0, 0, W, H);
    var data = paintField(now, sky, dp, wind);
    ctx.textBaseline = "top";
    var lastW = -1, drift = now * 0.00022;                      // texture slides slowly (alive, not flickering)
    for (var r = Math.floor(rows * SKY) - 2; r < rows; r++) {   // skip the clear upper band entirely
      if (r < 0) r = 0;
      var rowBase = r * LINE, ri = r * cols;
      for (var c = 0; c < cols; c++) {
        var b = data[(ri + c) * 4] / 255;                       // grayscale → brightness
        if (b <= 0.05) continue;
        // dither: a little drifting per-cell noise breaks the smooth iso-brightness rows into organic
        // texture (kills the horizontal +++ banding) and makes the glyphs shimmer as it slides
        var h = Math.sin((c + drift) * 12.9898 + r * 78.233) * 43758.5453; h -= Math.floor(h);
        var bb = (b + (h - 0.5) * 0.13) * ease;
        if (bb <= 0.045) continue;
        var gi = (Math.pow(bb, 0.82) * RAMP.length) | 0; if (gi >= RAMP.length) gi = RAMP.length - 1;
        var ch = RAMP[gi]; if (ch === " ") continue;
        var wq = Math.round((230 + bb * 560) / 60) * 60;        // continuous weight, quantized so we re-set ctx.font rarely
        if (wq !== lastW) { ctx.font = wq + " " + FONT_PX + "px 'GeistMono', ui-monospace, monospace"; lastW = wq; }
        ctx.globalAlpha = Math.min(1, 0.4 + 0.6 * bb);
        ctx.fillStyle = tint(bb, sky);
        ctx.fillText(ch, c * CELLW, rowBase);
      }
    }
    ctx.globalAlpha = 1;
  }

  function resize() {
    W = cv.clientWidth; H = cv.clientHeight; cv.width = W; cv.height = H;
    ctx.font = "500 " + FONT_PX + 'px "GeistMono", ui-monospace, monospace'; ctx.textBaseline = "top";
    CELLW = Math.max(6, ctx.measureText("M").width);
    cols = Math.ceil(W / CELLW); rows = Math.ceil(H / LINE);
    fcv.width = cols; fcv.height = rows;
  }

  function render(now) {
    if (!running) return;
    requestAnimationFrame(render);
    if (now - prev < 42) return;            // ~24fps (the per-cell font set makes this the right budget)
    prev = now;
    if (!t0) t0 = now;
    if (!resolveStart) resolveStart = now;
    var res = Math.min(1, (now - resolveStart) / 1400);
    frame(now, res >= 1 ? 1 : 1 - Math.pow(1 - res, 3));   // resolve-from-nothing flourish on first paint
  }

  function init() {
    if (pre) pre.style.display = "none";
    reseed(); resize();
    if (reduce) { t0 = 0; frame(0.25 * DAY_MS, 1); return; }   // one bright static frame
    requestAnimationFrame(render);
  }

  addEventListener("resize", function () { resize(); if (reduce) init(); });
  document.addEventListener("visibilitychange", function () {
    running = !document.hidden; if (running && !reduce) { prev = 0; requestAnimationFrame(render); }
  });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(init); else init();

  // ponytail: dev self-check — the ramp is ASCII-only and ordered space→'@'
  console.assert(RAMP[0] === " " && RAMP[RAMP.length - 1] === "@" && !/[^\x20-\x7e]/.test(RAMP), "ridge ramp");
})();
