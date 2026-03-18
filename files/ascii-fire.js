// Developed by runv (runawaydevil)
(function () {
  'use strict';

  var canvas = document.getElementById('ascii-fire-canvas');
  var wrap = canvas && canvas.closest('.ascii-fire-wrap');
  if (!wrap || !canvas) return;

  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var fireW = 80;
  var fireH = 60;
  var buffer = null;
  var palette = [];
  var rafId = null;
  var maxIntensity = 36;
  var frameCount = 0;

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function buildPalette() {
    var colors = [
      [0, 0, 0],
      [32, 0, 0],
      [64, 0, 0],
      [96, 0, 0],
      [128, 0, 0],
      [160, 0, 0],
      [192, 0, 0],
      [224, 0, 0],
      [255, 32, 0],
      [255, 64, 0],
      [255, 96, 0],
      [255, 128, 0],
      [255, 160, 0],
      [255, 192, 0],
      [255, 224, 0],
      [255, 255, 0],
      [255, 255, 128],
      [255, 248, 200]
    ];
    var n = 37;
    palette.length = 0;
    for (var i = 0; i < n; i++) {
      var t = i / (n - 1);
      var idx = t * (colors.length - 1);
      var lo = Math.floor(idx);
      var hi = Math.min(lo + 1, colors.length - 1);
      var f = idx - lo;
      var r = Math.round(colors[lo][0] * (1 - f) + colors[hi][0] * f);
      var g = Math.round(colors[lo][1] * (1 - f) + colors[hi][1] * f);
      var b = Math.round(colors[lo][2] * (1 - f) + colors[hi][2] * f);
      palette.push([r, g, b]);
    }
  }

  function initBuffer() {
    buffer = new Uint8Array(fireW * fireH);
    for (var i = 0; i < fireW * fireH; i++) buffer[i] = 0;
  }

  function spreadFire() {
    var rowSize = fireW;
    for (var y = 0; y < fireH - 1; y++) {
      var rowBelow = (y + 1) * rowSize;
      for (var x = 0; x < fireW; x++) {
        var center = buffer[rowBelow + x];
        var left = x > 0 ? buffer[rowBelow + (x - 1)] : center;
        var right = x < fireW - 1 ? buffer[rowBelow + (x + 1)] : center;
        var sum = center + left + right;
        var decay = Math.floor(Math.random() * 3);
        var v = Math.floor(sum / 3) - decay;
        if (v < 0) v = 0;
        buffer[y * rowSize + x] = v > maxIntensity ? maxIntensity : v;
      }
    }
    for (var x = 0; x < fireW; x++) {
      var bottomIdx = (fireH - 1) * rowSize + x;
      buffer[bottomIdx] = Math.random() > 0.3 ? maxIntensity : 20 + Math.floor(Math.random() * 10);
    }
  }

  function smoothStep(edge0, edge1, t) {
    var x = (t - edge0) / (edge1 - edge0);
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    return x * x * (3 - 2 * x);
  }

  function draw() {
    var w = canvas.width;
    var h = canvas.height;
    var scaleX = w / fireW;
    var scaleY = h / fireH;
    var imgData = ctx.createImageData(w, h);
    var data = imgData.data;
    var edgeFrac = 0.18;

    for (var sy = 0; sy < h; sy++) {
      var fy = Math.floor(sy / scaleY);
      if (fy >= fireH) fy = fireH - 1;
      var ny = 1 - sy / h;
      var bottomMask = smoothStep(0, edgeFrac, ny);
      for (var sx = 0; sx < w; sx++) {
        var fx = Math.floor(sx / scaleX);
        if (fx >= fireW) fx = fireW - 1;
        var nx = sx / w;
        var sideMask = smoothStep(0, edgeFrac, nx) * smoothStep(1, 1 - edgeFrac, nx);
        var mask = bottomMask * sideMask;
        var v = buffer[fy * fireW + fx];
        var c = palette[v] || palette[0];
        var boost = 1.35;
        var i = (sy * w + sx) * 4;
        data[i] = Math.min(255, Math.round(c[0] * mask * boost));
        data[i + 1] = Math.min(255, Math.round(c[1] * mask * boost));
        data[i + 2] = Math.min(255, Math.round(c[2] * mask * boost));
        data[i + 3] = 255;
      }
    }
    ctx.putImageData(imgData, 0, 0);
  }

  function resize() {
    var rect = wrap.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    var logicalH = 64;
    var aspect = (canvas.width / dpr) / Math.max(1, canvas.height / dpr);
    var newFireH = Math.max(24, Math.min(128, logicalH));
    var newFireW = Math.max(32, Math.min(256, Math.round(newFireH * aspect)));
    if (newFireW !== fireW || newFireH !== fireH) {
      fireW = newFireW;
      fireH = newFireH;
      if (buffer) initBuffer();
    }
  }

  function tick() {
    if (prefersReducedMotion()) {
      rafId = requestAnimationFrame(tick);
      return;
    }
    frameCount++;
    if (frameCount % 3 === 0) {
      spreadFire();
      draw();
    }
    rafId = requestAnimationFrame(tick);
  }

  function start() {
    if (prefersReducedMotion()) return;
    buildPalette();
    initBuffer();
    resize();
    tick();
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
  }

  resize();
  if (!prefersReducedMotion()) {
    buildPalette();
    initBuffer();
    tick();
  }

  window.addEventListener('resize', function () {
    resize();
  });

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  reduceMotion.addEventListener('change', function () {
    if (reduceMotion.matches) stop();
    else start();
  });
})();
