/* AstroNaradMuni v1.4.0: NaradVani is a still portrait. This file now only drives voice and mic.
 * The 3D/lip-sync page driver is not loaded; the page shows the static portrait image.
 *
 * Talk mode: the browser's own speech voice reads replies and the mic sends what the person says.
 * There is no longer any canvas animation, blinking or lip movement.
 */
(function () {
  "use strict";
  var CAL = {
    img: "/static/naradvani.jpg", w: 900, h: 1199,
    eyes: [{ cx: 388, cy: 463, rx: 41, ry: 14, src: [358, 431, 62, 12] }, { cx: 551, cy: 449, rx: 35, ry: 14, src: [522, 418, 58, 12] }],
    brows: [{ x: 335, y: 400, w: 100, h: 48 }, { x: 502, y: 388, w: 120, h: 48 }],
    mouth: { x: 392, y: 578, w: 200, h: 140, interiorTop: 620, interiorBot: 633, lipBot: 676, cx: 485, cy: 640 }
  };
  var L = { canvas: null, ctx: null, img: null, ready: false, mode: "chat", t0: 0, last: 0, rafOn: false,
    blink: 0, blinkAt: 0, blinkPhase: -1, blinkDouble: false,
    mouth: 0, mouthT: 0, brow: 0, browT: 0, nod: 0, tilt: 0, tiltT: 0,
    speaking: false, listening: false, track: null, pos: 0, cps: 13, sawBoundary: false, lastBoundary: 0, sig: "" };

  /* ---------------- text -> mouth openness ---------------- */
  var CLOSED = /[mbpMBPपफबभम]/, OPEN = /[aAअआा]/, MID = /[eEiIइईएऐिीेै]/, ROUND = /[oOuUउऊओऔुूोौ]/;
  function openness(ch) {
    if (CLOSED.test(ch)) return 0.02;
    if (OPEN.test(ch)) return 1;
    if (ROUND.test(ch)) return 0.72;
    if (MID.test(ch)) return 0.5;
    if (/\s/.test(ch)) return 0.08;
    if (/[.,;:!?।]/.test(ch)) return 0;
    return 0.28;
  }
  function visemeTrack(text) {
    var out = [], s = String(text || "");
    for (var i = 0; i < s.length; i++) out.push(openness(s.charAt(i)));
    return out;
  }
  function pauseAfter(ch) { return /[.!?।]/.test(ch) ? 5 : /[,;:]/.test(ch) ? 2.5 : 0; }

  /* ---------------- drawing ---------------- */
  function ease(x) { return x * x * (3 - 2 * x); }
  var tmp = document.createElement("canvas");
  function soften(tctx, w, h) {
    tctx.globalCompositeOperation = "destination-in";
    var g = tctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.22, w / 2, h / 2, Math.min(w, h) * 0.5);
    g.addColorStop(0, "rgba(0,0,0,1)"); g.addColorStop(1, "rgba(0,0,0,0)");
    tctx.fillStyle = g; tctx.fillRect(0, 0, w, h); tctx.globalCompositeOperation = "source-over";
  }
  function drawLid(ctx, e, p) {
    if (p < 0.02) return;
    var pad = 8, w = Math.ceil(2 * e.rx + 2 * pad), h = Math.ceil(2 * e.ry + 2 * pad), t, lid = 2 * e.ry * p + pad;
    tmp.width = w; tmp.height = h; t = tmp.getContext("2d");
    t.drawImage(L.img, e.src[0], e.src[1], e.src[2], e.src[3], 0, 0, w, lid + 2);          // skin from above the eye, drawn down over it
    t.globalCompositeOperation = "multiply"; t.fillStyle = "rgba(236,220,210,1)"; t.fillRect(0, 0, w, lid + 2); t.globalCompositeOperation = "source-over";
    var yl = lid, dy = yl - h / 2, half = Math.max(4, e.rx * Math.sqrt(Math.max(0.05, 1 - Math.pow(dy / (e.ry + pad), 2))));
    t.lineWidth = 2.2; t.lineCap = "round"; t.strokeStyle = "rgba(28,14,10," + (0.25 + 0.55 * p) + ")";
    t.beginPath(); t.moveTo(w / 2 - half, yl - 1); t.quadraticCurveTo(w / 2, yl + 3 * p, w / 2 + half, yl - 1); t.stroke();
    t.globalCompositeOperation = "destination-in"; t.save(); t.translate(w / 2, h / 2); t.scale(e.rx + pad, e.ry + pad);
    var g = t.createRadialGradient(0, 0, 0.7, 0, 0, 1); g.addColorStop(0, "rgba(0,0,0,1)"); g.addColorStop(1, "rgba(0,0,0,0)");
    t.fillStyle = g; t.fillRect(-1.1, -1.1, 2.2, 2.2); t.restore();
    ctx.drawImage(tmp, e.cx - w / 2, e.cy - h / 2);
  }
  function drawMouth(ctx, open) {
    var m = CAL.mouth, d = open * 12;
    if (d < 0.4) return;
    tmp.width = m.w; tmp.height = m.h; var t = tmp.getContext("2d");
    var it = m.interiorTop - m.y, ib = m.interiorBot - m.y, lb = m.lipBot - m.y;
    t.drawImage(L.img, m.x, m.y, m.w, it, 0, 0, m.w, it);                                   // above the opening: unchanged
    t.drawImage(L.img, m.x, m.y + it, m.w, ib - it, 0, it, m.w, ib - it + d);                // inside of the mouth: stretched
    t.drawImage(L.img, m.x, m.y + ib, m.w, lb - ib, 0, ib + d, m.w, lb - ib);                // lower lip and chin: moved down
    t.drawImage(L.img, m.x, m.y + lb, m.w, m.h - lb, 0, lb + d, m.w, m.h - lb - d);          // below: squeezed back to the photo
    soften(t, m.w, m.h);
    ctx.drawImage(tmp, m.x, m.y);
  }
  function drawBrows(ctx, b) {
    if (b < 0.05) return;
    CAL.brows.forEach(function (r) {
      tmp.width = r.w; tmp.height = r.h; var t = tmp.getContext("2d"), dy = 3.2 * b;
      t.drawImage(L.img, r.x, r.y, r.w, r.h, 0, -dy, r.w, r.h + dy);
      soften(t, r.w, r.h); ctx.drawImage(tmp, r.x, r.y);
    });
  }
  function draw() {
    var c = L.ctx; if (!c || !L.ready || L.three) return;
    var sig = [L.blink.toFixed(2), L.mouth.toFixed(2), L.brow.toFixed(2)].join("|");
    if (sig === L.sig) return; L.sig = sig;
    c.drawImage(L.img, 0, 0, CAL.w, CAL.h);
    drawBrows(c, L.brow);
    drawMouth(c, L.mouth);
    CAL.eyes.forEach(function (e) { drawLid(c, e, L.blink); });
  }

  /* ---------------- animation loop ---------------- */
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function frame(now) {
    L.rafOn = true; requestAnimationFrame(frame);
    var dt = Math.min(0.1, (now - (L.last || now)) / 1000); L.last = now; var t = now / 1000;
    if (!L.canvas || !L.canvas.isConnected || document.hidden) return;
    if (L.frozen) { draw(); return; }
    // blink: close 70ms, open 110ms; gaps 2.2-5.5 s, sometimes twice in a row; a little slower while listening
    if (L.blinkPhase < 0 && t >= L.blinkAt) { L.blinkPhase = 0; }
    if (L.blinkPhase >= 0) {
      L.blinkPhase += dt; var cl = 0.07, op = 0.11, p = L.blinkPhase;
      L.blink = p < cl ? ease(p / cl) : p < cl + op ? 1 - ease((p - cl) / op) : 0;
      if (p >= cl + op) { L.blinkPhase = -1; L.blink = 0; if (L.blinkDouble) { L.blinkDouble = false; L.blinkAt = t + 0.12; } else { L.blinkAt = t + rnd(2.2, 5.5) * (L.listening ? 1.3 : 1); L.blinkDouble = Math.random() < 0.18; } }
    }
    // speech: advance through the text, re-synchronised by word boundaries
    var talk = L.mode === "talk";
    if (L.speaking && L.track) {
      var i = Math.floor(L.pos), tr = L.track;
      if (i >= tr.length) { L.mouthT = 0; }
      else {
        var a = tr[i], b = tr[Math.min(tr.length - 1, i + 1)], mix = L.pos - i;
        L.mouthT = (a * (1 - mix) + b * mix) * (0.8 + 0.2 * Math.sin(t * 17));
        L.pos += dt * L.cps * (L.paused > 0 ? 0 : 1);
        if (L.sawBoundary && L.pos > L.lastBoundary + 14) L.pos = L.lastBoundary + 14;      // do not run ahead of the voice
        var ch = L.text.charAt(i);
        if (ch && pauseAfter(ch) && L.lastPauseIdx !== i) { L.lastPauseIdx = i; L.paused = pauseAfter(ch) / L.cps; }
        if (L.paused > 0) { L.paused -= dt; L.mouthT = 0; }
        if (ch === "?" ) L.browT = 1;
        else if (L.pos - L.sentenceAt > 40) { L.browT = 0.55; L.sentenceAt = L.pos; }
        else L.browT = Math.max(0, L.browT - dt * 0.8);
      }
    } else { L.mouthT = 0; L.browT = L.listening ? 0.35 : Math.max(0, L.browT - dt * 0.8); }
    var k = 1 - Math.pow(0.0005, dt);                    // frame-rate independent smoothing
    L.mouth += (L.mouthT - L.mouth) * Math.min(1, k * (L.mouthT > L.mouth ? 1.0 : 0.7));
    L.brow += (L.browT - L.brow) * Math.min(1, k * 0.5);
    L.tiltT = L.listening ? 2.2 : 0; L.tilt += (L.tiltT - L.tilt) * Math.min(1, k * 0.2);
    var breathe = Math.sin(t * 1.3) * 1.4, sway = talk ? Math.sin(t * 0.8) * 0.6 : Math.sin(t * 0.5) * 0.25;
    var nod = L.speaking ? Math.max(0, Math.sin(t * 3.1)) * 1.6 + L.mouth * 1.2 : 0;
    if (L.three) return;                                  // the 3D model is on stage; nothing more to draw here
    L.canvas.style.transform = "translateY(" + (breathe + nod).toFixed(2) + "px) rotate(" + (sway + L.tilt).toFixed(2) + "deg) scale(1.035)";
    draw();
  }
  L.paused = 0; L.sentenceAt = 0; L.text = ""; L.lastPauseIdx = -1;

  /* ---------------- voice out (browser speech synthesis) ---------------- */
  var VOICES = [];
  function loadVoices() { try { VOICES = window.speechSynthesis ? window.speechSynthesis.getVoices() : []; } catch (e) { VOICES = []; } }
  function pickVoice(lang) {
    if (!VOICES.length) loadVoices();
    var want = lang === "hi" ? "hi" : "en", male = /rishi|prabhat|hemant|ravi|madhur|male|david|daniel|google uk english male/i;
    var pool = VOICES.filter(function (v) { return v.lang && v.lang.toLowerCase().indexOf(want) === 0; });
    if (want === "en") { var inx = pool.filter(function (v) { return /en[-_]in/i.test(v.lang); }); if (inx.length) pool = inx; }
    return pool.filter(function (v) { return male.test(v.name); })[0] || pool[0] || null;
  }
  function clean(text) { return String(text || "").replace(/[*_`#>]+/g, "").replace(/\s+/g, " ").trim(); }
  function speak(text, lang, cb) {
    cb = cb || {};
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) { if (cb.onError) cb.onError("unsupported"); return false; }
    stop();
    var tx = clean(text); if (!tx) return false;
    var u = new SpeechSynthesisUtterance(tx), v = pickVoice(lang);
    if (v) u.voice = v; u.lang = v ? v.lang : (lang === "hi" ? "hi-IN" : "en-IN");
    u.rate = 0.93; u.pitch = 0.82; u.volume = 1;
    L.text = tx; L.track = visemeTrack(tx); L.pos = 0; L.lastBoundary = 0; L.sawBoundary = false; L.paused = 0; L.sentenceAt = 0; L.lastPauseIdx = -1;
    L.cps = 13.5 * u.rate;
    u.onstart = function () { L.speaking = true; if (cb.onStart) cb.onStart(); };
    u.onboundary = function (e) { if (typeof e.charIndex === "number") { L.sawBoundary = true; L.lastBoundary = e.charIndex; if (Math.abs(L.pos - e.charIndex) > 2) L.pos = e.charIndex; } };
    var done = function () { L.speaking = false; L.track = null; if (cb.onEnd) cb.onEnd(); };
    u.onend = done; u.onerror = done;
    L.speaking = true;
    window.speechSynthesis.speak(u);
    return true;
  }
  function stop() {
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* ignore */ }
    L.speaking = false; L.track = null;
  }

  /* ---------------- voice in (browser speech recognition) ---------------- */
  var REC = null;
  function micSupported() { return !!(window.SpeechRecognition || window.webkitSpeechRecognition); }
  function listen(lang, cb) {
    cb = cb || {};
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { if (cb.onError) cb.onError("unsupported"); return false; }
    stopListening(); stop();
    var r = new SR(); REC = r; r.lang = lang === "hi" ? "hi-IN" : "en-IN"; r.interimResults = true; r.maxAlternatives = 1; r.continuous = false;
    var finalText = "";
    r.onstart = function () { L.listening = true; if (cb.onStart) cb.onStart(); };
    r.onresult = function (e) {
      var s = ""; for (var i = e.resultIndex; i < e.results.length; i++) { s += e.results[i][0].transcript; if (e.results[i].isFinal) finalText += e.results[i][0].transcript; }
      if (cb.onText) cb.onText(finalText || s, !!finalText);
    };
    r.onerror = function (e) { L.listening = false; if (cb.onError) cb.onError(e.error || "error"); };
    r.onend = function () { L.listening = false; REC = null; if (cb.onEnd) cb.onEnd(finalText.trim()); };
    try { r.start(); } catch (e) { L.listening = false; if (cb.onError) cb.onError("start"); return false; }
    return true;
  }
  function stopListening() { try { if (REC) REC.stop(); } catch (e) { /* ignore */ } L.listening = false; }

  /* ---------------- mounting ---------------- */
  function mount(node, opts) {
    if (!node) return;
    opts = opts || {}; L.mode = opts.mode === "talk" ? "talk" : "chat";
    // Static portrait: the page renders a plain <img>. Keep the voice/mic API, do not start a draw loop.
    if (opts.still || node.tagName === "IMG") {
      L.still = true; L.canvas = null; L.ctx = null; L.three = false; L.ready = true;
      return;
    }
    L.still = false;
    L.canvas = node; node.width = CAL.w; node.height = CAL.h; L.ctx = node.getContext("2d"); L.sig = "";
    if (!L.img) {
      L.img = new Image(); L.img.onload = function () { L.ready = true; L.sig = ""; draw(); }; L.img.src = CAL.img;
    } else if (L.ready) { draw(); }
    if (!L.blinkAt) L.blinkAt = performance.now() / 1000 + rnd(1.2, 3);
    if (!L.rafOn) requestAnimationFrame(frame);
  }
  function setMode(m) { L.mode = m === "talk" ? "talk" : "chat"; if (L.mode === "chat") { stop(); stopListening(); } }
  if (window.speechSynthesis) { loadVoices(); try { window.speechSynthesis.onvoiceschanged = loadVoices; } catch (e) { /* ignore */ } }

  function preview(blink, mouth, brow) { L.frozen = true; L.blink = blink; L.mouth = mouth; L.brow = brow; L.sig = ""; draw(); }   // for calibration and tests
  function unfreeze() { L.frozen = false; }
  window.AMLive = { preview: preview, unfreeze: unfreeze, mount: mount, setMode: setMode, speak: speak, stop: stop, listen: listen, stopListening: stopListening, micSupported: micSupported,
    is3d: function () { return false; },                      // the page no longer mounts a 3D avatar
    speaking: function () { return L.speaking; }, listening: function () { return L.listening; }, visemeTrack: visemeTrack, openness: openness, CAL: CAL, _state: L };
})();
