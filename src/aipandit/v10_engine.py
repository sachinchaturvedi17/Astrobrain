"""AstroMuni v1.0 API layer. Glue between the deterministic engine and the pure v1.0 modules.

Routes (all POST, JSON in/out, served by the main web handler so CSP/body limits/error handling apply):
  /api/v10/config      -> {version, map: {...}}
  /api/v10/geocode     {q, lang?}                    -> {results:[{name, display, lat, lon, country, tz}]}   (OpenStreetMap Nominatim, proxied)
  /api/v10/reverse     {lat, lon, lang?}             -> {name, display, lat, lon, country, tz}
  /api/v10/chart       {profile}                     -> {chart summary}   (used to confirm onboarding)
  /api/v10/ask         {profile?, question, lang}    -> brain.answer(...)
  /api/v10/horoscope   {profile?, lang}              -> real transit readings for all 12 Moon signs (+ the user's own)
  /api/v10/panchang    {profile?, city?}             -> compute_panchang with a transparent transit-support figure
  /api/v10/compat      {person_a, person_b, lang}    -> exact Ashtakoota (see ashtakoota.py)
  /api/v10/calculator  {type, profile, lang}         -> moon / ascendant / nakshatra / sade_sati
  /api/v10/report      {topic, profile, lang}        -> house-by-house report
  /api/v10/journal     {}                            -> articles

A profile is {name, dob, tob?, time_certainty, place, lat, lon, tz, gender, guardian_consent?}. No silent defaults:
missing coordinates or timezone are an error, because a default city quietly gives a wrong chart.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import date, datetime
from typing import Any, Dict, Optional

from . import __version__, ashtakoota, brain, gochara_live

P = "parashari"
GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
UA = "AstroMuni/%s (open-source Vedic astrology app; https://github.com/sachinchaturvedi17/Astrobrain)" % __version__
NOMINATIM = "https://nominatim.openstreetmap.org"
SINGLE_TZ = {"IN": "Asia/Kolkata", "NP": "Asia/Kathmandu", "LK": "Asia/Colombo", "BD": "Asia/Dhaka", "PK": "Asia/Karachi",
             "BT": "Asia/Thimphu", "SG": "Asia/Singapore", "AE": "Asia/Dubai", "GB": "Europe/London", "JP": "Asia/Tokyo",
             "KR": "Asia/Seoul", "TH": "Asia/Bangkok", "MY": "Asia/Kuala_Lumpur", "QA": "Asia/Qatar", "SA": "Asia/Riyadh",
             "OM": "Asia/Muscat", "KW": "Asia/Kuwait", "AF": "Asia/Kabul", "IE": "Europe/Dublin", "NL": "Europe/Amsterdam"}
_chart_cache: "OrderedDict[tuple, dict]" = OrderedDict()
_geo_cache: "OrderedDict[str, Any]" = OrderedDict()
_geo_lock = threading.Lock()
_geo_last = [0.0]


def _req(p: Dict[str, Any], key: str) -> Any:
    v = p.get(key)
    if v in (None, ""):
        raise ValueError(f"missing {key}")
    return v


def validate_profile(p: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(p, dict):
        raise ValueError("profile is required")
    name = str(p.get("name") or "").strip()[:60]
    dob = str(_req(p, "dob"))
    try:
        d = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("date of birth must be YYYY-MM-DD")
    if d > date.today() or d.year < 1900:
        raise ValueError("date of birth is out of range")
    cert = str(p.get("time_certainty") or ("exact" if p.get("tob") else "unknown"))
    if cert not in ("exact", "approx_15min", "part_of_day", "unknown"):
        raise ValueError("bad time_certainty")
    tob = str(p.get("tob") or "").strip() or None
    if cert != "unknown":
        if not tob or not re.match(r"^\d{1,2}:\d{2}$", tob):
            raise ValueError("time of birth must be HH:MM")
    lat, lon = float(_req(p, "lat")), float(_req(p, "lon"))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        raise ValueError("pick the birthplace on the map or search for it")
    tz = str(_req(p, "tz"))
    age = (date.today() - d).days / 365.25
    return {"name": name, "dob": dob, "tob": tob if cert != "unknown" else None, "time_certainty": cert,
            "place": str(p.get("place") or "")[:80], "lat": lat, "lon": lon, "tz": tz,
            "gender": p.get("gender") if p.get("gender") in ("male", "female", "other", "prefer_not_to_say") else "prefer_not_to_say",
            "minor": age < 18, "guardian_consent": bool(p.get("guardian_consent"))}


def _birth(v: Dict[str, Any]):
    from .intake import BirthInput
    g = v["gender"]
    return BirthInput(name=v["name"], date=v["dob"], time=v["tob"], time_certainty=v["time_certainty"], place_name=v["place"],
                      latitude=v["lat"], longitude=v["lon"], tz_name=v["tz"], gender=g,
                      gender_rule_mode="binary" if g in ("male", "female") else "neutral",
                      subject_is_minor=v["minor"], guardian_consent=bool(v["guardian_consent"] and v["minor"]))


def build_chart(profile: Dict[str, Any]) -> Dict[str, Any]:
    v = validate_profile(profile)
    key = (v["name"], v["dob"], v["tob"], v["time_certainty"], v["lat"], v["lon"], v["tz"], v["gender"], date.today().isoformat())
    if key in _chart_cache:
        _chart_cache.move_to_end(key)
        return _chart_cache[key]
    from .astrobrain_extensions import build_astrobrain_store
    kundli, store = build_astrobrain_store(_birth(v), today=date.today())
    f = store.value
    planets = {}
    for g in GRAHAS:
        sign = f(g, "sign", P)
        if sign:
            planets[g] = {"sign": sign, "house": f(g, "house", P), "retrograde": bool(f(g, "retrograde", P)),
                          "nakshatra": f(g, "nakshatra", P), "pada": f(g, "pada", P)}
    lagna = f("lagna", "sign", P)
    d = {k: f("dasha", k, P) for k in ("maha_lord", "maha_end", "antar_lord", "antar_end")}
    chart = {"lagna": lagna, "moon": {"sign": f("Moon", "sign", P), "nakshatra": f("Moon", "nakshatra", P), "pada": f("Moon", "pada", P)},
             "planets": planets,
             "dasha": {"maha": d["maha_lord"], "antar": d["antar_lord"], "maha_end": str(d["maha_end"] or "")[:10],
                       "antar_end": str(d["antar_end"] or "")[:10]} if d["maha_lord"] else None,
             "time_certainty": v["time_certainty"], "withheld": sorted({f"{w.subject} {w.predicate}" for w in kundli.withheld}),
             "warnings": list(kundli.warnings), "name": v["name"], "profile": v}
    _chart_cache[key] = chart
    while len(_chart_cache) > 64:
        _chart_cache.popitem(last=False)
    return chart


def _sky(city: str = "Bhopal"):
    from .v09_engine import compute_panchang
    pan = compute_panchang(city or "Bhopal")
    return pan, pan["sky_planets"]


# ------------------------------------------------------------------------------------------ geocoding (OSM Nominatim)
def _tz_for(lat: float, lon: float, country: str) -> Optional[str]:
    try:                                    # optional offline lookup: pip install timezonefinder
        from timezonefinder import TimezoneFinder
        z = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        if z:
            return z
    except Exception:
        pass
    return SINGLE_TZ.get((country or "").upper())


def _nominatim(path: str, params: Dict[str, Any]) -> Any:
    """Nominatim usage policy: identify the app, <=1 request/second, cache results. Proxied here so the browser never
    talks to a third party and the User-Agent can be set."""
    url = f"{NOMINATIM}/{path}?" + urllib.parse.urlencode(params)
    with _geo_lock:
        if url in _geo_cache:
            return _geo_cache[url]
        wait = 1.05 - (time.time() - _geo_last[0])
        if wait > 0:
            time.sleep(wait)
        _geo_last[0] = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        raise ValueError("place search is unavailable right now; you can still tap the map or type latitude and longitude")
    with _geo_lock:
        _geo_cache[url] = data
        while len(_geo_cache) > 256:
            _geo_cache.popitem(last=False)
    return data


def _place(rec: Dict[str, Any]) -> Dict[str, Any]:
    a = rec.get("address") or {}
    cc = (a.get("country_code") or "").upper()
    lat, lon = float(rec["lat"]), float(rec["lon"])
    name = rec.get("name") or a.get("city") or a.get("town") or a.get("village") or a.get("state") or rec.get("display_name", "")[:40]
    return {"name": name, "display": rec.get("display_name", name), "lat": round(lat, 5), "lon": round(lon, 5), "country": cc, "tz": _tz_for(lat, lon, cc)}


def geocode(payload: Dict[str, Any]) -> Dict[str, Any]:
    q = str(payload.get("q") or "").strip()[:100]
    if len(q) < 3:
        raise ValueError("type at least 3 letters")
    data = _nominatim("search", {"q": q, "format": "jsonv2", "limit": 6, "addressdetails": 1,
                                 "accept-language": {"hi": "hi,en", "hg": "en", "en": "en"}.get(payload.get("lang"), "en")})
    return {"ok": True, "results": [_place(r) for r in data]}


def reverse(payload: Dict[str, Any]) -> Dict[str, Any]:
    lat, lon = float(_req(payload, "lat")), float(_req(payload, "lon"))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("bad coordinates")
    data = _nominatim("reverse", {"lat": round(lat, 5), "lon": round(lon, 5), "format": "jsonv2", "zoom": 10, "addressdetails": 1})
    if not isinstance(data, dict) or "lat" not in data:
        cc = ""
        return {"ok": True, "name": "", "display": f"{lat:.4f}, {lon:.4f}", "lat": round(lat, 5), "lon": round(lon, 5), "country": cc, "tz": _tz_for(lat, lon, cc)}
    out = _place(data)
    out.update({"lat": round(lat, 5), "lon": round(lon, 5), "tz": _tz_for(lat, lon, out["country"])})   # keep the exact pin
    return {"ok": True, **out}


# ------------------------------------------------------------------------------------------ features
def _chart_or_none(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return build_chart(payload["profile"]) if payload.get("profile") else None


def ask(payload: Dict[str, Any]) -> Dict[str, Any]:
    q = str(payload.get("question") or "").strip()[:500]
    if not q:
        raise ValueError("empty question")
    lang = payload.get("lang") if payload.get("lang") in ("en", "hg", "hi") else "en"
    chart = _chart_or_none(payload)
    sky = None
    if brain.classify(q) in ("transit", "sade_sati"):
        try:
            sky = _sky()[1]
        except Exception:
            sky = None
    hist = payload.get("history") if isinstance(payload.get("history"), list) else []
    hist = [{k: (str(m.get(k))[:40] if k != "text" else str(m.get(k))[:600]) for k in ("role", "text", "topic", "expects") if m.get(k) is not None}
            for m in hist[-6:] if isinstance(m, dict)]
    out = brain.answer(q, chart, lang, sky, history=hist)
    out["mode"] = payload.get("mode", "muni")
    return out


def horoscope(payload: Dict[str, Any]) -> Dict[str, Any]:
    lang = payload.get("lang") if payload.get("lang") in ("en", "hg", "hi") else "en"
    pan, sky = _sky(payload.get("city") or "Bhopal")
    from .kb_core import SIGNS
    signs = []
    for key, en, hi, lord, el, mod in SIGNS:
        r = gochara_live.reading_for_moon_sign(key, sky, lang)
        signs.append({"key": key, "en": en, "hi": hi, "lord": lord, "headline": r["headline"], "reading": " ".join(r["lines"][:2]),
                      "lines": r["lines"], "support": r["support"], "band": r["band"], "sade_sati": r["sade_sati"], "facts": r["facts"]})
    mine = None
    if payload.get("profile"):
        moon = build_chart(payload["profile"])["moon"]["sign"]
        mine = next((s for s in signs if s["key"] == moon), None)
    return {"ok": True, "date": pan["date_label"], "tithi": pan["tithi"], "signs": signs, "mine": mine,
            "method": "Classical Gochara: each planet's current house counted from the Moon sign. 'Transit support' is the weighted share of favourable transits, not a probability."}


def panchang(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Tithi/nakshatra/yoga/karana from the engine; sunrise, Abhijit and Rahu Kaal computed for the person's place
    (no fixed tables); 'energy' is the real transit-support figure for their Moon sign (see gochara_live)."""
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    from . import solar
    from .v09_engine import compute_panchang
    prof = payload.get("profile")
    chart = build_chart(prof) if prof else None
    cities = _known_cities()
    city = (prof or {}).get("place") or payload.get("city") or "Bhopal"
    pan = compute_panchang(city if str(city).lower() in cities else "Bhopal")
    w = payload.get("where") or prof          # where the person is NOW (falls back to the birthplace)
    lat, lon, tz = (float(w["lat"]), float(w["lon"]), str(w["tz"])) if w and w.get("lat") is not None and w.get("tz") else cities.get(str(city).lower(), (23.2599, 77.4126, "Asia/Kolkata"))
    pan["place"] = (payload.get("where") or {}).get("name") or (prof or {}).get("place") or str(city)
    try:
        zi = ZoneInfo(tz)
        today = datetime.now(zi)
        off = today.utcoffset().total_seconds() / 3600.0
        times = solar.day_timings(today.date(), float(lat), float(lon), off)
    except Exception:
        times = None
    pan.pop("lucky_hour", None)
    if times:
        pan.update({"sunrise": times["sunrise"], "sunset": times["sunset"], "abhijit": times["abhijit"], "rahu_kaal": times["rahu_kaal"]})
    else:
        for k in ("abhijit", "rahu_kaal"):
            pan[k] = ""
    moon = (chart["moon"]["sign"] if chart else pan.get("active_rashi"))
    if moon in gochara_live.RASHIS:
        r = gochara_live.reading_for_moon_sign(moon, pan["sky_planets"], payload.get("lang") or "en")
        pan["energy"], pan["energy_label"], pan["energy_band"] = r["support"], "Transit support", r["band"]
    pan["method"] = "Sunrise, Abhijit and Rahu Kaal are calculated for your birthplace's coordinates."
    return pan


def _known_cities():
    from .problem_solver import CITY_COORDS
    return CITY_COORDS


def compat(payload: Dict[str, Any]) -> Dict[str, Any]:
    ca, cb = build_chart(_req(payload, "person_a")), build_chart(_req(payload, "person_b"))
    a = {"name": ca["name"], "rashi": ca["moon"]["sign"], "nakshatra": ca["moon"]["nakshatra"]}
    b = {"name": cb["name"], "rashi": cb["moon"]["sign"], "nakshatra": cb["moon"]["nakshatra"]}
    r = ashtakoota.compute(a, b)
    r["person_a"], r["person_b"] = a, b
    return r


def calculator(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .v09_engine import run_calculator
    v = validate_profile(payload.get("profile"))
    legacy = {"name": v["name"], "dob": v["dob"], "tob": v["tob"] or "", "city": v["place"], "lat": v["lat"], "lon": v["lon"],
              "tz_name": v["tz"], "time_certainty": v["time_certainty"]}
    return run_calculator(payload.get("type") or "moon", legacy, payload.get("lang") or "en")


def report(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = payload.get("topic") if payload.get("topic") in brain.TOPICS else "career"
    lang = payload.get("lang") if payload.get("lang") in ("en", "hg", "hi") else "en"
    chart = build_chart(_req(payload, "profile"))
    out = brain.answer(f"{topic}", chart, lang, use_llm=False)
    out["houses"] = [brain.analyse_house(chart, h, lang) for h in brain.TOPICS[topic]["houses"]] if chart.get("lagna") in ashtakoota.RASHIS else []
    return out


def chart_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    c = build_chart(_req(payload, "profile"))
    return {"ok": True, "lagna": c["lagna"], "moon": c["moon"], "dasha": c["dasha"], "withheld": c["withheld"], "warnings": c["warnings"],
            "planets": c["planets"], "time_certainty": c["time_certainty"]}


def journal(_: Dict[str, Any]) -> Dict[str, Any]:
    from .v09_engine import JOURNAL_ARTICLES
    return {"ok": True, "articles": JOURNAL_ARTICLES}


ROUTES = {"/api/v10/geocode": geocode, "/api/v10/reverse": reverse, "/api/v10/chart": chart_summary, "/api/v10/ask": ask,
          "/api/v10/horoscope": horoscope, "/api/v10/panchang": panchang, "/api/v10/compat": compat,
          "/api/v10/calculator": calculator, "/api/v10/report": report, "/api/v10/journal": journal,
          "/api/v10/config": lambda _: {"ok": True, "version": __version__, "map": {"tiles": "osm", "geocoder": "nominatim"}}}


def handle_v10(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    fn = ROUTES.get(path)
    if fn is None:
        raise KeyError("route")
    return fn(payload)
