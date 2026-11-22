/* AstroMuni v1.1 main app: shell, routing and all screens. No inline handlers or styles (strict CSP). */
(function () {
  "use strict";
  var AM = window.AM, t = AM.t, esc = AM.esc, api = AM.api;
  var KEY = "astromuni_v1_profile";
  var SIGNS = [["Mesha", "Aries", "मेष", "♈"], ["Vrishabha", "Taurus", "वृषभ", "♉"], ["Mithuna", "Gemini", "मिथुन", "♊"], ["Karka", "Cancer", "कर्क", "♋"],
    ["Simha", "Leo", "सिंह", "♌"], ["Kanya", "Virgo", "कन्या", "♍"], ["Tula", "Libra", "तुला", "♎"], ["Vrishchika", "Scorpio", "वृश्चिक", "♏"],
    ["Dhanu", "Sagittarius", "धनु", "♐"], ["Makara", "Capricorn", "मकर", "♑"], ["Kumbha", "Aquarius", "कुंभ", "♒"], ["Meena", "Pisces", "मीन", "♓"]];
  var PL = { en: { Sun: "Sun", Moon: "Moon", Mars: "Mars", Mercury: "Mercury", Jupiter: "Jupiter", Venus: "Venus", Saturn: "Saturn", Rahu: "Rahu", Ketu: "Ketu" },
    hg: { Sun: "Surya", Moon: "Chandra", Mars: "Mangal", Mercury: "Budh", Jupiter: "Guru", Venus: "Shukra", Saturn: "Shani", Rahu: "Rahu", Ketu: "Ketu" },
    hi: { Sun: "सूर्य", Moon: "चंद्र", Mars: "मंगल", Mercury: "बुध", Jupiter: "गुरु", Venus: "शुक्र", Saturn: "शनि", Rahu: "राहु", Ketu: "केतु" } };
  var ABBR = { Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke" };
  var CHIPS = { en: ["How is my career going to be?", "Tell me about love and marriage", "How are my studies?", "What about money?", "Which phase am I in right now?"],
    hg: ["Mera career kaisa rahega?", "Pyaar aur shaadi ke baare mein batao", "Meri padhai kaisi rahegi?", "Paise ka kya haal hai?", "Abhi main kaunse daur mein hoon?"],
    hi: ["मेरा करियर कैसा रहेगा?", "प्रेम और विवाह के बारे में बताइए", "मेरी पढ़ाई कैसी रहेगी?", "पैसे का क्या हाल है?", "अभी मैं किस दौर में हूँ?"] };
  var TOPICS = ["career", "marriage", "wealth", "education", "family", "children", "health"];
  var LEARN = [["Nakshatra", "nakshatra"], ["Vimshottari Dasha", "dasha"], ["Gajakesari yoga", "gajakesari yoga"], ["Sade Sati", "sade sati"], ["Gochara", "gochara transit"], ["Panchang", "panchang"], ["Ashtakoota", "ashtakoota gun milan"], ["Navamsa", "navamsa"]];
  var ICON = {
    hub: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>', ask: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
    horoscope: '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>', chart: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/><path d="M12 3v6.5M12 14.5V21M3 12h6.5M14.5 12H21M5.6 5.6l4.6 4.6M13.8 13.8l4.6 4.6M18.4 5.6l-4.6 4.6M10.2 13.8l-4.6 4.6"/>',
    calculators: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 12h2M12 12h2M8 16h2M12 16h2"/>', reports: '<path d="M7 3h8l4 4v14H7z"/><path d="M15 3v4h4M10 12h6M10 16h6"/>', learn: '<path d="M4 5a2 2 0 012-2h5v17H6a2 2 0 00-2 2zM20 5a2 2 0 00-2-2h-5v17h5a2 2 0 012 2z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', search: '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/>', send: '<path d="M4 12l16-8-6 16-3-7z"/>', heart: '<path d="M12 20s-7-4.6-7-10a4 4 0 017-2.5A4 4 0 0119 10c0 5.4-7 10-7 10z"/>', cal: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>' };
  var svg = function (k) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + ICON[k] + '</svg>'; };

  var S = { route: "hub", profile: null, palms: {}, chart: null, pan: null, horo: null, sel: null, msgs: [], mode: "muni", busy: false, calc: null, calcType: "moon", rep: null, repTopic: "career", learn: null, learnQ: "", compat: null, where: null, drawer: false, loaded: {} };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var lang = function () { return AM.lang(); };
  var first = function () { return ((S.profile && S.profile.name) || "").trim().split(/\s+/)[0] || ""; };
  var signName = function (k) { var s = SIGNS.filter(function (x) { return x[0] === k; })[0]; if (!s) return k || ""; return lang() === "hi" ? s[2] : lang() === "hg" ? s[0] : s[1]; };
  var glyph = function (k) { var s = SIGNS.filter(function (x) { return x[0] === k; })[0]; return s ? s[3] + "︎" : ""; };
  var plName = function (p) { return (PL[lang()] || PL.en)[p] || p; };

  /* ------------------------------------------------------------ persistence */
  function save(remember) {
    var o = JSON.stringify({ profile: S.profile, lang: lang() });
    AM.store.set(KEY, o, remember !== false);
  }
  function resetAll() { AM.store.del(KEY); AM.store.del("astromuni_lang"); S.profile = null; S.palms = {}; S.chart = null; S.msgs = []; S.loaded = {}; S.pan = S.horo = S.calc = S.rep = S.learn = S.compat = null; }

  /* ------------------------------------------------------------ data loading (cached per language) */
  function body(extra) { return Object.assign({ profile: S.profile, lang: lang() }, extra || {}); }
  async function load(name) {
    var key = name + ":" + lang() + (name === "pan" && S.where ? ":" + S.where.lat + "," + S.where.lon : "");
    if (S.loaded[name] === key) return;
    try {
      if (name === "pan") S.pan = await api("/api/v10/panchang", body(S.where ? { where: S.where } : {}));
      if (name === "horo") { S.horo = await api("/api/v10/horoscope", body()); if (!S.sel) S.sel = (S.horo.mine && S.horo.mine.key) || "Simha"; }
      if (name === "chart") S.chart = await api("/api/v10/chart", body());
      S.loaded[name] = key;
    } catch (e) { S.loaded[name] = null; S["err_" + name] = e.message; }
    renderView();
  }
  function loadFor(route) {
    if (route === "hub") { load("horo"); }
    if (route === "horoscope") load("horo");
    if (route === "panchang") load("pan");
    if (route === "chart") load("chart");
    if (route === "reports" && !S.rep) runReport(S.repTopic);
    if (route === "calculators" && !S.calc) runCalc(S.calcType);
  }

  /* ------------------------------------------------------------ shell */
  var NAV = [["hub", "n_hub"], ["ask", "n_ask"], ["horoscope", "n_horo"], ["chart", "n_chart"], ["calculators", "n_calc"], ["reports", "n_reports"], ["learn", "n_learn"]];
  function navHtml() { return NAV.map(function (n) { return '<button type="button" data-go="' + n[0] + '" class="' + (S.route === n[0] ? "on" : "") + '" aria-label="' + esc(t(n[1])) + '">' + svg(n[0]) + '<span class="lbl">' + esc(t(n[1])) + '</span></button>'; }).join(""); }
  function moonCard() {
    var m = S.chart && S.chart.moon ? S.chart.moon : null, tz = (S.pan && S.pan.date_label) ? "" : "";
    return '<button type="button" class="mini" data-act="settings"><span class="sym">' + esc(m ? glyph(m.sign) : "☾") + '</span><span class="t"><small>' + esc(t("moon_sign")) + '</small><b>' + esc(m ? signName(m.sign) + (m.nakshatra ? " • " + m.nakshatra : "") : "—") + '</b></span></button>' +
      '<button type="button" class="mini" data-act="settings"><span class="av">' + esc((first() || "A").slice(0, 2).toUpperCase()) + '</span><span class="t"><b>' + esc(S.profile.name) + '</b><small>' + esc(t("member")) + '</small></span></button>';
  }
  function shell() {
    var root = $("#amRoot");
    root.innerHTML = '<div class="shell"><aside class="side"><div class="logo"><img src="/static/icon.svg" alt=""><div><b>astromuni</b><small>' + esc(t("tagline").slice(0, 0)) + 'Personal Vedic guide</small></div></div><nav class="nav" aria-label="Main">' + navHtml() + '</nav><div class="push"></div>' + moonCard() + '</aside>' +
      '<div class="main"><header class="top"><button type="button" class="icon-btn menu" data-act="drawer" aria-label="Menu">' + svg("menu") + '</button><div class="date"><h4 id="topDate">—</h4><small id="topTithi"></small></div><span class="spacer"></span>' +
      '' +
      '<button type="button" class="btn" data-go="ask">' + svg("ask").replace("<svg", '<svg width="18" height="18"') + esc(t("ask_muni")) + '</button></header><main class="page" id="view"></main></div></div>' +
      '<nav class="tabbar" aria-label="Tabs">' + [["hub", "n_cosmic"], ["ask", "n_ask_s"], ["horoscope", "n_horo_s"], ["chart", "n_my"]].map(function (n) { return '<button type="button" data-go="' + n[0] + '" class="' + (S.route === n[0] ? "on" : "") + '">' + svg(n[0]) + '<span>' + esc(t(n[1])) + '</span></button>'; }).join("") + '</nav>';
    paintTop();
  }
  function paintTop() {
    if (S.pan) { var d = $("#topDate"), s = $("#topTithi"); if (d) d.textContent = S.pan.date_label; if (s) s.textContent = S.pan.tithi; }
    else { var dd = $("#topDate"); if (dd) dd.textContent = new Date().toLocaleDateString(lang() === "hi" ? "hi-IN" : "en-IN", { weekday: "long", day: "numeric", month: "long" }); }
  }
  function go(route, replace) {
    S.route = route; S.drawer = false; closeDrawer();
    if (location.hash.slice(1) !== route) { if (replace) history.replaceState(null, "", "#" + route); else location.hash = route; }
    shell(); renderView(); loadFor(route); window.scrollTo(0, 0);
  }
  function openDrawer() {
    var el = document.createElement("div"); el.className = "drawer"; el.id = "drawer";
    el.innerHTML = '<div class="sheet"><div class="logo"><img src="/static/icon.svg" alt=""><b>astromuni</b></div><nav class="nav">' + navHtml() + '<button type="button" data-go="compat">' + svg("heart") + '<span class="lbl">' + esc(t("n_compat")) + '</span></button><button type="button" data-go="panchang">' + svg("cal") + '<span class="lbl">' + esc(t("n_panchang")) + '</span></button></nav><div class="push"></div>' + moonCard() + '</div>';
    el.onclick = function (e) { if (e.target === el || e.target.closest("[data-go],[data-act]")) closeDrawer(); };
    document.body.appendChild(el);
  }
  function closeDrawer() { var d = $("#drawer"); if (d) d.remove(); }

  /* ------------------------------------------------------------ views */
  function renderView() {
    var v = $("#view"); if (!v) return;
    var views = { hub: viewHub, ask: viewAsk, horoscope: viewHoro, chart: viewChart, calculators: viewCalc, reports: viewReports, learn: viewLearn, compat: viewCompat, panchang: viewPanchang };
    v.innerHTML = (views[S.route] || viewHub)();
    paintTop();
    if (S.route === "ask") { var th = $("#thread"); if (th) th.scrollTop = th.scrollHeight; }
    if (S.route === "compat") mountCompatPicker();
  }
  var skel = '<div class="card"><div class="skeleton"></div><p></p><div class="skeleton"></div></div>';
  var errBox = function (m) { return '<div class="notice">' + esc(m) + ' <button type="button" class="btn link" data-act="retry">' + esc(t("retry")) + '</button></div>'; };

  function greet() { var h = new Date().getHours(); return t(h < 12 ? "gm" : h < 17 ? "ga" : "ge"); }
  function orbit(moonSign) {
    return '<svg class="orbit" viewBox="0 0 300 300" role="img" aria-label="' + esc(t("weather")) + '"><circle class="ring" cx="150" cy="150" r="140"/><circle class="ring d" cx="150" cy="150" r="112"/><circle class="ring" cx="150" cy="150" r="82"/><g class="spin"><circle cx="150" cy="10" r="9" fill="#8a5a37"/><circle cx="48" cy="236" r="6" fill="#d9a93a"/></g><circle cx="150" cy="150" r="58" fill="#fbe9ae" stroke="#d9a93a"/><circle cx="150" cy="150" r="44" fill="#f4d675"/>' +
      '<text x="150" y="152" text-anchor="middle" font-size="40" fill="#6b3a93">' + esc(glyph(moonSign)) + '</text><text x="150" y="182" text-anchor="middle" font-size="10" letter-spacing="3" fill="#6b4a2a">' + esc(signName(moonSign).toUpperCase()) + '</text></svg>';
  }
  function meters(areas) {
    return '<div class="meters">' + (areas || []).map(function (a) {
      return '<div class="meter ' + esc(a.level) + '"><div class="m-head"><b>' + esc(a.label) + '</b><span>' + a.score + '</span></div><div class="bar" role="img" aria-label="' + esc(t("meter_label", { a: a.label, s: a.score })) + '"><i data-w="' + a.score + '"></i></div><p class="small muted">' + esc(a.text) + '</p></div>';
    }).join("") + '</div>';
  }
  function horoWhy(sg) {
    return '<details class="why"><summary>' + esc(t("why_reading")) + '</summary><p class="muted small">' + esc(S.horo.method) + '</p><ul>' + sg.lines.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join("") + '</ul><div class="scroll-x"><table class="t"><thead><tr><th>' + esc(t("planet")) + '</th><th>' + esc(t("house")) + ' (' + esc(t("from_moon")) + ')</th><th>' + esc(t("sign")) + '</th><th></th></tr></thead><tbody>' +
      sg.facts.map(function (f) { return '<tr><td>' + esc(plName(f.planet)) + (f.retrograde ? " ℞" : "") + '</td><td>' + f.house + '</td><td>' + esc(signName(f.sign)) + '</td><td class="' + (f.favourable ? "yes" : "no") + '">' + esc(t(f.favourable ? "fav" : "chall")) + '</td></tr>'; }).join("") + '</tbody></table></div></details>';
  }
  function horoCard(sg, full) {
    if (!sg) return skel;
    return '<div class="card tint horo"><div class="reading"><div class="badge">' + esc(glyph(sg.key)) + '</div><div class="grow"><div class="eyebrow">' + esc(signName(sg.key)) + ' • ' + esc(t("daily_horo")) + '</div><p class="para">' + esc(sg.paragraph || sg.headline) + '</p></div></div>' + meters(sg.areas) + '<p class="small muted">' + esc(t("area_note")) + '</p>' + (full ? horoWhy(sg) : "") + '</div>';
  }
  function viewHub() {
    var mine = S.horo && S.horo.mine, chips = CHIPS[lang()] || CHIPS.en;
    return '<section class="hub-head"><div class="eyebrow">' + esc(greet()) + '</div><h1>' + esc(first() || "") + '</h1></section>' +
      '<section><div class="eyebrow">' + esc(t("today_for_you")) + '</div>' + (S.err_horo && !S.horo ? errBox(S.err_horo) : horoCard(mine)) + '<div class="mt-s"><button type="button" class="btn link" data-go="horoscope">' + esc(t("read_full")) + ' →</button></div></section>' +
      '<section><h2>' + esc(t("hub_ask")) + '</h2><p class="muted mb-s">' + esc(t("hub_ask_sub")) + '</p><form class="askbox" id="hubAsk"><input id="hubQ" type="text" maxlength="500" autocomplete="off" placeholder="' + esc(t("ask_ph")) + '" aria-label="' + esc(t("ask_ph")) + '"><button class="btn" type="submit" aria-label="' + esc(t("ask_muni")) + '">' + svg("send").replace("<svg", '<svg width="20" height="20"') + '</button></form>' +
      '<div class="chips mt-s">' + chips.map(function (c) { return '<button type="button" class="chip" data-q="' + esc(c) + '">' + esc(c) + '</button>'; }).join("") + '</div></section>' +
      '<section><h2>' + esc(t("more_tools")) + '</h2><div class="grid4 tools">' +
      [["chart", "chart", "kundli_t", "kundli_d"], ["compat", "heart", "compat_t", "compat_d"], ["panchang", "cal", "panchang_t", "panchang_d"], ["reports", "reports", "pers_reports", "reports_d"]].map(function (x) { return '<button type="button" class="card flat tool" data-go="' + x[0] + '"><span class="ico">' + svg(x[1]).replace("<svg", '<svg width="24" height="24"') + '</span><h3>' + esc(t(x[2])) + '</h3><p class="small muted">' + esc(t(x[3])) + '</p></button>'; }).join("") + '</div></section>' +
      '<footer class="foot"><span><b>astromuni</b> · ' + esc(t("tagline")) + '</span> <span>' + esc(t("guidance_not_certainty")) + '</span></footer>';
  }
  function signStrip(sel) {
    return '<div class="signs" role="listbox">' + SIGNS.map(function (s) { return '<button type="button" class="sign ' + (s[0] === sel ? "on" : "") + '" data-sign="' + s[0] + '" role="option" aria-selected="' + (s[0] === sel) + '"><span class="g">' + s[3] + '︎</span>' + esc(lang() === "hi" ? s[2] : s[1]) + '</button>'; }).join("") + '</div>';
  }

  function viewHoro() {
    if (!S.horo) return S.err_horo ? errBox(S.err_horo) : skel;
    var sg = S.horo.signs.filter(function (x) { return x.key === S.sel; })[0] || S.horo.signs[0];
    return '<div><div class="eyebrow">' + esc(t("horo_title")) + '</div><h2>' + esc(S.horo.date) + '</h2></div>' + signStrip(sg.key) + horoCard(sg, true);
  }

  /* North Indian chart */
  var POS = { 1: [150, 78], 2: [76, 30], 3: [30, 76], 4: [78, 150], 5: [30, 224], 6: [76, 270], 7: [150, 222], 8: [224, 270], 9: [270, 224], 10: [222, 150], 11: [270, 76], 12: [224, 30] };
  function kundliSvg(c) {
    var li = SIGNS.map(function (s) { return s[0]; }).indexOf(c.lagna), byH = {};
    Object.keys(c.planets || {}).forEach(function (p) { var h = c.planets[p].house; if (h) (byH[h] = byH[h] || []).push(ABBR[p] + (c.planets[p].retrograde ? "ᴿ" : "")); });
    var out = '<svg class="kundli" viewBox="0 0 300 300" role="img" aria-label="' + esc(t("chart_title")) + '"><rect class="ln" x="1" y="1" width="298" height="298"/><path class="ln" d="M1 1L299 299M299 1L1 299M150 1L299 150L150 299L1 150Z"/>';
    for (var h = 1; h <= 12; h++) {
      var p = POS[h], n = ((li + h - 1) % 12) + 1, ps = byH[h] || [];
      out += '<text class="sg' + (h === 1 ? " lag" : "") + '" x="' + p[0] + '" y="' + (p[1] - (ps.length ? 12 : -4)) + '" text-anchor="middle">' + n + '</text>';
      for (var i = 0; i < ps.length; i += 2) out += '<text class="pl" x="' + p[0] + '" y="' + (p[1] + 4 + (i / 2) * 15) + '" text-anchor="middle">' + esc(ps.slice(i, i + 2).join(" ")) + '</text>';
    }
    return out + '</svg>';
  }
  function viewChart() {
    var c = S.chart; if (!c) return S.err_chart ? errBox(S.err_chart) : skel;
    var noHouse = !c.lagna;
    var rows = Object.keys(c.planets || {}).map(function (p) { var x = c.planets[p]; return '<tr><td><b>' + esc(plName(p)) + '</b></td><td>' + esc(signName(x.sign)) + '</td><td>' + (x.house || "—") + '</td><td>' + esc(x.nakshatra || "") + '</td><td>' + (x.retrograde ? esc(t("yes")) : "") + '</td></tr>'; }).join("");
    var d = c.dasha;
    return '<div class="sec-head"><div><div class="eyebrow">' + esc(t("your_chart")) + '</div><h2>' + esc(t("chart_title")) + '</h2><p class="muted">' + esc(S.profile.name) + ' · ' + esc(S.profile.dob) + (S.profile.tob ? " " + esc(S.profile.tob) : "") + ' · ' + esc(S.profile.place) + '</p></div><button type="button" class="btn ghost" data-act="edit">' + esc(t("edit")) + '</button></div>' +
      (noHouse ? '<div class="notice">' + esc(t("needs_time")) + '</div>' : "") +
      '<div class="grid2"><div class="card tint">' + (noHouse ? "" : kundliSvg(c)) + '<p class="small muted center">' + esc(t("chart_note")) + '</p></div><div class="card"><div class="kv">' +
      '<div><span>' + esc(t("lagna")) + '</span><b>' + esc(c.lagna ? signName(c.lagna) : "—") + '</b></div><div><span>' + esc(t("moon")) + '</span><b>' + esc(signName(c.moon.sign)) + (c.moon.pada ? ' · ' + esc(c.moon.nakshatra) + ' ' + c.moon.pada : "") + '</b></div>' +
      (d ? '<div><span>' + esc(t("dasha_now")) + '</span><b>' + esc(plName(d.maha)) + ' – ' + esc(plName(d.antar)) + '</b></div><div><span>' + esc(t("until")) + '</span><b>' + esc(d.antar_end) + '</b></div>' : "") + '</div>' +
      (c.withheld && c.withheld.length ? '<div class="notice mt-m"><b>' + esc(t("withheld_t")) + ':</b> ' + esc(c.withheld.join(", ")) + '</div>' : "") + (c.warnings && c.warnings.length ? '<p class="small muted mt-m">' + esc(c.warnings.join(" ")) + '</p>' : "") +
      '<div class="row mt-m"><button type="button" class="btn" data-act="pandit">' + esc(t("pandit")) + '</button><button type="button" class="btn ghost" data-go="ask">' + esc(t("cta_ask")) + '</button></div></div></div>' +
      '<div class="card"><div class="scroll-x"><table class="t"><thead><tr><th>' + esc(t("planet")) + '</th><th>' + esc(t("sign")) + '</th><th>' + esc(t("house")) + '</th><th>' + esc(t("nakshatra")) + '</th><th>' + esc(t("retro")) + '</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>';
  }

  function viewPanchang() {
    var p = S.pan; if (!p) return S.err_pan ? errBox(S.err_pan) : skel;
    var item = function (k, v) { return '<div class="card flat"><div class="eyebrow">' + esc(k) + '</div><h3>' + esc(v || "—") + '</h3></div>'; };
    return '<div class="sec-head"><div><div class="eyebrow">' + esc(t("vedic_cal")) + '</div><h2>' + esc(t("panchang_t")) + '</h2><p class="muted">' + esc(p.date_label) + ' · ' + esc(p.paksha) + ' · 📍 ' + esc(p.place || "") + '</p></div><button type="button" class="btn ghost" data-act="where">📍 ' + esc(t("f_place")) + '</button></div><div class="grid3">' +
      item(t("tithi"), p.tithi) + item(t("nakshatra"), p.nakshatra + " (" + plName(p.nakshatra_lord) + ")") + item(t("yoga"), p.yoga) + item(t("karana"), p.karana) + item(t("guiding"), plName(p.guiding_planet)) + item(t("focus"), p.focus) +
      item("Sunrise", p.sunrise) + item("Sunset", p.sunset) + item(t("abhijit"), p.abhijit) + item("Rahu Kaal", p.rahu_kaal) + '</div><p class="small muted">' + esc(p.method || "") + '</p>';
  }

  function replyHtml(m) {
    var d = m.data; if (!d) return '<div class="reply"><span class="typing"><i></i><i></i><i></i></span> <span class="muted small">' + esc(t("thinking")) + '</span></div>';
    var more = (d.reasons && d.reasons.length) || (d.evidence && d.evidence.length) || (d.timing && d.timing.length);
    var qr = m.last && d.quick_replies && d.quick_replies.length && !d.safety;
    return '<div class="reply">' + (d.showTitle && d.title ? '<h3>' + esc(d.title) + '</h3>' : "") + '<p class="ans">' + esc(d.answer) + '</p>' + (d.followup_question ? '<p class="fq">' + esc(d.followup_question) + '</p>' : "") +
      (qr ? '<div class="chips qr">' + d.quick_replies.map(function (c) { return '<button type="button" class="chip" data-q="' + esc(c) + '">' + esc(c) + '</button>'; }).join("") + '</div><p class="small muted">' + esc(t("reply_hint")) + '</p>' : "") +
      (d.confidence && d.confidence.level === "low" && d.confidence.why ? '<p class="small note">' + esc(d.confidence.why) + '</p>' : "") +
      (more && !d.safety ? '<details class="why"><summary>' + esc(t("why")) + '</summary>' + (d.reasons && d.reasons.length ? '<div class="eyebrow">' + esc(t("basis")) + '</div><ul>' + d.reasons.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join("") + '</ul>' : "") + (d.timing && d.timing.length ? '<div class="eyebrow">' + esc(t("timing")) + '</div><ul>' + d.timing.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join("") + '</ul>' : "") +
        (d.confidence && d.confidence.level !== "n/a" && d.confidence.why && d.confidence.level !== "low" ? '<p class="small muted">' + esc(t("confidence")) + ': ' + esc(t(d.confidence.level)) + '. ' + esc(d.confidence.why) + '</p>' : "") + (d.evidence && d.evidence.length ? '<div class="eyebrow">' + esc(t("sources")) + '</div><ul>' + d.evidence.map(function (e) { return '<li><b>' + esc(e.title) + '</b> <span class="src">' + (/^https?:\/\//.test(e.url) ? '<a href="' + esc(e.url) + '" target="_blank" rel="noopener noreferrer">' + esc(e.source) + '</a>' : esc(e.source)) + ' · ' + esc(e.licence) + '</span></li>'; }).join("") + '</ul>' : "") +
        (d.caveats && d.caveats.length ? '<p class="small muted">' + esc(d.caveats.join(" ")) + '</p>' : "") + '</details>' : "") + '</div>';
  }
  function threadHtml() {
    if (!S.msgs.length) {
      var chips = CHIPS[lang()] || CHIPS.en;
      return '<div class="welcome"><h3>' + esc(t("astro_hello", { n: first() })) + '</h3><p class="muted">' + esc(t("astro_hello_sub")) + '</p><div class="eyebrow mt-m">' + esc(t("try_tap")) + '</div><div class="chips">' + chips.map(function (c) { return '<button type="button" class="chip" data-q="' + esc(c) + '">' + esc(c) + '</button>'; }).join("") + '</div></div>';
    }
    var n = S.msgs.length;
    return S.msgs.map(function (m, i) { if (m.role === "user") return '<div class="bubble">' + esc(m.text) + '</div>'; m.last = i === n - 1; return replyHtml(m); }).join("");
  }
  function viewAsk() {
    return '<div class="chatpage"><div class="chat"><div class="chat-head"><span class="av">AM</span><div><b>AstroMuni</b><small class="muted">' + esc(S.chart && S.chart.moon ? t("moon_sign") + ': ' + signName(S.chart.moon.sign) : t("private")) + '</small></div></div><div class="thread" id="thread">' + threadHtml() + '</div>' +
      '<div class="composer"><form class="askbox" id="askForm"><input id="askQ" type="text" maxlength="500" autocomplete="off" placeholder="' + esc(t("ask_ph")) + '" aria-label="' + esc(t("ask_ph")) + '"><button class="btn" type="submit" aria-label="' + esc(t("ask_muni")) + '">' + svg("send").replace("<svg", '<svg width="20" height="20"') + '</button></form><p class="disclaimer">' + esc(t("disclaimer")) + '</p></div></div></div>';
  }
  async function ask(q) {
    q = (q || "").trim(); if (!q || S.busy) return;
    var hist = S.msgs.filter(function (x) { return x.role === "user" || x.data; }).slice(-6).map(function (x) { return x.role === "user" ? { role: "user", text: x.text } : { role: "bot", text: x.data.answer || "", topic: x.data.topic || "", expects: x.data.expects || "" }; });
    S.busy = true; S.msgs.push({ role: "user", text: q }); var m = { role: "bot", data: null }; S.msgs.push(m);
    if (S.route !== "ask") go("ask"); else renderView();
    try { m.data = await api("/api/v10/ask", Object.assign(body({ question: q, mode: S.mode, history: hist }), S.mode === "astropedia" ? { profile: null } : {})); }
    catch (e) { m.data = { answer: e.message, title: "", reasons: [], evidence: [], caveats: [], safety: "error" }; }
    S.busy = false; renderView(); var i = $("#askQ"); if (i) i.focus();
  }

  async function runCalc(type) {
    S.calcType = type; S.calc = { loading: true }; renderView();
    try { S.calc = await api("/api/v10/calculator", body({ type: type })); } catch (e) { S.calc = { error: e.message }; }
    renderView();
  }
  function viewCalc() {
    var items = [["moon", "c_moon", "☾"], ["ascendant", "c_asc", "☀︎"], ["nakshatra", "c_nak", "✦"], ["sade_sati", "c_sade", "♄"]], r = S.calc;
    return '<div><div class="eyebrow">' + esc(t("free_calc")) + '</div><h2>' + esc(t("calc_title")) + '</h2></div><div class="grid4">' + items.map(function (c) { return '<button type="button" class="card calc ' + (S.calcType === c[0] ? "tint" : "flat") + '" data-calc="' + c[0] + '"><span class="tool"><span class="ico">' + c[2] + '</span></span><span><h4>' + esc(t(c[1])) + '</h4><p class="small muted">' + esc(t(c[1] + "_d")) + '</p></span></button>'; }).join("") + '</div>' +
      (!r || r.loading ? skel : r.error ? errBox(r.error) : '<div class="card tint"><div class="eyebrow">' + esc(r.calculator || "") + '</div><h2>' + esc(r.headline) + '</h2><p class="muted">' + esc(r.subline || "") + '</p><p class="mt-m">' + esc(r.summary || "") + '</p>' + ((r.highlights || []).length ? '<ul>' + r.highlights.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul>' : "") + '</div>');
  }

  async function runReport(topic) {
    S.repTopic = topic; S.rep = { loading: true }; renderView();
    try { S.rep = await api("/api/v10/report", body({ topic: topic })); } catch (e) { S.rep = { error: e.message }; }
    renderView();
  }
  function viewReports() {
    var r = S.rep;
    return '<div><div class="eyebrow">' + esc(t("pers_reports")) + '</div><h2>' + esc(t("report_title")) + '</h2><p class="muted">' + esc(t("reports_d")) + '</p></div><div class="chips">' + TOPICS.map(function (k) { return '<button type="button" class="chip ' + (S.repTopic === k ? "on" : "") + '" data-rep="' + k + '">' + esc(t("r_" + k)) + '</button>'; }).join("") + '</div>' +
      (!r || r.loading ? skel : r.error ? errBox(r.error) : '<div class="card tint">' + replyHtml({ data: Object.assign({}, r, { title: t("r_" + S.repTopic), showTitle: true, followup_question: "", quick_replies: [] }) }) + '</div>' + (r.houses && r.houses.length ? '<details class="card flat why"><summary>' + esc(t("why")) + '</summary><div class="scroll-x"><table class="t"><thead><tr><th>' + esc(t("house")) + '</th><th>' + esc(t("sign")) + '</th><th>Lord</th><th></th></tr></thead><tbody>' + r.houses.map(function (h) { return '<tr><td>' + h.house + '</td><td>' + esc(signName(h.sign)) + '</td><td>' + esc(plName(h.lord)) + '</td><td class="' + (h.points > 0 ? "yes" : h.points < 0 ? "no" : "") + '">' + (h.points > 0 ? esc(t("fav")) : h.points < 0 ? esc(t("chall")) : "") + '</td></tr>'; }).join("") + '</tbody></table></div></details>' : ""));
  }

  async function runLearn(q) {
    S.learnQ = q; S.learn = { loading: true }; if (S.route !== "learn") go("learn"); else renderView();
    try { S.learn = await api("/api/v10/ask", { question: q, lang: lang(), mode: "astropedia" }); } catch (e) { S.learn = { error: e.message }; }
    renderView();
  }
  function viewLearn() {
    var r = S.learn;
    return '<div><div class="eyebrow">' + esc(t("n_learn")) + '</div><h2>' + esc(t("learn_title")) + '</h2><p class="muted">' + esc(t("learn_sub")) + '</p></div><form class="askbox" id="learnForm"><input id="learnQ" type="text" maxlength="200" value="' + esc(S.learnQ) + '" placeholder="' + esc(t("learn_ph")) + '" aria-label="' + esc(t("learn_ph")) + '"><button class="btn" type="submit" aria-label="' + esc(t("search")) + '">' + svg("search").replace("<svg", '<svg width="20" height="20"') + '</button></form>' +
      '<div class="chips">' + LEARN.map(function (x) { return '<button type="button" class="chip" data-learn="' + esc(x[1]) + '">' + esc(x[0]) + '</button>'; }).join("") + '</div>' +
      (!r ? "" : r.loading ? skel : r.error ? errBox(r.error) : '<div class="card tint">' + replyHtml({ data: Object.assign({}, r, { confidence: null }) }) + '</div>');
  }

  /* compatibility */
  var partnerPick = null;
  function viewCompat() {
    var r = S.compat, f = S.partner || { name: "", dob: "", tob: "", time_certainty: "exact" };
    return '<div><div class="eyebrow">' + esc(t("relationships")) + '</div><h2>' + esc(t("compat_title")) + '</h2><p class="muted">' + esc(t("compat_d")) + '</p></div><form class="card" id="compatForm" novalidate><h3 class="mb-s">' + esc(t("partner")) + '</h3><div class="form-grid"><label class="field"><span>' + esc(t("p_name")) + '</span><input id="cpName" type="text" maxlength="60" value="' + esc(f.name) + '"></label><label class="field"><span>' + esc(t("f_dob")) + '</span><input id="cpDob" type="date" value="' + esc(f.dob) + '"></label>' +
      '<label class="field"><span>' + esc(t("f_cert")) + '</span><select id="cpCert">' + ["exact", "approx_15min", "part_of_day", "unknown"].map(function (c) { return '<option value="' + c + '"' + (f.time_certainty === c ? " selected" : "") + '>' + esc(t("cert_" + c)) + '</option>'; }).join("") + '</select></label><label class="field"><span>' + esc(t("f_tob")) + '</span><input id="cpTob" type="time" value="' + esc(f.tob || "") + '"></label><div class="full" id="cpPlace"></div></div><p class="err" id="cpErr"></p><button class="btn mt-m" type="submit">' + esc(t("calc_btn")) + '</button></form>' +
      (!r ? "" : r.loading ? skel : !r.ok ? errBox(r.error || r.message || "") : compatResult(r));
  }
  function compatResult(r) {
    return '<div class="card tint"><div class="row between"><div><div class="eyebrow">' + esc(r.person_a.name || t("you")) + ' & ' + esc(r.person_b.name) + '</div><div class="big">' + r.total + '<small class="muted"> / 36</small></div><p class="muted">' + esc(r.band) + ' · ' + r.percent + '%</p></div></div><div class="mt-m">' +
      r.kootas.map(function (k) { return '<div class="koota"><b>' + esc(k.name) + (k.exact ? "" : ' <span class="chip">' + esc(t("approx")) + '</span>') + '</b><span>' + k.obtained + ' / ' + k.max + '</span><span class="note small muted">' + esc(k.note) + '</span></div>'; }).join("") + '</div>' + r.notes.map(function (n) { return '<p class="small muted mt-s">• ' + esc(n) + '</p>'; }).join("") + '</div>';
  }
  function mountCompatPicker() { if (partnerPick) partnerPick.destroy(); var el = $("#cpPlace"); if (el) partnerPick = AM.placePicker(el, S.partner || null, { noMap: true }); }

  /* ------------------------------------------------------------ modals: settings, where, pandit */
  function modal(html) { var m = $("#amModal"); m.className = "am-overlay dim"; m.innerHTML = html; m.hidden = false; return m; }
  function settingsModal() {
    var m = modal('<div class="win"><h2>' + esc(t("settings")) + '</h2><div class="kv"><div><span>' + esc(t("f_name")) + '</span><b>' + esc(S.profile.name) + '</b></div><div><span>' + esc(t("f_dob")) + '</span><b>' + esc(S.profile.dob) + '</b></div><div><span>' + esc(t("f_tob")) + '</span><b>' + esc(S.profile.tob || "—") + '</b></div><div><span>' + esc(t("f_place")) + '</span><b>' + esc(S.profile.place) + '</b></div></div>' +
      '<p class="eyebrow mt-m">' + esc(t("change_lang")) + '</p><div class="seg">' + AM.langs.map(function (l) { return '<button type="button" data-l="' + l[0] + '" class="' + (lang() === l[0] ? "on" : "") + '">' + esc(l[1]) + '</button>'; }).join("") + '</div>' +
      '<div class="actions"><button type="button" class="btn" data-act="edit">' + esc(t("edit")) + '</button><button type="button" class="btn ghost" data-act="pandit">' + esc(t("pandit")) + '</button></div><div class="actions"><button type="button" class="btn ghost" data-act="reset">' + esc(t("reset")) + '</button><button type="button" class="btn link" data-act="close">' + esc(t("close")) + '</button></div></div>');
    m.onclick = function (e) {
      var l = e.target.closest("[data-l]"); if (l) { AM.setLang(l.dataset.l); AM.store.set("astromuni_lang", l.dataset.l, true); save(!!localStorage.getItem(KEY)); S.loaded = {}; AM.closeModal(); go(S.route, true); return; }
      var a = e.target.closest("[data-act]"); if (!a) { if (e.target === m) AM.closeModal(); return; } act(a.dataset.act);
    };
  }
  function whereModal() {
    var m = modal('<div class="win wide"><h2>' + esc(t("f_place")) + '</h2><div id="whPick"></div><div class="actions"><button type="button" class="btn ghost" data-act="close">' + esc(t("cancel")) + '</button><button type="button" class="btn" id="whSave">' + esc(t("save")) + '</button></div></div>');
    var pk = AM.placePicker($("#whPick", m), S.where ? { place: S.where.name, lat: S.where.lat, lon: S.where.lon, tz: S.where.tz } : null, {});
    $("#whSave", m).onclick = function () { var p = pk.get(); if (p.lat == null || !p.tz) return; S.where = { name: p.place, lat: p.lat, lon: p.lon, tz: p.tz }; pk.destroy(); AM.closeModal(); S.loaded.pan = null; load("pan"); };
    m.onclick = function (e) { if (e.target.closest('[data-act="close"]')) { pk.destroy(); AM.closeModal(); } };
  }
  function panditModal() {
    var minor = (Date.now() - new Date(S.profile.dob).getTime()) / 3.156e10 < 18, hasP = S.palms.left && S.palms.right;
    var m = modal('<div class="win"><h2>' + esc(t("pandit")) + '</h2><p class="lead">' + esc(t("pandit_d")) + '</p>' + (minor ? '<div class="notice">Guardian consent is needed for under-18 profiles, so pandit requests are off here.</div>' :
      '<form id="pdForm" novalidate><div class="form-grid"><label class="field full"><span>' + esc(t("phone")) + '</span><input id="pdPhone" type="tel" inputmode="tel" placeholder="+91…"></label><label class="field"><span>' + esc(t("slot")) + '</span><select id="pdSlot">' + [["morning", "s_morning"], ["afternoon", "s_afternoon"], ["evening", "s_evening"], ["anytime", "s_anytime"]].map(function (s) { return '<option value="' + s[0] + '">' + esc(t(s[1])) + '</option>'; }).join("") + '</select></label><label class="field"><span>' + esc(t("about_what")) + '</span><select id="pdTopic">' + ["career", "marriage", "wealth", "education", "children", "other"].map(function (s) { return '<option value="' + s + '">' + esc(s === "other" ? "…" : t("r_" + s)) + '</option>'; }).join("") + '</select></label><label class="field full"><span>' + esc(t("note_opt")) + '</span><textarea id="pdNote" maxlength="300" rows="2"></textarea></label></div>' +
      '<label class="check mt-m"><input type="checkbox" id="pdShare"><span>' + esc(t("share_birth")) + '</span></label>' + (hasP ? '<label class="check mt-s"><input type="checkbox" id="pdPalms"><span>' + esc(t("share_palms")) + '</span></label>' : "") + '<p class="err" id="pdErr"></p><div class="actions"><button type="button" class="btn ghost" data-act="close">' + esc(t("cancel")) + '</button><button type="submit" class="btn">' + esc(t("send")) + '</button></div></form>') + '</div>');
    m.onclick = function (e) { if (e.target.closest('[data-act="close"]') || e.target === m) AM.closeModal(); };
    var f = $("#pdForm", m); if (!f) return;
    f.onsubmit = async function (e) {
      e.preventDefault(); var err = $("#pdErr", m), p = S.profile, pal = hasP && $("#pdPalms", m) && $("#pdPalms", m).checked;
      try {
        var st = await api("/api/start", { name: p.name, date: p.dob, time: p.tob, certainty: p.time_certainty, place: p.place, lat: p.lat, lon: p.lon, tz: p.tz, who: "adult", gender: p.gender === "other" ? "prefer_not_to_say" : p.gender, consent: false,
          palms: pal ? { left: S.palms.left.split(",")[1], right: S.palms.right.split(",")[1] } : undefined });
        var r = await api("/api/pandit-request", { session: st.session, phone: $("#pdPhone", m).value, slot: $("#pdSlot", m).value, topic: $("#pdTopic", m).value, note: $("#pdNote", m).value, share_details: $("#pdShare", m).checked, share_palms: !!pal });
        AM.closeModal(); AM.toast(t("sent", { ref: r.ref }), 6000);
      } catch (ex) { err.textContent = ex.message; }
    };
  }
  function editDetails() {
    AM.closeModal(); AM.runOnboarding({ profile: S.profile, palms: S.palms, startAt: "details", onCancel: function () {}, onDone: function (r) { applyProfile(r); go(S.route, true); } });
  }
  function applyProfile(r) { S.profile = r.profile; S.palms = r.palms || {}; S.chart = r.chart; S.loaded = {}; S.horo = S.pan = S.calc = S.rep = S.compat = null; S.sel = null; S.msgs = []; save(r.remember); }

  function act(a) {
    if (a === "settings") settingsModal();
    else if (a === "drawer") openDrawer();
    else if (a === "close") AM.closeModal();
    else if (a === "edit") editDetails();
    else if (a === "pandit") panditModal();
    else if (a === "where") whereModal();
    else if (a === "retry") { S.loaded = {}; renderView(); loadFor(S.route); }
    else if (a === "reset") { resetAll(); AM.closeModal(); location.hash = ""; start(); }
  }

  /* ------------------------------------------------------------ events */
  document.addEventListener("click", function (e) {
    var el;
    if ((el = e.target.closest("[data-go]"))) { e.preventDefault(); return go(el.dataset.go); }
    if ((el = e.target.closest("[data-act]")) && !e.target.closest("#amModal")) return act(el.dataset.act);
    if ((el = e.target.closest("[data-sign]"))) { S.sel = el.dataset.sign; return renderView(); }
    if ((el = e.target.closest("[data-mode]"))) { S.mode = el.dataset.mode; return renderView(); }
    if ((el = e.target.closest("[data-q]"))) return ask(el.dataset.q);
    if ((el = e.target.closest("[data-calc]"))) { if (S.route !== "calculators") { S.route = "calculators"; shell(); } return runCalc(el.dataset.calc); }
    if ((el = e.target.closest("[data-rep]"))) return runReport(el.dataset.rep);
    if ((el = e.target.closest("[data-learn]"))) return runLearn(el.dataset.learn);
  });
  document.addEventListener("submit", function (e) {
    var id = e.target.id;
    if (id === "hubAsk") { e.preventDefault(); var v = $("#hubQ").value; ask(v); }
    else if (id === "askForm") { e.preventDefault(); var i = $("#askQ"), q = i.value; i.value = ""; ask(q); }
    else if (id === "learnForm") { e.preventDefault(); runLearn($("#learnQ").value); }
    else if (id === "topSearch") { e.preventDefault(); var q2 = $("#topQ").value; if (q2.trim()) runLearn(q2); }
    else if (id === "compatForm") { e.preventDefault(); submitCompat(); }
  });
  async function submitCompat() {
    var err = $("#cpErr"), p = partnerPick ? partnerPick.get() : {}, f = { name: $("#cpName").value.trim(), dob: $("#cpDob").value, tob: $("#cpTob").value, time_certainty: $("#cpCert").value };
    S.partner = Object.assign({}, f, { place: p.place, lat: p.lat, lon: p.lon, tz: p.tz });
    if (!f.name || !f.dob) return err.textContent = t("e_dob");
    if (f.time_certainty !== "unknown" && !f.tob) return err.textContent = t("e_tob");
    if (p.lat == null || !p.tz) return err.textContent = t("e_place");
    var pb = { name: f.name, dob: f.dob, tob: f.time_certainty === "unknown" ? null : f.tob, time_certainty: f.time_certainty, place: p.place, lat: p.lat, lon: p.lon, tz: p.tz, gender: "prefer_not_to_say" };
    S.compat = { loading: true }; renderView(); mountCompatPickerKeep(S.partner);
    try { S.compat = await api("/api/v10/compat", { person_a: S.profile, person_b: pb, lang: lang() }); } catch (ex) { S.compat = { ok: false, error: ex.message }; }
    renderView();
  }
  function mountCompatPickerKeep() { /* the picker re-mounts in renderView with S.partner */ }
  window.addEventListener("hashchange", function () { var r = location.hash.slice(1); if (r && r !== S.route && S.profile) { S.route = r; shell(); renderView(); loadFor(r); } });
  document.addEventListener("transitionend", function () {});
  var obs = new MutationObserver(function () { document.querySelectorAll("[data-w]").forEach(function (b) { if (!b.dataset.d) { b.dataset.d = "1"; requestAnimationFrame(function () { b.style.width = b.dataset.w + "%"; }); } }); });
  obs.observe(document.body, { childList: true, subtree: true });

  /* ------------------------------------------------------------ boot */
  function start() {
    if (!S.profile) {
      AM.setLang(AM.store.get("astromuni_lang") || "en"); $("#amRoot").innerHTML = "";
      return AM.runOnboarding({ onDone: function (r) { applyProfile(r); startApp(); } });
    }
    startApp();
  }
  function startApp() {
    var r = location.hash.slice(1); S.route = /^(hub|ask|horoscope|chart|calculators|reports|learn|compat|panchang)$/.test(r) ? r : "hub";
    shell(); renderView(); loadFor(S.route);
    if (!S.chart) load("chart").then(function () { shell(); });
    else shell();
  }
  (function boot() {
    var raw = AM.store.get(KEY);
    if (raw) { try { var o = JSON.parse(raw); if (o && o.profile && o.profile.lat != null) { S.profile = o.profile; AM.setLang(o.lang || "en"); } } catch (e) { /* corrupt */ } }
    if (!S.profile) AM.setLang(AM.store.get("astromuni_lang") || "en");
    start();
  })();
})();
