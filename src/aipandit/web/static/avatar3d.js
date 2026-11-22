/* AstroNaradMuni v1.3.0: NaradVani in 3D.
 *
 * A classic script on purpose: it has no static imports, so the pure driver logic (text -> mouth shapes, blinks, brows,
 * eye saccades, head and breathing motion) can be tested in Node, and the page still works if three.js is missing.
 * three.js, GLTFLoader and the meshopt decoder are imported lazily, by absolute path, from /static/vendor/ (strict CSP:
 * script-src 'self', no inline scripts, no import maps). If anything fails (no WebGL, no GLB, slow device, lost context)
 * mount() resolves false and the 2D living portrait in live.js stays in place.
 *
 * live.js stays the brain for speech: it advances the text position and re-syncs it on every word boundary. This file
 * only reads AMLive._state (speaking, text, pos, paused, listening, mode) and moves the model. Public API of AMLive is
 * unchanged.
 *
 * The model needs the 52 ARKit shape keys and the 15 Oculus visemes (viseme_sil is an empty key). Mouth shapes already
 * contain their jaw movement, so no extra jawOpen is added. Bones are found by name (Head, Neck, Spine2, LeftEye,
 * RightEye, with or without a "mixamorig:" prefix) and rotated about WORLD axes, so bone roll in the export does not matter.
 * Tuning knobs live in CFG.
 */
(function (root) {
  "use strict";
  var VENDOR = "/static/vendor/";
  var MODELS = { naradvani: VENDOR + "naradvani.glb", mp: VENDOR + "naradvani_mp.glb" };   // ?model=mp is for private local testing only
  var CFG = { fov: 24, margin: 0.92, shiftY: 0.0, faceYaw: 0, exposure: 1.2, tone: "neutral", light: 1.8, cornea: 0.18, eyeTint: 0.8, pose: null, maxDpr: 2, slowMs: 42 };   // pose: {x,y,z,ex,ey} forces head/eye angles (verification only)   // tone: "aces" | "neutral" | "agx"
  var VIS = ["aa", "E", "I", "O", "U", "PP", "FF", "TH", "DD", "kk", "CH", "SS", "nn", "RR"];
  var REQUIRED = ["eyeBlinkLeft", "eyeBlinkRight", "browInnerUp", "jawOpen", "mouthSmileLeft", "mouthSmileRight"].concat(VIS.map(function (v) { return "viseme_" + v; }));

  /* ---------------- text -> viseme (pure) ---------------- */
  var DEV = {};
  function put(chars, v, w) { for (var i = 0; i < chars.length; i++) DEV[chars.charAt(i)] = v ? { v: v, w: w } : null; }
  put("टठडढतथदध", "DD", 0.65); put("अआा", "aa", 1); put("इईिी", "I", 0.75); put("एऐेै", "E", 0.8); put("उऊुू", "U", 0.85); put("ओऔोौ", "O", 0.9);
  put("कखगघङ", "kk", 0.7); put("चछजझञ", "CH", 0.7); put("नणं", "nn", 0.55); put("लळ", "nn", 0.55); put("पफबभम", "PP", 1);
  put("य", "I", 0.5); put("व", "U", 0.6); put("रऱ", "RR", 0.6); put("शषस", "SS", 0.6); put("ह", "aa", 0.25); put("़्", null, 0);
  var LAT = { a: ["aa", 1], e: ["E", 0.8], i: ["I", 0.75], o: ["O", 0.9], u: ["U", 0.85], y: ["I", 0.5], w: ["U", 0.6],
    m: ["PP", 1], b: ["PP", 1], p: ["PP", 1], f: ["FF", 0.9], v: ["FF", 0.9], t: ["DD", 0.65], d: ["DD", 0.65], n: ["nn", 0.55], l: ["nn", 0.55],
    s: ["SS", 0.6], z: ["SS", 0.6], k: ["kk", 0.7], g: ["kk", 0.7], q: ["kk", 0.7], x: ["kk", 0.7], c: ["kk", 0.7], j: ["CH", 0.7], r: ["RR", 0.6], h: ["aa", 0.25] };
  var DIG2 = { c: ["CH", 0.5], s: ["CH", 0.5], t: ["TH", 0.6], p: ["FF", 0.6], g: ["kk", 0.5], k: ["kk", 0.5], d: ["DD", 0.5], b: ["PP", 0.8] };   // second letter of ch, sh, th, ph, gh, kh, dh, bh
  function visemeFor(text, i) {
    var s = String(text || ""), ch = s.charAt(i);
    if (!ch) return null;
    var low = ch.toLowerCase(), nx = s.charAt(i + 1).toLowerCase(), pv = i > 0 ? s.charAt(i - 1).toLowerCase() : "", r;
    if (low === "h" && pv && DIG2[pv]) return { v: DIG2[pv][0], w: DIG2[pv][1] };
    if (low === "t" && nx === "h") return { v: "TH", w: 0.6 };
    if ((low === "c" || low === "s") && nx === "h") return { v: "CH", w: 0.7 };
    if (low === "p" && nx === "h") return { v: "FF", w: 0.8 };
    r = LAT[low]; if (r) return { v: r[0], w: r[1] };
    if (Object.prototype.hasOwnProperty.call(DEV, ch)) return DEV[ch];
    if (/[0-9]/.test(ch)) return { v: "DD", w: 0.5 };
    return null;                                                                      // spaces and punctuation: mouth rests (viseme_sil)
  }
  function targets(text, pos, paused) {
    var t = {}; if (paused) return t;
    var i = Math.floor(pos), f = pos - i, a = visemeFor(text, i), b = visemeFor(text, i + 1);
    if (a) t[a.v] = Math.min(1, (t[a.v] || 0) + a.w * (1 - 0.45 * f));
    if (b) t[b.v] = Math.min(1, (t[b.v] || 0) + b.w * 0.45 * f);                      // start opening for the next sound a little early
    return t;
  }

  /* ---------------- the driver (pure: numbers in, numbers out) ---------------- */
  function ease(x) { return x * x * (3 - 2 * x); }
  function createDriver(rand) {
    rand = rand || Math.random;
    function rnd(a, b) { return a + rand() * (b - a); }
    var D = { vis: {}, blink: 0, blinkPhase: -1, blinkAt: rnd(1.2, 3), blinkDouble: false, brow: 0, browT: 0, sentenceAt: 0,
      eyeX: 0, eyeY: 0, eyeTX: 0, eyeTY: 0, sacAt: rnd(0.8, 2.2), hx: 0, hy: 0, hz: 0, smile: 0.16 };
    VIS.forEach(function (n) { D.vis[n] = 0; });
    D.update = function (dt, t, inp) {
      dt = Math.max(0.001, Math.min(0.1, dt)); inp = inp || {};
      var spk = !!inp.speaking, talk = !!inp.talk, red = inp.reduced ? 0.4 : 1, pos = inp.pos || 0;
      // mouth: eased towards the viseme under the text position (about 40 ms to open, 70 ms to release)
      var tg = spk ? targets(inp.text, pos, inp.paused) : {}, wob = 0.9 + 0.1 * Math.sin(t * 17), sum = 0, mx = 0;
      VIS.forEach(function (n) {
        var target = Math.min(1, (tg[n] || 0) * wob), cur = D.vis[n];
        cur += (target - cur) * (1 - Math.exp(-dt / (target > cur ? 0.04 : 0.07)));
        D.vis[n] = cur; sum += cur; if (cur > mx) mx = cur;
      });
      var sc = sum > 1.2 ? 1.2 / sum : 1;
      // blink: close 70 ms, open 110 ms; gaps 2.2-5.5 s (a little longer while listening), 18% double blinks
      if (D.blinkPhase < 0 && t >= D.blinkAt) D.blinkPhase = 0;
      if (D.blinkPhase >= 0) {
        D.blinkPhase += dt; var cl = 0.07, op = 0.11, p = D.blinkPhase;
        D.blink = p < cl ? ease(p / cl) : p < cl + op ? 1 - ease((p - cl) / op) : 0;
        if (p >= cl + op) {
          D.blinkPhase = -1; D.blink = 0;
          if (D.blinkDouble) { D.blinkDouble = false; D.blinkAt = t + 0.12; }
          else { D.blinkAt = t + rnd(2.2, 5.5) * (inp.listening ? 1.3 : 1); D.blinkDouble = rand() < 0.18; }
        }
      }
      // brows: lift on a question mark and on a new sentence, a little while listening, tiny drift otherwise
      if (pos < D.sentenceAt) D.sentenceAt = 0;
      if (spk) {
        var ch = String(inp.text || "").charAt(Math.floor(pos));
        if (ch === "?") D.browT = 1;
        else if (pos - D.sentenceAt > 40) { D.browT = 0.55; D.sentenceAt = pos; }
        else D.browT = Math.max(0, D.browT - dt * 0.8);
      } else { D.sentenceAt = 0; D.browT = inp.listening ? 0.35 : Math.max(0, D.browT - dt * 0.8); }
      D.brow += (D.browT - D.brow) * (1 - Math.exp(-dt / 0.25));
      var brow = Math.min(1, D.brow + 0.07 + 0.05 * Math.sin(t * 0.37));
      // eyes: small saccades, mostly back to the camera (more so while speaking)
      D.sacAt -= dt;
      if (D.sacAt <= 0) {
        var back = rand() < (spk ? 0.7 : 0.5);
        D.eyeTX = back ? 0 : rnd(-1, 1) * 0.11; D.eyeTY = back ? 0 : rnd(-0.5, 0.5) * 0.05; D.sacAt = rnd(0.7, 2.6);
      }
      var ke = 1 - Math.exp(-dt / 0.05); D.eyeX += (D.eyeTX - D.eyeX) * ke; D.eyeY += (D.eyeTY - D.eyeY) * ke;
      // head (radians, world axes: x = nod down, y = turn, z = tilt): sway, nod while speaking, tilt while listening
      var tY = (talk ? Math.sin(t * 0.8) * 0.03 : Math.sin(t * 0.5) * 0.018) * red;
      var tX = (Math.sin(t * 0.37) * 0.008 + (spk ? Math.max(0, Math.sin(t * 3.1)) * 0.02 + mx * 0.012 : 0)) * red;
      var tZ = (Math.sin(t * 0.43) * 0.008 + (inp.listening ? 0.04 : 0)) * red, kh = 1 - Math.exp(-dt / 0.18);
      D.hx += (tX - D.hx) * kh; D.hy += (tY - D.hy) * kh; D.hz += (tZ - D.hz) * kh;
      // light resting smile, eased off while the mouth is shaping a sound
      D.smile += ((inp.listening ? 0.22 : spk ? 0.14 : 0.16) - D.smile) * (1 - Math.exp(-dt / 0.4));
      var smile = D.smile * (1 - 0.6 * Math.min(1, mx)), m = {};
      VIS.forEach(function (n) { m["viseme_" + n] = D.vis[n] * sc; });
      m.viseme_sil = 0;
      m.eyeBlinkLeft = D.blink; m.eyeBlinkRight = D.blink;
      m.browInnerUp = brow * 0.9; m.browOuterUpLeft = brow * 0.5; m.browOuterUpRight = brow * 0.5;
      m.mouthSmileLeft = smile; m.mouthSmileRight = smile; m.cheekSquintLeft = smile * 0.3; m.cheekSquintRight = smile * 0.3;
      return { morph: m, head: { x: D.hx, y: D.hy, z: D.hz }, eyes: { x: D.eyeX, y: D.eyeY }, breath: Math.sin(t * 1.3) * red };
    };
    return D;
  }

  /* ---------------- capability ---------------- */
  var SUP = null, DISABLED = false, LAST_ERR = "";
  function search() { return root.location && root.location.search ? root.location.search : ""; }
  function supported() {
    if (SUP !== null) return SUP;
    try {
      var c = root.document.createElement("canvas"), gl = c.getContext("webgl2") || c.getContext("webgl");
      SUP = !!(root.WebGLRenderingContext && gl);
      if (gl) { var x = gl.getExtension("WEBGL_lose_context"); if (x) x.loseContext(); }
    } catch (e) { SUP = false; }
    return SUP;
  }
  function enabled() { return !DISABLED && !/[?&]avatar=2d\b/.test(search()) && supported(); }

  /* ---------------- model loading (lazy, cached) ---------------- */
  var CACHE = {};
  function modelKey() { var m = /[?&]model=([a-z0-9_]+)/i.exec(search()); return m && MODELS[m[1]] ? m[1] : "naradvani"; }
  function loadFrom(url) {
    return Promise.all([import(VENDOR + "three.module.js"), import(VENDOR + "GLTFLoader.js"), import(VENDOR + "meshopt_decoder.module.js")]).then(function (m) {
      var loader = new m[1].GLTFLoader(), dec = m[2].MeshoptDecoder;
      return Promise.resolve(dec && dec.ready).then(function () { if (dec) loader.setMeshoptDecoder(dec); return loader.loadAsync(url); })
        .then(function (g) { return { THREE: m[0], gltf: g, url: url, rig: null }; });
    });
  }
  function loadModel() {
    var key = modelKey();
    function get(k) { if (!CACHE[k]) CACHE[k] = loadFrom(MODELS[k]).catch(function (e) { delete CACHE[k]; throw e; }); return CACHE[k]; }
    return get(key).catch(function (e) { if (key === "naradvani") throw e; return get("naradvani"); });
  }
  function tuneMaterial(o) {
    (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) {
      if (!m) return;
      var nm = (m.name || "") + " " + (o.name || "");
      if (/hair|lash|brow/i.test(nm) || m.alphaTest > 0 || (m.transparent && m.map && !/eye|cornea|glass/i.test(nm))) {
        m.alphaToCoverage = true; m.transparent = false; m.depthWrite = true; if (!(m.alphaTest > 0)) m.alphaTest = 0.3; m.side = 2;   // hair cards: cut-out edges, smoothed by MSAA
      }
      if (/cloth|shawl|drape/i.test(nm)) m.side = 2;
      if (/(^|[^a-z])eye(ball)?([^a-z]|$)/i.test(m.name || "") && !/cornea|lash|brow/i.test(nm) && m.color) m.color.setRGB(CFG.eyeTint, CFG.eyeTint * 0.94, CFG.eyeTint * 0.88);   // calm the sclera against the skin, warm the iris
      if (/cornea/i.test(nm)) {                                                        // a thin gloss layer: transmission would hide the iris on a transparent canvas and costs a pass
        m.transmission = 0; m.transparent = true; m.opacity = CFG.cornea; m.depthWrite = false; m.roughness = 0.05; if ("thickness" in m) m.thickness = 0;
      }
      m.needsUpdate = true;
    });
  }
  function buildRig(M) {
    if (M.rig) return M.rig;
    var THREE = M.THREE, scene = M.gltf.scene, rig = { morphs: {}, bones: {}, byName: {}, missing: [], size: null, center: null };
    scene.updateMatrixWorld(true);
    scene.traverse(function (o) {
      if (o.isSkinnedMesh) o.frustumCulled = false;
      if (o.isMesh) tuneMaterial(o);
      if (o.isMesh && o.morphTargetDictionary && o.morphTargetInfluences) {
        Object.keys(o.morphTargetDictionary).forEach(function (k) { (rig.morphs[k] = rig.morphs[k] || []).push([o, o.morphTargetDictionary[k]]); });
      }
      if (o.isBone) rig.byName[o.name.replace(/^mixamorig:?/i, "").toLowerCase()] = o;
    });
    [["head", "head"], ["neck", "neck"], ["chest", "spine2"], ["chest", "spine1"], ["eyeL", "lefteye"], ["eyeR", "righteye"]].forEach(function (p) {
      var b = rig.byName[p[1]]; if (!b || rig.bones[p[0]]) return;
      var P = new THREE.Quaternion(); if (b.parent) b.parent.getWorldQuaternion(P);
      rig.bones[p[0]] = { b: b, rest: b.quaternion.clone(), P: P, iP: P.clone().invert() };
    });
    REQUIRED.forEach(function (n) { if (!rig.morphs[n]) rig.missing.push(n); });
    var box = new THREE.Box3().setFromObject(scene);
    rig.size = box.getSize(new THREE.Vector3()); rig.center = box.getCenter(new THREE.Vector3());
    M.rig = rig; return rig;
  }

  /* ---------------- mounting ---------------- */
  var TOK = 0, A = null;
  function fitCamera(cam, rig, aspect) {
    var hv = Math.tan(cam.fov * Math.PI / 360), half = 0.5 * CFG.margin * Math.max(rig.size.y, rig.size.x / aspect), d = half / hv + rig.size.z * 0.5;
    var y = rig.center.y + CFG.shiftY * rig.size.y;
    cam.position.set(rig.center.x, y, rig.center.z + d); cam.lookAt(rig.center.x, y, rig.center.z);
    cam.aspect = aspect; cam.near = 0.05; cam.far = d + 5; cam.updateProjectionMatrix();
  }
  function unmount() {
    var a = A; A = null; if (!a) return;
    try { if (a.raf) cancelAnimationFrame(a.raf); } catch (e) { /* ignore */ }
    try { a.scene.remove(a.model.gltf.scene); a.renderer.dispose(); if (a.renderer.forceContextLoss) a.renderer.forceContextLoss(); } catch (e) { /* ignore */ }
    try { if (a.canvas.parentNode) a.canvas.parentNode.removeChild(a.canvas); } catch (e) { /* ignore */ }
  }
  function fail(reason) { LAST_ERR = String(reason); if (reason === "too slow") DISABLED = true; var o = A && A.opts; unmount(); if (o && o.onFail) o.onFail(reason); }
  function rotate(rec, x, y, z, tmp) {                                                   // rotate a bone about world axes, whatever its local axes are
    if (!rec) return;
    tmp.e.set(x, y, z, "XYZ"); tmp.d.setFromEuler(tmp.e);
    rec.b.quaternion.copy(rec.iP).multiply(tmp.d).multiply(rec.P).multiply(rec.rest);
  }
  function start(host, opts, M, tok) {
    var THREE = M.THREE, rig = buildRig(M), canvas, renderer;
    try {
      canvas = root.document.createElement("canvas"); canvas.className = "nv3d"; canvas.setAttribute("aria-hidden", "true"); host.appendChild(canvas);
      renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
    } catch (e) { if (canvas && canvas.parentNode) canvas.parentNode.removeChild(canvas); LAST_ERR = "webgl: " + (e && e.message); return false; }
    renderer.setClearColor(0x000000, 0); renderer.toneMappingExposure = CFG.exposure;
    renderer.toneMapping = CFG.tone === "neutral" && THREE.NeutralToneMapping ? THREE.NeutralToneMapping : CFG.tone === "agx" && THREE.AgXToneMapping ? THREE.AgXToneMapping : THREE.ACESFilmicToneMapping;
    var dpr = Math.min(root.devicePixelRatio || 1, CFG.maxDpr); renderer.setPixelRatio(dpr);
    var scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(CFG.fov, 1, 0.05, 20);
    var Lk = CFG.light, key = new THREE.DirectionalLight(0xffe2bd, 2.4 * Lk); key.position.set(0.7, 0.9, 1.2);
    var fill = new THREE.DirectionalLight(0xffd2a0, 0.7 * Lk); fill.position.set(-0.9, 0.2, 1);
    var rim = new THREE.DirectionalLight(0xbcd4ff, 1.1 * Lk); rim.position.set(-0.8, 0.6, -1);
    scene.add(new THREE.HemisphereLight(0xfff1dc, 0x3a2a22, 0.9 * Lk), key, fill, rim, M.gltf.scene);
    M.gltf.scene.rotation.y = CFG.faceYaw;
    var aniso = renderer.capabilities && renderer.capabilities.getMaxAnisotropy ? Math.min(8, renderer.capabilities.getMaxAnisotropy()) : 1;
    M.gltf.scene.traverse(function (o) { if (o.isMesh && o.material && o.material.map) o.material.map.anisotropy = aniso; });
    var a = { canvas: canvas, renderer: renderer, scene: scene, cam: cam, model: M, rig: rig, opts: opts, driver: createDriver(), raf: 0, last: 0, w: 0, h: 0,
      frames: 0, acc: 0, slowStrikes: 0, dpr: dpr, fps: 0, tmp: { e: new THREE.Euler(), d: new THREE.Quaternion() },
      reduced: !!(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches) };
    A = a;
    canvas.addEventListener("webglcontextlost", function (ev) { ev.preventDefault(); if (A === a) fail("webgl context lost"); });
    function tick(now) {
      if (A !== a) return;
      a.raf = requestAnimationFrame(tick);
      if (!canvas.isConnected) { unmount(); return; }
      var dt = a.last ? (now - a.last) / 1000 : 0.016; a.last = now;
      if (root.document.hidden) return;
      var w = host.clientWidth || 300, h = host.clientHeight || 300;
      if (w !== a.w || h !== a.h) { a.w = w; a.h = h; renderer.setSize(w, h, false); fitCamera(cam, rig, w / h); }
      var S = (opts && opts.state) || {};
      var out = a.driver.update(dt, now / 1000, { speaking: !!(S.speaking && S.track), text: S.text || "", pos: S.pos || 0, paused: S.paused > 0,
        listening: !!S.listening, talk: S.mode === "talk", reduced: a.reduced });
      Object.keys(out.morph).forEach(function (k) { var l = rig.morphs[k]; if (l) for (var i = 0; i < l.length; i++) l[i][0].morphTargetInfluences[l[i][1]] = out.morph[k]; });
      var r = rig.bones, hd = out.head, P = CFG.pose;
      if (P) { hd = { x: P.x || 0, y: P.y || 0, z: P.z || 0 }; out.eyes = { x: P.ex || 0, y: P.ey || 0 }; }
      rotate(r.neck, hd.x * 0.4, hd.y * 0.4, hd.z * 0.4, a.tmp); rotate(r.head, hd.x * 0.6, hd.y * 0.6, hd.z * 0.6, a.tmp);
      rotate(r.chest, out.breath * 0.004, 0, 0, a.tmp);
      rotate(r.eyeL, out.eyes.y, out.eyes.x, 0, a.tmp); rotate(r.eyeR, out.eyes.y, out.eyes.x, 0, a.tmp);
      renderer.render(scene, cam);
      // adaptive quality: drop to 1x pixels once, then give up on 3D if it is still slow (the 2D portrait takes over)
      a.frames++; a.acc += dt;
      if (a.frames >= 90) {
        var avg = a.acc / a.frames; a.fps = Math.round(1 / avg); a.frames = 0; a.acc = 0;
        if (avg * 1000 > CFG.slowMs) { if (a.dpr > 1) { a.dpr = 1; renderer.setPixelRatio(1); a.w = 0; } else if (++a.slowStrikes >= 2) fail("too slow"); } else a.slowStrikes = 0;
      }
    }
    a.raf = requestAnimationFrame(tick);
    return true;
  }
  function mount(host, opts) {
    var tok = ++TOK; unmount();
    if (!host || !enabled()) return Promise.resolve(false);
    return loadModel().then(function (M) {
      if (tok !== TOK || !host.isConnected) return false;
      return start(host, opts || {}, M, tok);
    }).catch(function (e) { LAST_ERR = String((e && e.message) || e); return false; });
  }
  function report() {
    return { active: !!A, enabled: enabled(), model: A ? A.model.url : null, missing: A ? A.rig.missing : [], bones: A ? Object.keys(A.rig.bones) : [],
      morphs: A ? Object.keys(A.rig.morphs).length : 0, fps: A ? A.fps : 0, error: LAST_ERR };
  }
  function materials() {                                                               // debug: what three.js built from the GLB
    var r = []; if (!A) return r;
    A.model.gltf.scene.traverse(function (o) {
      if (!o.isMesh) return;
      [].concat(o.material).forEach(function (m) {
        r.push({ mesh: o.name, mat: m.name, type: m.type, color: m.color && m.color.getHexString(), map: !!m.map, metal: m.metalness, rough: m.roughness,
          transmission: m.transmission || 0, transparent: m.transparent, opacity: m.opacity, alphaTest: m.alphaTest, normalMap: !!m.normalMap, spec: m.specularIntensity === undefined ? null : m.specularIntensity });
      });
    });
    return r;
  }
  function morphValues(names) {                                                       // debug: current influence of named shape keys (first mesh that has each)
    var o = {}; if (!A) return o;
    (names || Object.keys(A.rig.morphs)).forEach(function (n) { var l = A.rig.morphs[n]; if (l && l[0]) o[n] = l[0][0].morphTargetInfluences[l[0][1]]; });
    return o;
  }
  var API = { supported: supported, enabled: enabled, mount: mount, unmount: unmount, isActive: function () { return !!A; }, report: report, materials: materials, morphValues: morphValues,
    disable: function () { DISABLED = true; unmount(); }, createDriver: createDriver, visemeFor: visemeFor, targets: targets, VIS: VIS, CFG: CFG, MODELS: MODELS };
  root.AM3D = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : globalThis);
