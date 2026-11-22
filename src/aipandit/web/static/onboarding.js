/* AstroMuni v1.1: API helper, OpenStreetMap place picker (Leaflet), and the one-question-per-screen onboarding:
   language, name, gender, date, time (with "I don't know"), place with a map pin, then optional palm photos (skippable). */
(function () {
  "use strict";
  var AM = (window.AM = window.AM || {});
  var t = function (k, v) { return AM.t(k, v); }, esc = function (s) { return AM.esc(s); };

  /* ---------------------------------------------------------------- api */
  AM.api = async function (path, body) {
    var r;
    try {
      r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    } catch (e) { throw new Error(t("offline")); }
    var j = {};
    try { j = await r.json(); } catch (e) { /* non-json */ }
    if (!r.ok) { var err = new Error(j.error || ("HTTP " + r.status)); err.alternatives = j.alternatives || []; throw err; }
    return j;
  };
  AM.toast = function (msg, ms) {
    var el = document.getElementById("amToast"); if (!el) return;
    el.textContent = msg; el.hidden = false; clearTimeout(AM._tt); AM._tt = setTimeout(function () { el.hidden = true; }, ms || 3200);
  };
  AM.store = {
    get: function (k) { try { return localStorage.getItem(k) || sessionStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v, persist) { try { (persist ? localStorage : sessionStorage).setItem(k, v); if (persist) sessionStorage.removeItem(k); else localStorage.removeItem(k); } catch (e) { /* private mode */ } },
    del: function (k) { try { localStorage.removeItem(k); sessionStorage.removeItem(k); } catch (e) { /* ignore */ } }
  };

  /* ---------------------------------------------------------------- leaflet (vendored, no CDN) */
  var leafletP = null;
  AM.loadLeaflet = function () {
    if (window.L) return Promise.resolve(window.L);
    if (leafletP) return leafletP;
    leafletP = new Promise(function (res, rej) {
      var s = document.createElement("script"); s.src = "/static/vendor/leaflet.js?v=1.1.0";
      s.onload = function () { window.L ? res(window.L) : rej(new Error("leaflet")); };
      s.onerror = function () { rej(new Error("leaflet")); };
      document.head.appendChild(s);
    });
    return leafletP;
  };
  var TZ_FALLBACK = ["Asia/Kolkata", "Asia/Kathmandu", "Asia/Colombo", "Asia/Dhaka", "Asia/Karachi", "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo", "Europe/London", "Europe/Paris", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Toronto", "Australia/Sydney", "Pacific/Auckland", "Africa/Johannesburg", "Africa/Nairobi"];
  function tzList() { try { if (Intl.supportedValuesOf) return Intl.supportedValuesOf("timeZone"); } catch (e) { /* old browser */ } return TZ_FALLBACK; }

  /* ---------------------------------------------------------------- place picker */
  AM.placePicker = function (root, initial, opts) {
    opts = opts || {};
    var S = { name: "", lat: null, lon: null, tz: "", country: "" };
    if (initial && initial.lat != null) S = { name: initial.place || "", lat: initial.lat, lon: initial.lon, tz: initial.tz || "", country: "" };
    var map = null, marker = null, L = null, lastSearch = 0;
    var tzs = tzList();
    root.innerHTML =
      '<div class="field"><span>' + esc(t("f_place")) + '</span><div class="row"><input id="plQ" class="grow" type="text" autocomplete="off" placeholder="' + esc(t("f_place_ph")) + '" value="' + esc(S.name) + '"><button type="button" class="btn ghost" id="plGo">' + esc(t("search")) + '</button></div><span class="hint">' + esc(t("place_hint")) + '</span></div>' +
      '<ul class="results" id="plRes" hidden></ul>' +
      (opts.noMap ? "" : '<div class="mapbox"><div id="amMap"></div></div>') +
      '<div class="picked" id="plPicked" hidden></div>' +
      '<div class="form-grid"><label class="field"><span>' + esc(t("tz")) + '</span><select id="plTz"><option value="">' + esc(t("tz_pick")) + '</option>' + tzs.map(function (z) { return '<option value="' + esc(z) + '">' + esc(z) + '</option>'; }).join("") + '</select></label>' +
      '<details class="field"><summary class="small">' + esc(t("enter_coords")) + '</summary><div class="form-grid"><input id="plLat" type="number" step="0.0001" placeholder="Lat"><input id="plLon" type="number" step="0.0001" placeholder="Lon"></div></details></div>' +
      '<p class="err" id="plErr"></p>';
    var $ = function (id) { return root.querySelector("#" + id); };

    function paint() {
      var p = $("plPicked");
      if (S.lat == null) { p.hidden = true; return; }
      p.hidden = false;
      p.innerHTML = '<span>📍</span><div><b>' + esc(t("picked")) + '</b><br>' + esc(S.name || "") + '<br><span class="muted small">' + S.lat.toFixed(4) + ', ' + S.lon.toFixed(4) + '</span></div>';
      $("plLat").value = S.lat; $("plLon").value = S.lon;
      if (S.tz) { if (!Array.prototype.some.call($("plTz").options, function (o) { return o.value === S.tz; })) { var o = document.createElement("option"); o.value = o.textContent = S.tz; $("plTz").appendChild(o); } $("plTz").value = S.tz; }
      $("plErr").textContent = S.tz ? "" : t("tz_needed");
      if (opts.onChange) opts.onChange(S);
    }
    function place(lat, lon, name, tz, country, pan) {
      S.lat = Math.round(lat * 1e5) / 1e5; S.lon = Math.round(lon * 1e5) / 1e5; if (name != null) S.name = name; if (tz !== undefined) S.tz = tz || S.tz || ""; if (country) S.country = country;
      if (map && L) {
        if (!marker) { marker = L.marker([S.lat, S.lon], { draggable: true, icon: L.divIcon({ className: "", html: '<div class="pin"></div>', iconSize: [26, 26], iconAnchor: [13, 26] }) }).addTo(map); marker.on("dragend", function () { var p = marker.getLatLng(); pinned(p.lat, p.lng); }); }
        else marker.setLatLng([S.lat, S.lon]);
        if (pan) map.setView([S.lat, S.lon], Math.max(map.getZoom(), 10));
      }
      paint();
    }
    async function pinned(lat, lon) {      // user dropped / dragged the pin: coordinates are exact, name and tz come from reverse lookup
      place(lat, lon, S.name, S.tz, "", false);
      try { var r = await AM.api("/api/v10/reverse", { lat: lat, lon: lon }); place(r.lat, r.lon, r.name || r.display, r.tz || S.tz, r.country, false); }
      catch (e) { $("plErr").textContent = e.message; }
    }
    async function search() {
      var q = $("plQ").value.trim(), box = $("plRes"); $("plErr").textContent = "";
      if (q.length < 3) return;
      var now = Date.now(); if (now - lastSearch < 1100) return; lastSearch = now;
      box.hidden = false; box.innerHTML = '<li class="small muted pad-s">' + esc(t("loading")) + '</li>';
      try {
        var r = await AM.api("/api/v10/geocode", { q: q, lang: AM.lang() });
        box.innerHTML = r.results.length ? r.results.map(function (x, i) { return '<li><button type="button" data-i="' + i + '">' + esc(x.display) + '</button></li>'; }).join("") : '<li class="small muted pad-s">—</li>';
        box.onclick = function (ev) { var b = ev.target.closest("button[data-i]"); if (!b) return; var x = r.results[+b.dataset.i]; box.hidden = true; $("plQ").value = x.name; place(x.lat, x.lon, x.display, x.tz, x.country, true); };
      } catch (e) { box.hidden = true; $("plErr").textContent = e.message; }
    }
    $("plGo").onclick = search;
    $("plQ").onkeydown = function (e) { if (e.key === "Enter") { e.preventDefault(); search(); } };
    $("plTz").onchange = function (e) { S.tz = e.target.value; $("plErr").textContent = S.tz ? "" : t("tz_needed"); if (opts.onChange) opts.onChange(S); };
    var manual = function () { var a = parseFloat($("plLat").value), b = parseFloat($("plLon").value); if (isFinite(a) && isFinite(b) && Math.abs(a) <= 90 && Math.abs(b) <= 180) pinned(a, b).then(function () { if (map) map.setView([a, b], 9); }); };
    $("plLat").onchange = $("plLon").onchange = manual;

    if (!opts.noMap) {
      AM.loadLeaflet().then(function (Lf) {
        L = Lf; var el = $("amMap"); if (!el) return;
        map = L.map(el, { center: S.lat != null ? [S.lat, S.lon] : [22.5, 79], zoom: S.lat != null ? 10 : 4, worldCopyJump: true });
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap contributors" }).addTo(map);
        map.on("click", function (e) { pinned(e.latlng.lat, e.latlng.lng); });
        if (S.lat != null) place(S.lat, S.lon, S.name, S.tz, "", false);
        setTimeout(function () { map.invalidateSize(); }, 250);
      }).catch(function () { var m = root.querySelector(".mapbox"); if (m) m.innerHTML = '<div class="map-fallback">' + esc(t("map_off")) + '</div>'; var d = root.querySelector("details"); if (d) d.open = true; });
    }
    if (S.lat != null) paint();
    return { get: function () { return { place: S.name, lat: S.lat, lon: S.lon, tz: S.tz }; }, destroy: function () { if (map) map.remove(); map = null; } };
  };

  /* ---------------------------------------------------------------- image helper */
  AM.resizeToJpeg = function (file) {
    return new Promise(function (res, rej) {
      if (!file || !/^image\/(jpeg|png|webp|heic|heif)$/i.test(file.type || "image/jpeg")) return rej(new Error(t("palm_bad")));
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var max = 1024, k = Math.min(1, max / Math.max(img.width, img.height)), c = document.createElement("canvas");
        c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);      // re-encoding drops EXIF / GPS metadata
        URL.revokeObjectURL(url);
        var q = 0.82, out = c.toDataURL("image/jpeg", q);
        while (out.length * 0.75 > 560 * 1024 && q > 0.4) { q -= 0.1; out = c.toDataURL("image/jpeg", q); }
        res(out);
      };
      img.onerror = function () { URL.revokeObjectURL(url); rej(new Error(t("palm_bad"))); };
      img.src = url;
    });
  };

  /* ---------------------------------------------------------------- onboarding (one question per screen) */
  var TOTAL = 7;
  function overlay(html, dim) { var m = document.getElementById("amModal"); m.className = "am-overlay" + (dim ? " dim" : ""); m.innerHTML = html; m.hidden = false; m.scrollTop = 0; return m; }
  AM.closeModal = function () { var m = document.getElementById("amModal"); m.hidden = true; m.innerHTML = ""; };
  var LOGO = '<div class="logo"><img src="/static/icon.svg" alt=""><b>AstroMuni</b></div>';
  function progress(n) { return '<div class="pbar" aria-hidden="true"><i></i></div><p class="small muted ob-step">' + esc(t("ob_step", { n: n, m: TOTAL })) + '</p>'; }
  function frame(n, inner, wide) {
    var m = overlay('<div class="win' + (wide ? " wide" : "") + '"><form id="obForm" novalidate>' + LOGO + progress(n) + inner + '</form></div>');
    var bar = m.querySelector(".pbar i"); if (bar) requestAnimationFrame(function () { bar.style.width = Math.round(100 * n / TOTAL) + "%"; });
    return m;
  }
  function actions(backLabel, nextLabel, hideNext) {
    return '<div class="actions"><button type="button" class="btn ghost" id="obBack">' + esc(backLabel) + '</button>' + (hideNext ? "" : '<button type="submit" class="btn">' + esc(nextLabel || t("next")) + '</button>') + '</div>';
  }

  /* opts: {profile?, palms?, startAt: "lang"|"details", onDone(result), onCancel?} */
  AM.runOnboarding = function (opts) {
    var data = Object.assign({ name: "", dob: "", tob: "", time_certainty: "exact", place: "", lat: null, lon: null, tz: "", gender: "prefer_not_to_say" }, opts.profile || {});
    if (data.time_certainty === "part_of_day") data.time_certainty = "unknown";
    var palms = Object.assign({}, opts.palms || {}), remember = opts.remember !== false, picker = null;
    var today = new Date().toISOString().slice(0, 10), editing = opts.startAt === "details" && !!opts.onCancel;
    var $ = function (m, id) { return m.querySelector("#" + id); };
    function wire(m, onBack, onNext) {
      $(m, "obForm").onsubmit = function (e) { e.preventDefault(); onNext(); };
      if ($(m, "obBack")) $(m, "obBack").onclick = onBack;
      var f = m.querySelector("input:not([type=radio]):not([type=checkbox]):not([type=file])"); if (f && f.type !== "hidden" && window.innerWidth > 700) f.focus();
    }
    function err(m, msg) { var e = $(m, "obErr"); if (e) e.textContent = msg || ""; return false; }

    function stepLang() {
      var m = overlay('<div class="win">' + LOGO + progress(1) + '<h2>' + esc(t("lang_title")) + '</h2><p class="lead">' + esc(t("lang_sub")) + '</p><div class="lang-grid">' +
        AM.langs.map(function (l) { return '<button type="button" data-l="' + l[0] + '">' + esc(l[1]) + '<small>' + esc(l[2]) + '</small></button>'; }).join("") + '</div></div>');
      var bar = m.querySelector(".pbar i"); requestAnimationFrame(function () { bar.style.width = Math.round(100 / TOTAL) + "%"; });
      m.querySelector(".lang-grid").onclick = function (e) { var b = e.target.closest("button[data-l]"); if (!b) return; AM.setLang(b.dataset.l); AM.store.set("astromuni_lang", b.dataset.l, true); stepName(); };
    }

    function stepName(msg) {
      var m = frame(2, '<h2>' + esc(t("q_name")) + '</h2><p class="lead">' + esc(t("name_why")) + '</p><label class="field"><input id="obName" type="text" autocomplete="name" maxlength="60" placeholder="' + esc(t("q_name_ph")) + '" value="' + esc(data.name) + '"></label><p class="err" id="obErr">' + esc(msg || "") + '</p>' +
        actions(editing ? t("cancel") : t("back")));
      wire(m, function () { if (editing) { AM.closeModal(); opts.onCancel(); } else stepLang(); }, function () {
        data.name = $(m, "obName").value.trim(); if (!data.name) return err(m, t("e_name")); stepGender();
      });
    }

    function stepGender() {
      var gens = [["male", "g_male"], ["female", "g_female"], ["other", "g_other"], ["prefer_not_to_say", "g_na"]];
      var m = frame(3, '<h2>' + esc(t("q_gender")) + '</h2><div class="choices">' + gens.map(function (g) { return '<button type="button" class="choice' + (g[0] === data.gender && opts.profile ? " on" : "") + '" data-g="' + g[0] + '">' + esc(t(g[1])) + '</button>'; }).join("") + '</div>' + actions(t("back"), t("next")));
      m.querySelector(".choices").onclick = function (e) { var b = e.target.closest("[data-g]"); if (!b) return; data.gender = b.dataset.g; stepDob(); };
      wire(m, function () { stepName(); }, function () { stepDob(); });
    }

    function stepDob(msg) {
      var m = frame(4, '<h2>' + esc(t("q_dob")) + '</h2><label class="field"><input id="obDob" type="date" min="1900-01-01" max="' + today + '" value="' + esc(data.dob) + '"></label><p class="err" id="obErr">' + esc(msg || "") + '</p>' + actions(t("back")));
      wire(m, function () { stepGender(); }, function () {
        var v = $(m, "obDob").value; if (!v || v > today || v < "1900-01-01") return err(m, t("e_dob")); data.dob = v; stepTime();
      });
    }

    function stepTime(msg) {
      var unk = data.time_certainty === "unknown";
      var m = frame(5, '<h2>' + esc(t("q_tob")) + '</h2><p class="lead">' + esc(t("tob_why")) + '</p><label class="field"><input id="obTob" type="time" value="' + esc(unk ? "" : (data.tob || "")) + '"></label>' +
        '<label class="check mt-s"><input type="checkbox" id="obApprox"' + (data.time_certainty === "approx_15min" ? " checked" : "") + '><span>' + esc(t("tob_approx")) + '</span></label>' +
        '<p class="err" id="obErr">' + esc(msg || "") + '</p><div class="center"><button type="button" class="btn link" id="obUnk">' + esc(t("tob_unknown")) + '</button></div>' + actions(t("back")));
      $(m, "obUnk").onclick = function () { data.time_certainty = "unknown"; data.tob = ""; stepPlace(); };
      wire(m, function () { stepDob(); }, function () {
        var v = $(m, "obTob").value; if (!v) return err(m, t("e_tob"));
        data.tob = v; data.time_certainty = $(m, "obApprox").checked ? "approx_15min" : "exact"; stepPlace();
      });
    }

    function stepPlace(msg) {
      var m = frame(6, '<h2>' + esc(t("q_place")) + '</h2><div id="obPlace"></div><label class="check mt-m"><input type="checkbox" id="obRem"' + (remember ? " checked" : "") + '><span>' + esc(t("remember")) + '</span></label><p class="err" id="obErr">' + esc(msg || "") + '</p>' + actions(t("back")), true);
      if (picker) picker.destroy();
      picker = AM.placePicker($(m, "obPlace"), data, {});
      function collect() { var p = picker.get(); data.place = p.place; data.lat = p.lat; data.lon = p.lon; data.tz = p.tz; remember = $(m, "obRem").checked; }
      wire(m, function () { collect(); picker.destroy(); picker = null; stepTime(); }, function () {
        collect(); if (data.lat == null) return err(m, t("e_place")); if (!data.tz) return err(m, t("e_tz"));
        picker.destroy(); picker = null; stepPalms();
      });
    }

    function stepPalms() {
      var m = overlay('<div class="win wide">' + LOGO + progress(7) + '<h2>' + esc(t("palm_title")) + '</h2><p class="lead">' + esc(t("palm_lead")) + '</p><div class="palms">' +
        ["left", "right"].map(function (s) { return '<label class="drop" data-s="' + s + '"><input type="file" accept="image/*" capture="environment" data-s="' + s + '"><span class="emoji-l">🖐️</span><b>' + esc(t(s + "_hand")) + '</b><span class="muted small">' + esc(t("tap_upload")) + '</span></label>'; }).join("") +
        '</div><p class="small muted mt-s">' + esc(t("palm_note")) + '</p><p class="err" id="pmErr"></p>' +
        '<div class="actions"><button type="button" class="btn ghost" id="pmBack">' + esc(t("back")) + '</button><button type="button" class="btn" id="pmGo">' + esc(t("palm_continue")) + '</button></div>' +
        '<div class="center mt-m"><button type="button" class="btn link" id="pmSkip">' + esc(t("skip_continue")) + '</button></div></div>');
      var bar = m.querySelector(".pbar i"); requestAnimationFrame(function () { bar.style.width = "100%"; });
      function show(side) { var d = m.querySelector('.drop[data-s="' + side + '"]'); if (!d || !palms[side]) return; var old = d.querySelector("img"); if (old) old.remove(); var i = document.createElement("img"); i.alt = ""; i.src = palms[side]; d.appendChild(i); var tg = document.createElement("span"); tg.className = "tag"; tg.textContent = t(side + "_hand"); d.appendChild(tg); }
      show("left"); show("right");
      m.querySelector(".palms").onchange = async function (e) {
        var inp = e.target.closest("input[type=file]"); if (!inp || !inp.files[0]) return;
        try { palms[inp.dataset.s] = await AM.resizeToJpeg(inp.files[0]); show(inp.dataset.s); m.querySelector("#pmErr").textContent = ""; } catch (er) { m.querySelector("#pmErr").textContent = er.message; }
      };
      m.querySelector("#pmBack").onclick = function () { stepPlace(); };
      m.querySelector("#pmSkip").onclick = function () { palms = {}; finish(); };
      m.querySelector("#pmGo").onclick = finish;
    }

    async function finish() {
      overlay('<div class="win center">' + LOGO + '<div class="orbit-wait my-l"><span class="typing"><i></i><i></i><i></i></span></div><h2>' + esc(t("building")) + '</h2></div>');
      var profile = { name: data.name, dob: data.dob, tob: data.time_certainty === "unknown" ? null : data.tob, time_certainty: data.time_certainty, place: data.place, lat: data.lat, lon: data.lon, tz: data.tz, gender: data.gender };
      try {
        var chart = await AM.api("/api/v10/chart", { profile: profile });
        AM.closeModal(); opts.onDone({ profile: profile, palms: palms, chart: chart, remember: remember });
      } catch (e) {
        var alt = (e.alternatives && e.alternatives.length) ? " " + e.alternatives.join(" ") : "";
        stepPlace(t("chart_err") + " " + e.message + alt);
      }
    }
    (editing ? stepName : stepLang)();
  };
})();
