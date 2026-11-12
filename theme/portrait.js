/* حركة الرسم الشخصي
   data-motion="ink"      : يُرسم بالقلم مرة واحدة في الجلسة (الواجهة)
   data-motion="letters"  : وجه من حروف التدوينات، يتفرّق تحت الفأرة أو الإصبع (صفحة عني)
   الصورة الأصلية تبقى في الصفحة؛ اللوحة تُضاف فوقها فقط إن كان المتصفح قادرًا ولم يطلب القارئ تقليل الحركة. */
(function () {
  var boxes = [].slice.call(document.querySelectorAll("[data-motion]"));
  if (!boxes.length || !window.requestAnimationFrame) return;
  if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var GOLD = "#C9971C", BURGUNDY = "#6D1F2C";
  var clamp = function (v, a, b) { a = a || 0; b = b === undefined ? 1 : b; return Math.max(a, Math.min(b, v)); };
  var inOut = function (t) { return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
  function rng(seed) { return function () { return (seed = (seed * 16807) % 2147483647) / 2147483647; }; }
  function ss(key, val) { try { if (val === undefined) return sessionStorage.getItem(key); sessionStorage.setItem(key, val); } catch (e) { return null; } }

  function ready(img) {
    if (img.complete && img.naturalWidth) return Promise.resolve();
    return new Promise(function (res, rej) { img.addEventListener("load", res, { once: true }); img.addEventListener("error", rej, { once: true }); });
  }
  function whenVisible(el, fn) {
    if (!("IntersectionObserver" in window)) return fn();
    var o = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { o.disconnect(); fn(); } }, { threshold: .35 });
    o.observe(el);
  }

  /* اللوحة الكاملة: القرص الذهبي + الرسم، بنفس نسب .sketchp::before */
  function composeFull(img, W, H) {
    var c = document.createElement("canvas"); c.width = W; c.height = H;
    var x = c.getContext("2d"), d = W * .74;
    x.globalAlpha = .2; x.fillStyle = GOLD;
    x.beginPath(); x.arc(W * .13 + d / 2, H * .04 + d / 2, d / 2, 0, Math.PI * 2); x.fill();
    x.globalAlpha = 1; x.drawImage(img, 0, 0, W, H);
    return c;
  }

  function mount(box, img) {
    var cv = document.createElement("canvas");
    cv.setAttribute("aria-hidden", "true");
    var dpr = Math.min(2, window.devicePixelRatio || 1), b = img.getBoundingClientRect();
    cv.width = Math.round(b.width * dpr); cv.height = Math.round(b.height * dpr);
    box.appendChild(cv); box.classList.add("is-motion");
    return { cv: cv, ctx: cv.getContext("2d"), W: cv.width, H: cv.height, dpr: dpr };
  }
  function unmount(box, cv) { box.classList.remove("is-motion"); if (cv && cv.parentNode) cv.parentNode.removeChild(cv); }

  /* ——— يُرسم بالقلم ——— */
  function ink(box, img) {
    if (ss("ink-seen")) return;           // مرة واحدة في الجلسة
    var m0 = mount(box, img), ctx = m0.ctx, W = m0.W, H = m0.H, full = composeFull(img, W, H);
    var mask = document.createElement("canvas"); mask.width = W; mask.height = H;
    var m = mask.getContext("2d"), r = rng(5), pts = [], lw = W * .085, step = lw * .62, dir = 1, k = W / 588;
    for (var y = H * .02; y < H * 1.02; y += step) {
      var x0 = dir > 0 ? W * .1 : W * .9, x1 = dir > 0 ? W * .9 : W * .1;
      for (var i = 0; i <= 10; i++) { var u = i / 10; pts.push([x0 + (x1 - x0) * u + (r() - .5) * 6 * k, y + u * step * .8 + (r() - .5) * 4 * k]); }
      dir *= -1;
    }
    var lens = [0];
    for (i = 1; i < pts.length; i++) lens[i] = lens[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    var L = lens[lens.length - 1], d = W * .74, ccx = W * .13 + d / 2, ccy = H * .04 + d / 2;
    var delay = 350, tCircle = 700, tDraw = 2100, total = delay + tCircle + tDraw + 150;

    function frame(t) {
      t -= delay; ctx.clearRect(0, 0, W, H); if (t < 0) return;
      var kc = inOut(clamp(t / tCircle));
      ctx.save(); ctx.strokeStyle = GOLD; ctx.lineWidth = 2 * m0.dpr; ctx.globalAlpha = .7 * (1 - clamp((t - tCircle) / 600));
      ctx.beginPath(); ctx.arc(ccx, ccy, d / 2, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * kc); ctx.stroke(); ctx.restore();
      var kd = inOut(clamp((t - tCircle * .8) / tDraw)), target = kd * L, tip = pts[0];
      m.clearRect(0, 0, W, H); m.lineCap = m.lineJoin = "round"; m.lineWidth = lw; m.strokeStyle = "#000";
      m.beginPath(); m.moveTo(pts[0][0], pts[0][1]);
      for (var i = 1; i < pts.length; i++) {
        if (lens[i] <= target) { m.lineTo(pts[i][0], pts[i][1]); tip = pts[i]; continue; }
        var u = (target - lens[i - 1]) / (lens[i] - lens[i - 1]);
        tip = [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u];
        m.lineTo(tip[0], tip[1]); break;
      }
      if (kd > 0) m.stroke();
      if (kd >= 1) m.fillRect(0, 0, W, H);
      m.globalCompositeOperation = "source-in"; m.drawImage(full, 0, 0); m.globalCompositeOperation = "source-over";
      ctx.drawImage(mask, 0, 0);
      if (kd > 0 && kd < 1) {               // سنّ القلم
        ctx.save(); ctx.translate(tip[0], tip[1]); ctx.rotate(-.7); ctx.scale(k * 1.15, k * 1.15);
        ctx.fillStyle = BURGUNDY; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(5, -16); ctx.lineTo(-5, -16); ctx.closePath(); ctx.fill();
        ctx.fillRect(-5, -60, 10, 44); ctx.fillStyle = GOLD; ctx.fillRect(-5, -64, 10, 5); ctx.restore();
      }
    }
    whenVisible(box, function () {
      var t0 = performance.now();
      (function tick(now) {
        var t = now - t0; frame(t);
        if (t < total) requestAnimationFrame(tick); else { ss("ink-seen", "1"); unmount(box, m0.cv); }
      })(t0);
    });
  }

  /* ——— وجه من حروف ——— */
  function letters(box, img) {
    var TEXT = (box.getAttribute("data-letters") || "كاتب ثلاثيني").replace(/[\sـ«»؟،.:!]/g, "");
    var state = null, raf = 0, pointer = null;

    function build(animate) {
      if (state) { cancelAnimationFrame(raf); raf = 0; unmount(box, state.cv); }
      var m0 = mount(box, img), ctx = m0.ctx, W = m0.W, H = m0.H, full = composeFull(img, W, H), data;
      try { data = full.getContext("2d").getImageData(0, 0, W, H).data; }
      catch (e) { unmount(box, m0.cv); state = null; return; }   // مثلًا عند فتح الملفات محليًا
      var g = Math.max(W / 44, 6.5 * m0.dpr), r = rng(3), parts = [], ti = 0;
      var darkAt = function (x, y) { var i = ((y | 0) * W + (x | 0)) * 4, a = data[i + 3] / 255; return a * (1 - (data[i] * .3 + data[i + 1] * .59 + data[i + 2] * .11) / 255); };
      for (var y = g / 2; y < H; y += g) for (var x = g / 2; x < W; x += g) {
        var s = 0, n = 0;
        for (var yy = -g / 2; yy < g / 2; yy += g / 5) for (var xx = -g / 2; xx < g / 2; xx += g / 5) {
          var X = x + xx, Y = y + yy; if (X >= 0 && Y >= 0 && X < W && Y < H) { s += darkAt(X, Y); n++; }
        }
        var dark = s / n; if (dark < .2) continue;
        var sx = r() * W, sy = r() * H;
        parts.push({ hx: x, hy: y, sx: sx, sy: sy, x: animate ? sx : x, y: animate ? sy : y, vx: 0, vy: 0, r: 0, rot: (r() - .5) * 3,
                     ch: TEXT[ti++ % TEXT.length], a: clamp((dark - .15) * 2.4, .3, 1), size: g * (.85 + dark * .8), d: r() * 500 });
      }
      state = { cv: m0.cv, ctx: ctx, W: W, H: H, full: full, parts: parts, live: !animate, cssW: img.getBoundingClientRect().width };
      bind(m0.cv);
      if (!animate) draw(null, .5);
      return state;
    }
    function draw(t, imgA) {
      var S = state, ctx = S.ctx;
      ctx.clearRect(0, 0, S.W, S.H);
      if (imgA > 0) { ctx.globalAlpha = imgA; ctx.drawImage(S.full, 0, 0); }
      ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = BURGUNDY;
      for (var i = 0; i < S.parts.length; i++) {
        var p = S.parts[i];
        ctx.globalAlpha = p.a * (t === null ? 1 : clamp((t - p.d * .3) / 300));
        ctx.font = "700 " + p.size.toFixed(1) + "px 'Thmanyah Serif Display', serif";
        ctx.save(); ctx.translate(p.x, p.y); if (p.r) ctx.rotate(p.r); ctx.fillText(p.ch, 0, 0); ctx.restore();
      }
      ctx.globalAlpha = 1;
    }
    function physics() {
      var S = state, moving = false, R = S.W * .22;
      for (var i = 0; i < S.parts.length; i++) {
        var p = S.parts[i], ax = (p.hx - p.x) * .06, ay = (p.hy - p.y) * .06;
        if (pointer) {
          var dx = p.x - pointer.x, dy = p.y - pointer.y, d2 = dx * dx + dy * dy;
          if (d2 < R * R) { var d = Math.sqrt(d2) || 1, f = (1 - d / R) * 16 * (S.W / 588); ax += dx / d * f; ay += dy / d * f; }
        }
        p.vx = (p.vx + ax) * .82; p.vy = (p.vy + ay) * .82; p.x += p.vx; p.y += p.vy; p.r = p.r * .9 + p.vx * .02;
        if (Math.abs(p.vx) + Math.abs(p.vy) > .05 || Math.abs(p.hx - p.x) > .3) moving = true;
      }
      draw(null, .5);
      raf = (moving || pointer) ? requestAnimationFrame(physics) : 0;
    }
    function bind(cv) {
      var pos = function (e) { var b = cv.getBoundingClientRect(); return { x: (e.clientX - b.left) / b.width * state.W, y: (e.clientY - b.top) / b.height * state.H }; };
      var move = function (e) { if (!state || !state.live) return; pointer = pos(e); if (!raf) raf = requestAnimationFrame(physics); };
      cv.addEventListener("pointermove", move);
      cv.addEventListener("pointerdown", move);
      ["pointerleave", "pointerup", "pointercancel"].forEach(function (ev) { cv.addEventListener(ev, function () { pointer = null; }); });
    }
    function form() {
      var S = state, dur = 1700, total = dur + 900, t0 = performance.now();
      (function tick(now) {
        var t = now - t0;
        for (var i = 0; i < S.parts.length; i++) {
          var p = S.parts[i], k = inOut(clamp((t - p.d) / (dur - 500)));
          p.x = p.sx + (p.hx - p.sx) * k; p.y = p.sy + (p.hy - p.sy) * k; p.r = p.rot * (1 - k);
        }
        draw(t, .5 * clamp((t - dur + 200) / 700));
        if (t < total) raf = requestAnimationFrame(tick); else { raf = 0; S.live = true; draw(null, .5); }
      })(t0);
    }

    var fontReady = document.fonts && document.fonts.load ? document.fonts.load("700 20px 'Thmanyah Serif Display'").catch(function () {}) : Promise.resolve();
    fontReady.then(function () {
      if (build(true)) whenVisible(box, form);
    });
    var rt = 0;
    window.addEventListener("resize", function () {
      clearTimeout(rt);
      rt = setTimeout(function () {
        if (state && Math.abs(img.getBoundingClientRect().width - state.cssW) > 2) build(false);
      }, 200);
    });
  }

  var MODES = { ink: ink, letters: letters };
  boxes.forEach(function (box) {
    var img = box.querySelector("img"), fn = MODES[box.getAttribute("data-motion")];
    if (img && fn) ready(img).then(function () { fn(box, img); }).catch(function () {});
  });
})();
