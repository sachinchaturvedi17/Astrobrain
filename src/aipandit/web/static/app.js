"use strict";
/* AstroMuni v0.6 front end. No frameworks. Every piece of text goes in with textContent, never innerHTML.
   Flow: details (3 steps) -> hub -> kundli | horoscope | AstroMuni room | real-pandit request.
   The "thinking" pause before an answer is presentation pacing: the engine itself answers in milliseconds. */
(() => {
const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const wrapStore = st => ({ get(k) { try { return st.getItem(k) } catch (e) { return null } }, set(k, v) { try { st.setItem(k, v) } catch (e) {} }, del(k) { try { st.removeItem(k) } catch (e) {} } });
const local = wrapStore(window.localStorage || { getItem() {}, setItem() {}, removeItem() {} });
const sess = wrapStore(window.sessionStorage || { getItem() {}, setItem() {}, removeItem() {} });
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rand = (a, b) => a + Math.random() * (b - a);
const REQUIRE_PALMS = true;                 // set to false to make the two palm photos optional
const THINK_MS = [2200, 3400];              // how long AstroMuni "thinks" before answering
const VIEWS = ["onboard", "making", "hub", "kundli", "horo", "muni", "pandit"];

let LANG = ["hg", "hi", "en"].includes(local.get("astromuni.lang")) ? local.get("astromuni.lang") : "hg";
let SESSION = null, CHART = null, PROFILE = null, VIEW = "onboard", STEP = 1;
const PALMS = { left: null, right: null };
const HORO = {};
const t = k => window.COPY[LANG][k];
const fmt = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => (o[k] != null ? o[k] : ""));
const planet = g => t("planets")[g] || g;
const signName = x => (x ? (window.SIGNS[LANG][x] || x) : "");

// ------------------------------------------------------------------------------------------ DOM helpers
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in attrs || {}) { if (k === "class") e.className = attrs[k]; else if (attrs[k] !== false && attrs[k] != null) e.setAttribute(k, attrs[k]); }
  kids.flat().forEach(c => { if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(c)); });
  return e;
}
function s(tag, attrs, text) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  return e;
}
function svgIcon(paths, extra) {
  const v = s("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" });
  paths.forEach(d => v.appendChild(s("path", { d })));
  (extra || []).forEach(e => v.appendChild(e));
  return v;
}
const ICON = {
  kundli: () => svgIcon(["M4 4h16v16H4z", "M4 4l16 16M20 4L4 20", "M12 4l8 8-8 8-8-8z"]),
  horo: () => svgIcon(["M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"], [s("circle", { cx: 12, cy: 12, r: 4 })]),
  muni: () => svgIcon(["M5 21c0-4 3-7 7-7s7 3 7 7", "M7.2 4.6a6.2 6.2 0 0 1 9.6 0"], [s("circle", { cx: 12, cy: 9, r: 3.4 })]),
  pandit: () => svgIcon(["M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6", "M15.2 14.3c3 0 5.3 2 5.3 5.7"], [s("circle", { cx: 9, cy: 8, r: 3 }), s("circle", { cx: 17, cy: 9, r: 2.4 })]),
  go: () => svgIcon(["M5 12h14M13 6l6 6-6 6"])
};
const GLYPH = {
  kundli: () => svgIcon(["M4 4h16v16H4z", "M12 4l8 8-8 8-8-8z"]),
  numerology: () => { const v = s("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" }); for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) v.appendChild(s("circle", { cx: 5 + c * 7, cy: 5 + r * 7, r: 1.9, class: "fill" })); return v; },
  both: () => { const v = s("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" }); v.appendChild(s("circle", { cx: 9, cy: 12, r: 6 })); v.appendChild(s("circle", { cx: 15, cy: 12, r: 6 })); return v; }
};
async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: "unexpected response" }));
  if (!r.ok) { const e = new Error(j.error || "request failed"); e.status = r.status; e.alternatives = j.alternatives || []; throw e; }
  return j;
}

// ------------------------------------------------------------------------------------------ language
const CITIES = [["Bhopal", 23.2599, 77.4126], ["Delhi", 28.6139, 77.2090], ["Mumbai", 19.0760, 72.8777], ["Kolkata", 22.5726, 88.3639], ["Chennai", 13.0827, 80.2707],
  ["Bengaluru", 12.9716, 77.5946], ["Hyderabad", 17.3850, 78.4867], ["Jaipur", 26.9124, 75.7873], ["Indore", 22.7196, 75.8577], ["Lucknow", 26.8467, 80.9462], [null, null, null]];
function fillSelect(sel, opts) { const v = sel.value; sel.replaceChildren(); opts.forEach(([val, label]) => sel.appendChild(h("option", { value: val }, label))); if (v) sel.value = v; }
function setLang(l) {
  LANG = l; local.set("astromuni.lang", l);
  document.documentElement.lang = l === "hi" ? "hi" : l === "hg" ? "hi-Latn" : "en";
  document.querySelectorAll("#langSeg button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === l)));
  document.querySelectorAll("[data-i]").forEach(n => { const v = t(n.dataset.i); if (typeof v === "string") n.textContent = v; });
  document.querySelectorAll("[data-ph]").forEach(n => { n.placeholder = t(n.dataset.ph); });
  fillSelect($("cert"), t("certs")); fillSelect($("gender"), t("genders")); fillSelect($("who"), t("whos"));
  fillSelect($("slot"), t("slots")); fillSelect($("topic"), t("topics"));
  const keep = $("city").value; $("city").replaceChildren();
  CITIES.forEach((c, i) => $("city").appendChild(h("option", { value: i }, c[0] || t("otherCity")))); $("city").value = keep || "0";
  $("obPoints").replaceChildren(...t("obPoints").map(x => h("li", null, x)));
  $("palmTips").replaceChildren(...t("palmTips").map(x => h("li", null, x)));
  setStep(STEP); renderStars();
  $("mRole").textContent = t("mRole"); setState(document.getElementById("stage").dataset.state || "idle");
  $("askBtn").setAttribute("aria-label", t("send"));
  if (SESSION) (RENDER[VIEW] || (() => {}))();
  renderChips();
}
document.querySelectorAll("#langSeg button").forEach(b => b.addEventListener("click", () => setLang(b.dataset.lang)));

// ------------------------------------------------------------------------------------------ router
const RENDER = {};
function show(v, push = true) {
  if (!SESSION && v !== "onboard") v = "onboard";
  VIEW = v;
  VIEWS.forEach(n => { $("v-" + n).hidden = n !== v; });
  document.body.dataset.view = v;
  $("homeBtn").hidden = !(SESSION && !["hub", "onboard", "making"].includes(v));
  document.querySelectorAll(".fbopen").forEach(b => { b.hidden = !SESSION || ["onboard", "making"].includes(v); });
  if (push && v !== "making") { try { history.pushState({ v }, "", "#" + v); } catch (e) {} }
  if (RENDER[v]) RENDER[v]();
  window.scrollTo(0, 0);
  const view = $("v-" + v), hd = view.querySelector("h1");
  if (v === "muni") $("q").focus({ preventScroll: true });
  else if (hd) { hd.tabIndex = -1; hd.focus({ preventScroll: true }); }
}
window.addEventListener("popstate", e => {
  const v = (e.state && e.state.v) || location.hash.slice(1) || "onboard";
  show(VIEWS.includes(v) && v !== "making" ? v : (SESSION ? "hub" : "onboard"), false);
});
document.addEventListener("click", e => { const b = e.target.closest("[data-go]"); if (b) show(b.dataset.go); });
$("brandBtn").addEventListener("click", () => show(SESSION ? "hub" : "onboard"));
$("homeBtn").addEventListener("click", () => show("hub"));

// ------------------------------------------------------------------------------------------ 1. details wizard
function syncCity() { const c = CITIES[$("city").value]; const other = c[1] === null; $("coords").hidden = !other; if (!other) { $("lat").value = c[1]; $("lon").value = c[2]; } }
$("city").addEventListener("change", syncCity);
$("cert").addEventListener("change", () => { $("time").disabled = $("cert").value === "unknown"; });
$("date").max = new Date().toISOString().slice(0, 10);

function setStep(n) {
  STEP = n;
  document.querySelectorAll("fieldset.step").forEach(f => { f.hidden = Number(f.dataset.step) !== n; });
  $("progBar").style.width = Math.round((n / 3) * 100) + "%";
  $("stepOf").textContent = fmt(t("stepOf"), { n });
  $("backStep").hidden = n === 1;
  const btn = $("nextStep"); if (!btn.disabled) btn.textContent = n === 3 ? t("start") : t("next");
}
function stepError(n) {
  if (n === 1 && $("name").value.trim().length < 2) return ["needName", "name"];
  if (n === 2) {
    if (!$("date").value) return ["needDate", "date"];
    if ($("cert").value !== "unknown" && !$("time").value) return ["needTime", "time"];
  }
  if (n === 3 && REQUIRE_PALMS && !(PALMS.left && PALMS.right)) return ["needPalms", "fileL"];
  return null;
}
$("backStep").addEventListener("click", () => { $("formErr").textContent = ""; setStep(STEP - 1); });

function toJpeg(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file), img = new Image();
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("read")); };
    img.onload = () => {
      try {
        const sc = Math.min(1, 1280 / Math.max(img.naturalWidth, img.naturalHeight)), w = Math.round(img.naturalWidth * sc), hh = Math.round(img.naturalHeight * sc);
        const c = document.createElement("canvas"); c.width = w; c.height = hh;
        const x = c.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, w, hh); x.drawImage(img, 0, 0, w, hh);   // re-encoding also drops camera/GPS metadata
        URL.revokeObjectURL(url);
        let q = 0.85;
        const attempt = () => c.toBlob(b => {
          if (!b) return reject(new Error("read"));
          if (b.size > 480 * 1024 && q > 0.45) { q -= 0.1; return attempt(); }
          if (b.size > 560 * 1024) return reject(new Error("big"));
          const rd = new FileReader();
          rd.onload = () => resolve({ b64: String(rd.result).split(",")[1], url: URL.createObjectURL(b) });
          rd.onerror = () => reject(new Error("read")); rd.readAsDataURL(b);
        }, "image/jpeg", q);
        attempt();
      } catch (e) { reject(new Error("read")); }
    };
    img.src = url;
  });
}
function paintPalm(side) {
  const tile = $(side === "left" ? "palmL" : "palmR"), img = tile.querySelector("img"), p = PALMS[side];
  tile.classList.toggle("has", !!p); img.hidden = !p; if (p) img.src = p.url; else img.removeAttribute("src");
  tile.querySelector(".palm-a").textContent = p ? t("palmChange") : t("palmAdd");
}
[["left", "fileL"], ["right", "fileR"]].forEach(([side, id]) => $(id).addEventListener("change", async ev => {
  const f = ev.target.files && ev.target.files[0]; if (!f) return;
  $("formErr").textContent = "";
  try { PALMS[side] = await toJpeg(f); } catch (e) { $("formErr").textContent = t(e.message === "big" ? "photoBig" : "photoFail"); PALMS[side] = null; }
  paintPalm(side);
}));

$("birth").addEventListener("submit", async ev => {
  ev.preventDefault(); $("formErr").textContent = "";
  const err = stepError(STEP);
  if (err) { $("formErr").textContent = t(err[0]); $(err[1]).focus(); return; }
  if (STEP < 3) { setStep(STEP + 1); const f = document.querySelector(`fieldset[data-step="${STEP}"] .input, fieldset[data-step="${STEP}"] input`); if (f) f.focus({ preventScroll: true }); return; }
  for (const n of [1, 2]) { const e2 = stepError(n); if (e2) { setStep(n); $("formErr").textContent = t(e2[0]); $(e2[1]).focus(); return; } }
  const btn = $("nextStep"); btn.disabled = true; btn.textContent = t("going");
  try {
    const c = CITIES[$("city").value];
    const body = {
      name: $("name").value.trim(), date: $("date").value, time: $("cert").value === "unknown" ? null : ($("time").value || null), certainty: $("cert").value,
      place: c[0] || "Custom", lat: parseFloat($("lat").value), lon: parseFloat($("lon").value), tz: $("tz").value.trim(),
      gender: $("gender").value, who: $("who").value, consent: $("consent").checked };
    if (PALMS.left && PALMS.right) body.palms = { left: PALMS.left.b64, right: PALMS.right.b64 };
    const j = await post("/api/start", body);
    adopt(j); sess.set("astromuni.sid", SESSION);
    await ceremony();
    show("hub");
  } catch (e) {
    $("formErr").textContent = e.message + (e.alternatives && e.alternatives.length ? "\n• " + e.alternatives.join("\n• ") : "");
    if (VIEW === "making") show("onboard", false);
  } finally { btn.disabled = false; btn.textContent = STEP === 3 ? t("start") : t("next"); }
});
function adopt(j) { SESSION = j.session; CHART = j.chart; PROFILE = j.profile; for (const k in HORO) delete HORO[k]; }
async function ceremony() {
  show("making", false);
  const lines = t("making"), el = $("makingText"), step = reduced() ? 500 : 900;
  for (let i = 0; i < lines.length; i++) { el.textContent = lines[i]; await sleep(i === lines.length - 1 ? step : step + 100); }
}

// ------------------------------------------------------------------------------------------ 3. hub
RENDER.hub = () => {
  const n = PROFILE && PROFILE.first_name;
  $("hubTitle").textContent = n ? fmt(t("hello"), { n }) : t("helloAnon");
  const pills = [];
  if (CHART.lagna_sign) pills.push([t("chipLagna"), signName(CHART.lagna_sign)]);
  if (CHART.moon && CHART.moon.sign) pills.push([t("chipMoon"), signName(CHART.moon.sign)]);
  const N = CHART.numbers || {};
  if (N.mulank) pills.push([t("chipMulank"), String(N.mulank.value)]);
  if (N.bhagyank) pills.push([t("chipBhagyank"), String(N.bhagyank.value)]);
  $("profileChips").replaceChildren(...pills.map(([a, b]) => h("li", { class: "pill" }, h("span", null, a), h("b", null, b))));
  const C = t("cards");
  const mk = (key, view, cls) => {
    const b = h("button", { class: "tool " + (cls || ""), type: "button", "data-open": view },
      h("span", { class: "ic" }, ICON[key === "horo" ? "horo" : key]()), h("h2", null, C[key][0]), h("p", null, C[key][1]), h("span", { class: "tag" }, C[key][2]), h("span", { class: "go" }, ICON.go()));
    b.addEventListener("click", () => show(view)); return b;
  };
  $("hubCards").replaceChildren(mk("kundli", "kundli"), mk("horo", "horo"), mk("muni", "muni", "feature"), mk("pandit", "pandit"));
};

// ------------------------------------------------------------------------------------------ 4. kundli
const HOUSES = [[1, "200,0 300,100 200,200 100,100", [200, 100], [200, 152]], [2, "0,0 200,0 100,100", [100, 38], [100, 72]], [3, "0,0 100,100 0,200", [36, 100], [64, 100]],
  [4, "0,200 100,100 200,200 100,300", [100, 200], [100, 236]], [5, "0,200 100,300 0,400", [36, 300], [64, 300]], [6, "0,400 100,300 200,400", [100, 362], [100, 330]],
  [7, "200,400 100,300 200,200 300,300", [200, 300], [200, 352]], [8, "200,400 300,300 400,400", [300, 362], [300, 330]], [9, "400,400 300,300 400,200", [364, 300], [336, 300]],
  [10, "400,200 300,300 200,200 300,100", [300, 200], [300, 236]], [11, "400,200 300,100 400,0", [364, 100], [336, 100]], [12, "400,0 300,100 200,0", [300, 38], [300, 72]]];
const ABBR = { latin: { Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke" },
               hi: { Sun: "सू", Moon: "चं", Mars: "मं", Mercury: "बु", Jupiter: "गु", Venus: "शु", Saturn: "श", Rahu: "रा", Ketu: "के" } };
const KENDRA = n => n === 1 || n === 4 || n === 7 || n === 10;
function drawChart(ch) {
  const box = $("chartBox"); box.replaceChildren();
  if (ch.lagna_index === null || ch.lagna_index === undefined) { box.appendChild(h("p", { class: "warn" }, t("noLagna"))); return; }
  const ab = LANG === "hi" ? ABBR.hi : ABBR.latin;
  const svg = s("svg", { viewBox: "-3 -3 406 406", role: "img", "aria-label": t("chartTitle") + ": " + t("lagna") + " " + signName(ch.lagna_sign) });
  HOUSES.forEach(([n, pts]) => svg.appendChild(s("polygon", { points: pts, class: "ln" + (n === 1 ? " h1" : "") })));
  const by = {}; ch.planets.forEach(p => { if (p.house) (by[p.house] = by[p.house] || []).push(p); });
  HOUSES.forEach(([n, , pa, sa]) => {
    svg.appendChild(s("text", { x: sa[0], y: sa[1] + 4, class: "sg", "text-anchor": "middle" }, String(((ch.lagna_index + n - 1) % 12) + 1)));
    const ps = by[n] || [], cols = !KENDRA(n) ? 1 : (ps.length > 3 ? 2 : 1), rows = Math.ceil(ps.length / cols);
    ps.forEach((p, i) => {
      const row = Math.floor(i / cols), col = i % cols;
      const x = pa[0] + (cols === 2 ? (col ? 17 : -17) : 0), y = pa[1] + 5 + row * 17 - (rows - 1) * 8.5;
      const txt = s("text", { x, y, class: "pl", "text-anchor": "middle" }, ab[p.name]);
      if (p.retrograde) txt.appendChild(s("tspan", { dy: "-5", "font-size": "9" }, "R"));
      svg.appendChild(txt);
    });
  });
  box.appendChild(svg);
}
RENDER.kundli = () => {
  const ch = CHART;
  drawChart(ch);
  const facts = [];
  if (ch.lagna_sign) facts.push([t("lagna"), signName(ch.lagna_sign)]);
  if (ch.moon && ch.moon.sign) facts.push([t("moon"), signName(ch.moon.sign)]);
  if (ch.moon && ch.moon.nakshatra) facts.push([t("nak"), ch.moon.nakshatra + (ch.moon.pada ? " (" + ch.moon.pada + ")" : "")]);
  if (ch.sun_sign) facts.push([t("sun"), signName(ch.sun_sign)]);
  $("keyFacts").replaceChildren(...facts.flatMap(([a, b]) => [h("dt", null, a), h("dd", null, b)]));
  const tb = $("planets"); tb.replaceChildren();
  tb.appendChild(h("tr", null, ...["thGraha", "thSign", "thHouse", "thNak"].map(k => h("th", { scope: "col" }, t(k)))));
  ch.planets.forEach(p => tb.appendChild(h("tr", null, h("td", null, planet(p.name) + (p.retrograde ? " (R)" : "")), h("td", null, p.sign ? signName(p.sign) : "—"), h("td", null, p.house || "—"), h("td", null, p.nakshatra || "—"))));
  const d = ch.dasha, now = $("dashaNow");
  now.textContent = d ? t("dashaMain") + ": " + planet(d.maha_lord) + " " + t("until") + " " + d.maha_end + (d.antar_lord ? "  ·  " + t("dashaSub") + ": " + planet(d.antar_lord) + " " + t("until") + " " + d.antar_end : "") : t("noDasha");
  const tl = $("timeline"); tl.replaceChildren();
  (ch.timeline || []).forEach(m => {
    const past = !m.current && m.end <= new Date().toISOString().slice(0, 10);
    tl.appendChild(h("li", { class: m.current ? "now" : past ? "past" : "" }, h("b", null, planet(m.lord)), h("span", null, m.start.slice(0, 4) + " – " + m.end.slice(0, 4)), m.current ? h("span", null, t("dashaNow")) : null));
  });
  const cur = tl.querySelector(".now"); if (cur) setTimeout(() => cur.scrollIntoView({ inline: "center", block: "nearest" }), 60);
  const nums = $("nums"); nums.replaceChildren();
  const N = ch.numbers || {};
  ["mulank", "bhagyank", "name_number", "personal_year"].forEach(k => { if (N[k]) nums.appendChild(h("div", { class: "num" }, h("span", { class: "nm" }, t("nums")[k]), h("span", { class: "dg" }, String(N[k].value)), h("span", { class: "pn" }, planet(N[k].planet)))); });
  $("numsSect").hidden = !nums.children.length;
  const notes = []; if (ch.time_uncertain) notes.push(t("uncertain")); (ch.warnings || []).forEach(w => notes.push(w));
  $("kWarn").textContent = notes.join(" ");
};
$("printBtn").addEventListener("click", () => window.print());

// ------------------------------------------------------------------------------------------ shared reading blocks
function lensLabel(l) { return l === "numerology" ? t("lensNum") : l === "both" ? t("lensBoth") : t("lensKundli"); }
function splitLead(text) {            // presentation only: the first sentence becomes a heading-weight lead, the text itself is unchanged
  let depth = 0;
  for (let i = 0; i < text.length - 2; i++) {
    const ch = text[i];
    if (ch === "(") depth++; else if (ch === ")") depth = Math.max(0, depth - 1);
    else if (depth === 0 && (ch === "." || ch === ":") && text[i + 1] === " " && i >= 12 && i <= 130) return [text.slice(0, i + 1), text.slice(i + 2)];
  }
  return [text, ""];
}
function readingBlock(st, showLens, lensTag) {
  const lens = st.lens || "kundli";
  const box = h("div", { class: "rd" + (lens === "both" ? " bridge" : "") });
  if (showLens && (lens !== lensTag.last || lens === "both")) box.appendChild(h("div", { class: "lens " + lens }, GLYPH[lens](), lensLabel(lens)));
  lensTag.last = lens;
  const p = h("p", { class: "rd-text" });
  if (st.kind === "reading") { const [a, b] = splitLead(st.text); p.append(h("strong", null, a)); if (b) p.append(" " + b); } else p.append(st.text);
  if (st.label) p.appendChild(h("span", { class: "tag" }, st.label));
  box.appendChild(p);
  if (st.basis && st.basis.length) box.appendChild(h("details", { class: "why" }, h("summary", null, t("why")), h("ul", null, st.basis.map(b => h("li", null, b)))));
  return box;
}
const countLenses = sts => new Set(sts.filter(x => x.kind !== "framing" && x.kind !== "caveat").map(x => x.lens || "kundli")).size;
function thumb(up) {
  const v = s("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" });
  v.appendChild(s("path", { d: up ? "M7 11v9H4v-9zM7 11l4-8c1.5 0 2.5 1.2 2.2 2.7L12.7 9H19a2 2 0 0 1 2 2.4l-1.3 6.5A2 2 0 0 1 17.7 20H7" : "M17 13V4h3v9zM17 13l-4 8c-1.5 0-2.5-1.2-2.2-2.7l.5-3.3H5a2 2 0 0 1-2-2.4l1.3-6.5A2 2 0 0 1 6.3 4H17" }));
  return v;
}
function feedbackRow(answerId, ask) {
  const wrap = h("div", { class: "fb" });
  const up = h("button", { class: "th", type: "button", "aria-pressed": "false", "aria-label": t("up"), title: t("up") }, thumb(true));
  const dn = h("button", { class: "th", type: "button", "aria-pressed": "false", "aria-label": t("down"), title: t("down") }, thumb(false));
  const more = h("div", { class: "fb-more", hidden: "" });
  const ta = h("textarea", { class: "input", rows: 2, maxlength: 600, "aria-label": t("fbWhy"), placeholder: t("fbWhy") });
  const send = h("button", { class: "fb-send", type: "button" }, t("fbSend"));
  more.append(ta, send);
  const rate = async which => {
    up.setAttribute("aria-pressed", String(which === "up")); dn.setAttribute("aria-pressed", String(which === "down")); more.hidden = false;
    try { await post("/api/feedback", { session: SESSION, answer_id: answerId, kind: "answer", rating: which }); } catch (e) { /* feedback must never break the page */ }
  };
  up.addEventListener("click", () => rate("up")); dn.addEventListener("click", () => rate("down"));
  send.addEventListener("click", async () => {
    if (!ta.value.trim()) return;
    try { await post("/api/feedback", { session: SESSION, answer_id: answerId, kind: "answer_comment", comment: ta.value.trim() }); } catch (e) {}
    more.replaceChildren(h("span", null, t("fbThanks")));
  });
  wrap.append(h("span", null, ask || t("fbAsk")), up, dn, more);
  return wrap;
}

// ------------------------------------------------------------------------------------------ 5. horoscope
let horoToken = 0;
RENDER.horo = async () => {
  const token = ++horoToken, lang = LANG, body = $("horoBody"), load = $("horoLoad");
  body.replaceChildren();
  let data = HORO[lang];
  if (!data) {
    load.hidden = false;
    const lines = t("hLoad"); let i = 0; $("horoLoadText").textContent = lines[0];
    const tick = setInterval(() => { i = (i + 1) % lines.length; $("horoLoadText").textContent = lines[i]; }, 850);
    try {
      [data] = await Promise.all([post("/api/horoscope", { session: SESSION, lang }), sleep(rand(THINK_MS[0], THINK_MS[1]))]);
      HORO[lang] = data;
    } catch (e) { clearInterval(tick); load.hidden = true; body.appendChild(h("p", { class: "err" }, t("err") + e.message)); return; }
    clearInterval(tick);
  }
  if (token !== horoToken) return;                 // the language or view changed while loading
  load.hidden = true;
  const add = async el => { body.appendChild(el); if (!reduced()) await sleep(380); };
  if (CHART.dasha) {
    const d = CHART.dasha, span = (CHART.timeline || []).find(m => m.current);
    const card = h("section", { class: "card sec now-card" }, h("h2", null, t("nowTitle")),
      h("p", { class: "big" }, fmt(t("nowText"), { m: planet(d.maha_lord), a: d.maha_end }) + (d.antar_lord ? " " + fmt(t("nowSub"), { s: planet(d.antar_lord), b: d.antar_end }) : "")));
    if (span) {
      const a = Date.parse(span.start), b = Date.parse(span.end), pct = Math.max(2, Math.min(100, Math.round(((Date.now() - a) / (b - a)) * 100)));
      const bar = h("div", { class: "bar", "aria-hidden": "true" }, h("span")); bar.firstChild.style.width = pct + "%"; card.appendChild(bar);
    }
    await add(card); if (token !== horoToken) return;
  }
  for (const sec of data.sections) {
    const lensTag = { last: null }, showLens = countLenses(sec.statements) > 1;
    const card = h("section", { class: "card sec" }, h("h2", null, t("areas")[sec.key] || sec.key), ...sec.statements.map(st => readingBlock(st, showLens, lensTag)), feedbackRow(sec.answer_id));
    await add(card); if (token !== horoToken) return;
  }
  const N = CHART.numbers || {};
  if (data.uncovered && data.uncovered.length) body.appendChild(h("p", { class: "note-line" }, fmt(t("uncovered"), { list: data.uncovered.map(k => t("areas")[k] || k).join(", ") })));
  if (data.lang_fallback && t("fallbackHi")) body.appendChild(h("p", { class: "note-line" }, t("fallbackHi")));
  if (data.notes && data.notes.length) body.appendChild(h("section", { class: "sec" }, h("h2", null, t("notesTitle")), h("ul", { class: "notes" }, data.notes.map(n => h("li", null, n)))));
};

// ------------------------------------------------------------------------------------------ 6. AstroMuni room
let busy = false, ASKED = new Set(), TURNS = 0, thinkTimer = null;
function setState(st) { const el = $("stage"); el.dataset.state = st; $("mState").textContent = t("mState")[st] || ""; }
function followBottom(ans) {          // keep the growing answer in view without pushing its first line off the top
  const log = $("log"), r = ans.getBoundingClientRect(), lr = log.getBoundingClientRect();
  const over = r.bottom - (lr.bottom - 12), room = r.top - (lr.top + 8);
  if (over > 0 && room > 0) log.scrollBy({ top: Math.min(over, room), behavior: reduced() ? "auto" : "smooth" });
}
const beat = async () => { if (!reduced()) await sleep(rand(380, 620)); };
function thinkingEl() {
  const txt = h("span", null, t("think")[0]);
  const el = h("div", { class: "thinking", role: "status" }, h("span", { class: "dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")), txt);
  let i = 0; clearInterval(thinkTimer);
  thinkTimer = setInterval(() => { i = (i + 1) % t("think").length; txt.textContent = t("think")[i]; }, 850);
  return el;
}
async function reveal(turn, ans, items) {
  setState("speaking");
  turn.appendChild(ans);
  for (const el of items) { ans.appendChild(el); followBottom(ans); await beat(); }
}
function answerItems(j) {
  const items = [], sts = j.statements, showLens = countLenses(sts) > 1, lensTag = { last: null }, caveats = [];
  sts.forEach(st => {
    if (st.kind === "framing") items.push(h("p", { class: "intro" }, st.text));
    else if (st.kind === "caveat") caveats.push(st.text);
    else items.push(readingBlock(st, showLens, lensTag));
  });
  if (caveats.length) items.push(h("p", { class: "note-line" }, caveats.join(" ")));
  items.push(feedbackRow(j.answer_id));
  return items;
}
async function ask(q, chipIdx) {
  if (busy || !SESSION) return;
  busy = true; $("askBtn").disabled = true;
  if (chipIdx != null) { ASKED.add(chipIdx); renderChips(); }
  const log = $("log"), turn = h("div", { class: "turn" }, h("div", { class: "q" }, q));
  const th = thinkingEl(); turn.appendChild(th); log.appendChild(turn);
  turn.scrollIntoView({ block: "end", behavior: reduced() ? "auto" : "smooth" });
  setState("thinking");
  try {
    const [j] = await Promise.all([post("/api/chat", { session: SESSION, question: q }), sleep(rand(THINK_MS[0], THINK_MS[1]))]);
    clearInterval(thinkTimer); th.remove();
    const ans = h("div", { class: "ans" });
    await reveal(turn, ans, answerItems(j));
    TURNS++;
    if (TURNS % 3 === 0) { const b = h("button", { class: "btn ghost", type: "button" }, t("panditNudgeBtn")); b.addEventListener("click", () => show("pandit")); ans.appendChild(h("div", { class: "nudge" }, h("span", null, t("panditNudge")), b)); followBottom(ans); }
  } catch (e) {
    clearInterval(thinkTimer); th.remove();
    turn.appendChild(h("div", { class: "ans" }, h("p", { class: "note-line" }, t("err") + e.message)));
  } finally { setState("idle"); busy = false; $("askBtn").disabled = false; $("q").focus({ preventScroll: true }); }
}
RENDER.muni = async () => {
  renderChips(); $("mRole").textContent = t("mRole"); setState($("stage").dataset.state || "idle");
  const log = $("log");
  if (log.children.length) return;
  const n = PROFILE && PROFILE.first_name, turn = h("div", { class: "turn" }), ans = h("div", { class: "ans" });
  log.appendChild(turn);
  await reveal(turn, ans, [h("p", { class: "intro" }, n ? fmt(t("greet"), { n }) : t("greetAnon")), h("p", { class: "rd-text" }, t("greet2"))]);
  setState("idle");
};
function renderChips() {
  const c = $("chips"); c.replaceChildren();
  t("chips").forEach(([label, q], i) => { if (ASKED.has(i)) return; const b = h("button", { class: "chip", type: "button" }, label); b.addEventListener("click", () => ask(q, i)); c.appendChild(b); });
}
$("ask").addEventListener("submit", ev => { ev.preventDefault(); const q = $("q").value.trim(); if (!q) return; $("q").value = ""; ask(q); });

// ------------------------------------------------------------------------------------------ 7. real pandit
RENDER.pandit = () => {
  $("sharePalmsRow").hidden = !(PROFILE && PROFILE.has_palms);
  if (!$("pOk").hidden) return;
  $("pform").hidden = false;
};
$("pform").addEventListener("submit", async ev => {
  ev.preventDefault(); $("pErr").textContent = "";
  const phone = $("phone").value.replace(/[\s\-()]/g, "");
  if (!/^\+?[0-9]{10,13}$/.test(phone)) { $("pErr").textContent = t("pErrPhone"); $("phone").focus(); return; }
  if (!$("shareDetails").checked) { $("pErr").textContent = t("pErrDetails"); $("shareDetails").focus(); return; }
  const btn = $("pSend"); btn.disabled = true; btn.textContent = t("pSending");
  try {
    const j = await post("/api/pandit-request", { session: SESSION, phone, slot: $("slot").value, topic: $("topic").value, note: $("note").value.trim(),
      share_details: true, share_palms: $("sharePalms").checked && !$("sharePalmsRow").hidden });
    $("pOkTitle").textContent = t("pOkTitle"); $("pOkText").textContent = fmt(t("pOkText"), { p: phone, r: j.ref });
    $("pform").hidden = true; $("pOk").hidden = false;
  } catch (e) { $("pErr").textContent = e.message; } finally { btn.disabled = false; btn.textContent = t("pSend"); }
});

// ------------------------------------------------------------------------------------------ overall feedback dialog
let stars = 0;
function renderStars() { const w = $("stars"); w.replaceChildren(); for (let i = 1; i <= 5; i++) { const b = h("button", { type: "button", "aria-pressed": String(stars === i), "aria-label": String(i) }, String(i)); b.addEventListener("click", () => { stars = i; renderStars(); }); w.appendChild(b); } }
document.querySelectorAll(".fbopen").forEach(b => b.addEventListener("click", () => $("fbDlg").showModal()));
$("fbSend").addEventListener("click", async () => {
  try { await post("/api/feedback", { session: SESSION, kind: "session", rating: stars || null, comment: $("fbText").value.trim() }); } catch (e) {}
  $("fbText").value = "";
});

// ------------------------------------------------------------------------------------------ start
(async function init() {
  setLang(LANG); syncCity(); setStep(1);
  const sid = sess.get("astromuni.sid");
  if (sid) {
    try {
      adopt(await post("/api/resume", { session: sid }));
      const want = location.hash.slice(1);
      show(["kundli", "horo", "muni", "pandit"].includes(want) ? want : "hub", false);
      try { history.replaceState({ v: VIEW }, "", "#" + VIEW); } catch (e) {}
      return;
    } catch (e) { sess.del("astromuni.sid"); }
  }
  show("onboard", false);
})();
})();

/* AstroMuni v0.7 intake-first problem-solver enhancement keeping v0.6 visual style */
(() => {
  const getProfileFromDom = () => ({
    name: (document.getElementById("name") && document.getElementById("name").value.trim()) || (window.PROFILE && window.PROFILE.full_name) || "Sachin Chaturvedi",
    dob: (document.getElementById("date") && document.getElementById("date").value) || "2001-01-29",
    tob: (document.getElementById("time") && document.getElementById("time").value) || "09:30",
    city: (document.getElementById("city") && document.getElementById("city").selectedOptions[0] && document.getElementById("city").selectedOptions[0].textContent) || "Bhopal",
    lat: document.getElementById("lat") && document.getElementById("lat").value,
    lon: document.getElementById("lon") && document.getElementById("lon").value,
  });

  function ensureSolverBox() {
    const muniView = document.getElementById("v-muni");
    if (!muniView || document.getElementById("v07SolverBox")) return;
    const talk = muniView.querySelector(".talk");
    if (!talk) return;

    const box = document.createElement("div");
    box.id = "v07SolverBox";
    box.className = "card";
    box.style.margin = "0 clamp(16px,4vw,48px) 12px";
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
        <strong id="v07Heading">Problem Solver (v0.7)</strong>
        <span id="v07Score" class="tag"></span>
      </div>
      <p id="v07Verdict" class="rd-text" style="margin-top:8px;font-weight:600;"></p>
      <p id="v07Meta" class="note-line"></p>
      <ol id="v07Steps" style="margin:8px 0 0;padding-left:18px;font-size:0.92rem;"></ol>
      <p id="v07Practice" class="note-line"></p>
    `;
    const dock = talk.querySelector(".dock");
    if (dock) talk.insertBefore(box, dock);
  }

  async function updateSolverFromQuestion(questionText) {
    ensureSolverBox();
    const activeLang = document.querySelector("#langSeg button[aria-pressed='true']")?.dataset.lang || "hg";
    try {
      const r = await fetch("/api/v07/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile: getProfileFromDom(),
          question: questionText || "",
          category: "general",
          lang: activeLang,
        }),
      });
      if (!r.ok) return;
      const d = await r.json();
      const hEl = document.getElementById("v07Heading");
      const sEl = document.getElementById("v07Score");
      const vEl = document.getElementById("v07Verdict");
      const mEl = document.getElementById("v07Meta");
      const stEl = document.getElementById("v07Steps");
      const prEl = document.getElementById("v07Practice");
      if (hEl) hEl.textContent = `${d.heading} — ${d.question}`;
      if (sEl) sEl.textContent = `${d.score}% clarity • ${d.window}`;
      if (vEl) vEl.textContent = d.answer;
      if (mEl) mEl.textContent = `${d.why} | Watch out: ${d.watchout}`;
      if (stEl) {
        stEl.innerHTML = "";
        (d.steps || []).forEach(step => {
          const li = document.createElement("li");
          li.textContent = step;
          stEl.appendChild(li);
        });
      }
      if (prEl) prEl.textContent = `Daily habit: ${d.practice}`;
    } catch (_) {}
  }

  document.addEventListener("submit", (ev) => {
    if (ev.target && ev.target.id === "ask") {
      const q = document.getElementById("q")?.value || "";
      setTimeout(() => updateSolverFromQuestion(q), 60);
    }
  });

  document.addEventListener("click", (ev) => {
    const chip = ev.target.closest("#chips .chip");
    if (chip) {
      setTimeout(() => updateSolverFromQuestion(chip.textContent || ""), 60);
    }
  });

  window.addEventListener("DOMContentLoaded", () => {
    ensureSolverBox();
    updateSolverFromQuestion("");
  });
})();
