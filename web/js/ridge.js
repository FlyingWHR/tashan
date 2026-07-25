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
  // Calm knobs — turn these, not the code, when the art reads busy or too faint.
  // Ramp is deliberately SHORT and letterform-free: 'a e z n x Q B' read as text noise, not as tone.
  var RAMP = " ..--=+*#";                       // light → heavy (ASCII-only: no missing-glyph tofu)
  var CUT = 0.15;                                 // brightness below this draws NOTHING — THE sparseness knob
  var GAMMA = 1.05;                               // >1 pushes mid-tones toward blank (calm), <1 fills in
  // Keep leading spaces in RAMP to ONE: more, and the ramp starts blanking before CUT does, so turning CUT
  // stops doing anything and the art silently goes empty.
  var SKY = 0.40;                                 // upper band kept clear (the headline lives there)
  var DAY_MS = 600000;                            // a full day↔night in ~10 min (was 4 — the light
                                                  // sweep is what pops glyphs; slower sweep = calmer)

  var W = 0, H = 0, cols = 0, rows = 0, running = true, prev = 0, t0 = 0, resolveStart = 0, dayStart = 0, curWind = 0.5;
  var layers = [], mist = [], dith = null, lastB = null, lastGi = null;
  var HYST = 0.045;  // a cell keeps its glyph until brightness moves this much. Too high and the art
                     // freezes: nothing in the scene changes enough to ever cross it.
  var fcv = document.createElement("canvas"), fctx = fcv.getContext("2d", { willReadFrequently: true });

  // ---------- day/night: key-light tint + ambient + sun/moon phase (sky itself isn't drawn) ----------
  // The whole cycle stays in the jade family — the art should read as the brand accent at any hour, not
  // amber at 3pm. Variety comes from value/saturation across the day, not from leaving the hue.
  var SKYK = [
    { p: 0.00, lit: [118, 214, 162], amb: 0.82, orb: 1 },   // dawn (soft jade)
    { p: 0.25, lit: [92, 240, 192],  amb: 1.00, orb: 1 },   // noon (jade-bright, = --jade-bright)
    { p: 0.50, lit: [52, 224, 160],  amb: 0.86, orb: 1 },   // dusk (--jade proper)
    { p: 0.75, lit: [64, 156, 146],  amb: 0.68, orb: 0 },   // night (dim teal-jade)
    { p: 1.00, lit: [118, 214, 162], amb: 0.82, orb: 1 }
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
      { crest: makeHill(s + 3, 0.9, 0.56, 0.085), lift: 0.08, val: 0.34 },   // 远山
      { crest: makeHill(s + 7, 1.1, 0.69, 0.105), lift: 0.13, val: 0.60 },   // 中景
      { crest: makeHill(s + 1, 1.3, 0.82, 0.130), lift: 0.18, val: 1.00 }    // 近山
    ];
    // drifting mist wisps (soft additive blobs) — the living 云雾 of the scene
    mist = [];
    // more, SMALLER wisps: a big soft blob brightens a whole region at once (a flash); small ones read as
    // something travelling across the slope.
    for (var i = 0; i < 7; i++) mist.push({ x: Math.random(), y: 0.74 + Math.random() * 0.16, r: 0.045 + Math.random() * 0.06, ph: Math.random() * 6.28, sp: 0.5 + Math.random() * 0.9 });
    var hr = new Date().getHours() + new Date().getMinutes() / 60;    // grounded in the visitor's real time-of-day
    dayStart = ((hr - 6 + 24) % 24) / 24;
  }
  function windAt(now) {   // slow, organic breeze (drives the mist drift)
    // All terms are slow on purpose. The old 0.00025 term gusted on a ~25s cycle, which accelerated the
    // mist hard enough to read as a pulse rather than a breeze.
    var w = 0.5 + 0.30 * Math.sin(now * 0.00003) + 0.17 * Math.sin(now * 0.00007 + 1.3) + 0.09 * Math.sin(now * 0.00011 + 2.1);
    return w < 0.05 ? 0.05 : w;
  }

  // ---------- paint the smooth grayscale FIELD, return its pixels ----------
  function paintField(now, sky, dp, wind) {
    var fw = cols, fh = rows;
    fctx.globalCompositeOperation = "source-over";
    fctx.fillStyle = "#000"; fctx.fillRect(0, 0, fw, fh);
    // mountains far→near (near paints over far = clean 前后 occlusion). Painted PER COLUMN so EACH column's
    // crest is the bright lit edge — a clear ridgeline — fading down to a dark valley base (contrast = shape).
    var band = Math.max(2.2, fh * 0.11);   // crest-band thickness in ROWS — the density knob, independent of height
    for (var li = 0; li < layers.length; li++) {
      var L = layers[li], peak = Math.min(1, 0.62 + 0.38 * L.val);
      // always-on life: a wave TRAVELLING along each ridge, not a uniform bob. Uniform motion lifts every
      // cell at once, so they all cross the glyph threshold together and the layer flashes; a spatial phase
      // makes the change arrive column by column — vegetation sweeping, not a strobe.
      // Tuning history — the usable band is narrow, so change these by ~2x, not 10x:
      //   0.010 amp x 0.000035 rate = frozen (a cell never crosses HYST)
      //   0.030 amp x 0.00016  rate = too much
      //   0.020 amp x 0.00008  rate = here. Crest travels ~1 row / 19s.
      // Amplitude is safe at this level BECAUSE the phase is spatial — the stagger is what keeps it a
      // sweep rather than a flash, not the smallness.
      var ph = now * 0.00008 + li * 2.1;
      for (var c = 0; c < fw; c++) {
        var breathe = 0.020 * Math.sin(ph - c * 0.05);
        var y0 = (L.crest(c) - L.lift * env(c) + breathe) * fh;
        if (y0 >= fh - 0.5) continue;
        // Gradient ends a FIXED number of rows below the crest, not at the canvas bottom — so raising a
        // ridge moves it up without also thickening it. (Spanning to fh coupled height to density: a higher
        // crest stretched the falloff and inked far more rows.) Past the last stop the gradient clamps to
        // 0.005, i.e. under CUT, so the body below stays empty.
        var g = fctx.createLinearGradient(0, y0, 0, y0 + band);
        g.addColorStop(0, "rgba(255,255,255," + peak.toFixed(3) + ")");
        g.addColorStop(0.32, "rgba(255,255,255," + (peak * 0.30).toFixed(3) + ")");
        g.addColorStop(0.70, "rgba(255,255,255," + (peak * 0.10).toFixed(3) + ")");
        g.addColorStop(1, "rgba(255,255,255,0.005)");
        fctx.fillStyle = g; fctx.fillRect(c, y0, 1.02, fh - y0);
      }
    }
    // key light: MULTIPLY, not add. Additive light lifts the empty sky/valley above CUT too, which inks the
    // whole band with haze — the "busy" look. Multiplying shapes what's already there and keeps black black.
    fctx.globalCompositeOperation = "multiply";
    var prog = dp < 0.5 ? dp / 0.5 : (dp - 0.5) / 0.5;
    var ox = prog * fw, oy = fh * (0.30 - 0.18 * Math.sin(prog * Math.PI));
    var lg = fctx.createRadialGradient(ox, oy, 0, ox, oy, fw * 0.9);
    var dim = Math.round(255 * (0.40 + 0.42 * sky.amb));    // unlit side falls off; ambient sets how far
    lg.addColorStop(0, "#ffffff"); lg.addColorStop(1, "rgb(" + dim + "," + dim + "," + dim + ")");
    fctx.fillStyle = lg; fctx.fillRect(0, 0, fw, fh);
    // mist: soft radial wisps drifting on the wind. Additive, but kept UNDER CUT on its own — so mist only
    // becomes visible where it drifts across a slope, never as free-floating fog in empty sky.
    fctx.globalCompositeOperation = "lighter";
    for (var i = 0; i < mist.length; i++) {
      var m = mist[i];
      var mx = (((m.x + now * 0.0000030 * m.sp * (0.5 + wind)) % 1.16) - 0.08) * fw;
      var my = (m.y + 0.014 * Math.sin(now * 0.00003 * m.sp + m.ph)) * fh;
      var mr = m.r * fw;
      var mg = fctx.createRadialGradient(mx, my, 0, mx, my, mr);
      mg.addColorStop(0, "rgba(255,255,255,0.10)"); mg.addColorStop(0.6, "rgba(255,255,255,0.03)"); mg.addColorStop(1, "rgba(255,255,255,0)");
      fctx.fillStyle = mg; fctx.fillRect(mx - mr, my - mr, mr * 2, mr * 2);
    }
    fctx.globalCompositeOperation = "source-over";
    return fctx.getImageData(0, 0, fw, fh).data;
  }

  // stone (dim) → time-of-day key light (bright), by brightness
  // Ramp to the lit color across the range cells ACTUALLY occupy (CUT..~0.6). The old divisor of 0.88 put a
  // typical cell at t≈0.2 — still stone grey — which is why the field read brown instead of jade.
  function tint(b, sky) {
    var base = [56, 76, 68], lit = sky.lit, t = Math.max(0, Math.min(1, (b - CUT) / 0.42));
    return "rgb(" + Math.round(base[0] + (lit[0] - base[0]) * t) + "," + Math.round(base[1] + (lit[1] - base[1]) * t) + "," + Math.round(base[2] + (lit[2] - base[2]) * t) + ")";
  }

  function frame(now, ease) {
    var dp = ((now - t0) / DAY_MS + dayStart) % 1;
    var sky = daySample(dp);
    var wind = curWind = windAt(now);
    ctx.clearRect(0, 0, W, H);
    var data = paintField(now, sky, dp, wind);
    ctx.textBaseline = "top";
    var lastW = -1;
    for (var r = Math.floor(rows * SKY) - 2; r < rows; r++) {   // skip the clear upper band entirely
      if (r < 0) r = 0;
      var rowBase = r * LINE, ri = r * cols;
      for (var c = 0; c < cols; c++) {
        var b = data[(ri + c) * 4] / 255;                       // grayscale → brightness
        if (b <= CUT) continue;
        var k = ri + c, bb = b + dith[k];
        if (bb <= CUT) continue;
        // Reveal fades ALPHA, never brightness. Scaling brightness by the ease meant every cell sat under
        // CUT until the ease was nearly done, so the art popped in instead of resolving. Sweeps left→right.
        var rv = ease >= 1 ? 1 : ease * 1.45 - (c / cols) * 0.45;
        if (rv <= 0) continue; else if (rv > 1) rv = 1;
        // hysteresis: hold the glyph unless brightness really moved. Without this, mist drifting a fraction
        // of a cell tips a whole run of cells across a ramp step at once and the ridge twinkles.
        // ...and jitter the threshold per cell, or every cell at a similar brightness snaps on the SAME
        // frame — that synchronized snap is what reads as the mountain flashing rather than a sweep.
        var gi, hy = HYST + dith[k] * 1.6;
        if (lastB[k] >= 0 && Math.abs(bb - lastB[k]) < hy) {
          gi = lastGi[k];
        } else {
          gi = (Math.pow(bb, GAMMA) * RAMP.length) | 0; if (gi >= RAMP.length) gi = RAMP.length - 1;
          lastB[k] = bb; lastGi[k] = gi;
        }
        var ch = RAMP[gi]; if (ch === " ") continue;
        var wq = 220 + gi * 60;                                 // weight follows the HELD glyph, so it can't pop on its own
        if (wq !== lastW) { ctx.font = wq + " " + FONT_PX + "px 'GeistMono', ui-monospace, monospace"; lastW = wq; }
        ctx.globalAlpha = Math.min(1, 0.15 + 0.60 * bb) * rv;   // dim cells actually recede instead of floor-40%
        ctx.fillStyle = tint(bb, sky);
        ctx.fillText(ch, c * CELLW, rowBase);
      }
    }
    ctx.globalAlpha = 1;
  }

  // Per-cell dither, computed ONCE per size. It breaks the smooth iso-brightness rows into organic texture.
  // It must be STATIC in time: the hash is chaotic, so advancing it even slightly re-randomizes every cell
  // each frame and the whole field boils like TV static. That flicker — not the density — is what reads as
  // busy and cheap. With it frozen, the only motion left is the real scene: slow mist, slower light.
  function makeDither() {
    dith = new Float32Array(cols * rows);
    lastB = new Float32Array(cols * rows).fill(-1); lastGi = new Int8Array(cols * rows);
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var h = Math.sin(c * 12.9898 + r * 78.233) * 43758.5453;
        dith[r * cols + c] = (h - Math.floor(h) - 0.5) * 0.05;
      }
    }
  }

  function resize() {
    W = cv.clientWidth; H = cv.clientHeight; cv.width = W; cv.height = H;
    ctx.font = "500 " + FONT_PX + 'px "GeistMono", ui-monospace, monospace'; ctx.textBaseline = "top";
    CELLW = Math.max(6, ctx.measureText("M").width);
    cols = Math.ceil(W / CELLW); rows = Math.ceil(H / LINE);
    fcv.width = cols; fcv.height = rows;
    makeDither();
  }

  function render(now) {
    if (!running) return;
    requestAnimationFrame(render);
    if (now - prev < 55) return;            // ~18fps — enough for the sweep to read as continuous motion
    prev = now;
    if (!t0) t0 = now;
    if (!resolveStart) resolveStart = now;
    var res = Math.min(1, (now - resolveStart) / 1900);
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

  // ponytail: dev self-check — ramp is ASCII-only, starts blank, and stays letterform-free (no alphabet soup)
  console.assert(RAMP[0] === " " && !/[^\x20-\x7e]/.test(RAMP) && !/[a-zA-Z]/.test(RAMP), "ridge ramp");
})();
