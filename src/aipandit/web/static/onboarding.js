/* AstroMuni v1.0: API helper, OpenStreetMap place picker (Leaflet), and the three-step onboarding:
   1) language  2) birth details with a map pin  3) optional palm photos (skippable). */
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
      var s = document.createElement("script"); s.src = "/static/vendor/leaflet.js?v=1.0.0";
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

  /* ---------------------------------------------------------------- onboarding */
  function overlay(html, dim) { var m = document.getElementById("amModal"); m.className = "am-overlay" + (dim ? " dim" : ""); m.innerHTML = html; m.hidden = false; m.scrollTop = 0; return m; }
  AM.closeModal = function () { var m = document.getElementById("amModal"); m.hidden = true; m.innerHTML = ""; };
  function steps(n) { return '<div class="steps" aria-hidden="true"><i class="on"></i><i class="' + (n >= 2 ? "on" : "") + '"></i><i class="' + (n >= 3 ? "on" : "") + '"></i></div>'; }
  var LOGO = '<div class="logo"><img src="/static/icon.svg" alt=""><b>AstroMuni</b></div>';

  /* opts: {profile?, palms?, startAt: "lang"|"details", onDone(result), onCancel?} */
  AM.runOnboarding = function (opts) {
    var data = Object.assign({ name: "", dob: "", tob: "", time_certainty: "exact", place: "", lat: null, lon: null, tz: "", gender: "prefer_not_to_say" }, opts.profile || {});
    var palms = Object.assign({}, opts.palms || {}), remember = opts.remember !== false, picker = null;

    function stepLang() {
      var m = overlay('<div class="win">' + LOGO + steps(1) + '<h2>' + esc(t("lang_title")) + '</h2><p class="lead">' + esc(t("lang_sub")) + '</p><div class="lang-grid">' +
        AM.langs.map(function (l) { return '<button type="button" data-l="' + l[0] + '">' + esc(l[1]) + '<small>' + esc(l[2]) + '</small></button>'; }).join("") + '</div></div>');
      m.querySelector(".lang-grid").onclick = function (e) { var b = e.target.closest("button[data-l]"); if (!b) return; AM.setLang(b.dataset.l); AM.store.set("astromuni_lang", b.dataset.l, true); stepDetails(); };
    }

    function stepDetails(msg) {
      var certs = ["exact", "approx_15min", "part_of_day", "unknown"], gens = [["male", "g_male"], ["female", "g_female"], ["other", "g_other"], ["prefer_not_to_say", "g_na"]];
      var today = new Date().toISOString().slice(0, 10);
      var m = overlay('<div class="win wide"><form id="obForm" novalidate>' + LOGO + steps(2) + '<h2>' + esc(t("ob_title")) + '</h2><p class="lead">' + esc(t("ob_lead")) + '</p>' +
        '<div class="form-grid">' +
        '<label class="field full"><span>' + esc(t("f_name")) + '</span><input id="obName" type="text" autocomplete="name" maxlength="60" value="' + esc(data.name) + '"></label>' +
        '<label class="field"><span>' + esc(t("f_dob")) + '</span><input id="obDob" type="date" min="1900-01-01" max="' + today + '" value="' + esc(data.dob) + '"></label>' +
        '<label class="field"><span>' + esc(t("f_cert")) + '</span><select id="obCert">' + certs.map(function (c) { return '<option value="' + c + '"' + (c === data.time_certainty ? " selected" : "") + '>' + esc(t("cert_" + c)) + '</option>'; }).join("") + '</select></label>' +
        '<label class="field" id="obTobWrap"><span>' + esc(t("f_tob")) + '</span><input id="obTob" type="time" value="' + esc(data.tob || "") + '"></label>' +
        '<div class="field full" id="obGender"><span>' + esc(t("f_gender")) + '</span><div class="gender">' + gens.map(function (g) { return '<label><input type="radio" name="gender" value="' + g[0] + '"' + (g[0] === data.gender ? " checked" : "") + '><span>' + esc(t(g[1])) + '</span></label>'; }).join("") + '</div></div>' +
        '<div class="full" id="obPlace"></div></div>' +
        '<label class="check mt-m"><input type="checkbox" id="obRem"' + (remember ? " checked" : "") + '><span>' + esc(t("remember")) + '</span></label>' +
        '<p class="err" id="obErr">' + esc(msg || "") + '</p>' +
        '<div class="actions">' + (opts.startAt === "details" && opts.onCancel ? '<button type="button" class="btn ghost" id="obCancel">' + esc(t("cancel")) + '</button>' : '<button type="button" class="btn ghost" id="obBack">' + esc(t("back")) + '</button>') + '<button type="submit" class="btn">' + esc(t("next")) + '</button></div></form></div>');
      var $ = function (id) { return m.querySelector("#" + id); };
      if (picker) picker.destroy();
      picker = AM.placePicker($("obPlace"), data, {});
      var syncCert = function () { $("obTobWrap").hidden = $("obCert").value === "unknown"; }; $("obCert").onchange = syncCert; syncCert();
      if ($("obBack")) $("obBack").onclick = function () { collect(); stepLang(); };
      if ($("obCancel")) $("obCancel").onclick = function () { picker.destroy(); AM.closeModal(); opts.onCancel(); };
      function collect() {
        data.name = $("obName").value.trim(); data.dob = $("obDob").value; data.time_certainty = $("obCert").value; data.tob = $("obTob").value;
        var g = m.querySelector('input[name="gender"]:checked'); data.gender = g ? g.value : "prefer_not_to_say"; remember = $("obRem").checked;
        var p = picker.get(); data.place = p.place; data.lat = p.lat; data.lon = p.lon; data.tz = p.tz;
      }
      $("obForm").onsubmit = function (e) {
        e.preventDefault(); collect(); var err = $("obErr");
        if (!data.name) return err.textContent = t("e_name");
        if (!data.dob || data.dob > today) return err.textContent = t("e_dob");
        if (data.time_certainty !== "unknown" && !data.tob) return err.textContent = t("e_tob");
        if (data.lat == null) return err.textContent = t("e_place");
        if (!data.tz) return err.textContent = t("e_tz");
        picker.destroy(); picker = null; stepPalms();
      };
    }

    function stepPalms() {
      var m = overlay('<div class="win wide">' + LOGO + steps(3) + '<h2>' + esc(t("palm_title")) + '</h2><p class="lead">' + esc(t("palm_lead")) + '</p><div class="palms">' +
        ["left", "right"].map(function (s) { return '<label class="drop" data-s="' + s + '"><input type="file" accept="image/*" capture="environment" data-s="' + s + '"><span class="emoji-l">🖐️</span><b>' + esc(t(s + "_hand")) + '</b><span class="muted small">' + esc(t("tap_upload")) + '</span></label>'; }).join("") +
        '</div><p class="small muted mt-s">' + esc(t("palm_note")) + '</p><p class="err" id="pmErr"></p>' +
        '<div class="actions"><button type="button" class="btn ghost" id="pmBack">' + esc(t("back")) + '</button><button type="button" class="btn" id="pmGo">' + esc(t("palm_continue")) + '</button></div>' +
        '<div class="center mt-m"><button type="button" class="btn link" id="pmSkip">' + esc(t("skip_continue")) + '</button></div></div>');
      function show(side) { var d = m.querySelector('.drop[data-s="' + side + '"]'); if (!d || !palms[side]) return; var old = d.querySelector("img"); if (old) old.remove(); var i = document.createElement("img"); i.alt = ""; i.src = palms[side]; d.appendChild(i); var tg = document.createElement("span"); tg.className = "tag"; tg.textContent = t(side + "_hand"); d.appendChild(tg); }
      show("left"); show("right");
      m.querySelector(".palms").onchange = async function (e) {
        var inp = e.target.closest("input[type=file]"); if (!inp || !inp.files[0]) return;
        try { palms[inp.dataset.s] = await AM.resizeToJpeg(inp.files[0]); show(inp.dataset.s); m.querySelector("#pmErr").textContent = ""; } catch (er) { m.querySelector("#pmErr").textContent = er.message; }
      };
      m.querySelector("#pmBack").onclick = function () { stepDetails(); };
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
        stepDetails(t("chart_err") + " " + e.message + alt);
      }
    }
    (opts.startAt === "details" ? stepDetails : stepLang)();
  };
})();
