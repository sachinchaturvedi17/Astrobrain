"""Dasha timing windows (v1.1.3). Pure functions; stdlib only.

The chart engine tells us the running Vimshottari period (Maha lord, Antar lord, and when the Antar ends). From that one
anchor the rest of the timeline follows deterministically: antardashas run in the fixed Vimshottari order starting from
the Maha lord, each lasting maha_years * antar_years / 120 years, and mahadashas follow the fixed order.

We then mark the upcoming sub-periods whose lord is tied to the topic asked about (lord/occupant of the relevant houses or
its natural significator). A "window" means the area is switched on, never that a particular event will happen.
If the anchor does not agree with the engine's own Maha end date, no windows are produced (we would rather say nothing).
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional

ORDER = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
YEAR_DAYS = 365.25
SOFT = {"Jupiter", "Venus", "Mercury", "Moon"}
MONTHS = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "hg": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "hi": ("जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुला", "अग", "सित", "अक्टू", "नव", "दिस"),
}
PN = {"Sun": ("Sun", "Surya", "सूर्य"), "Moon": ("Moon", "Chandra", "चंद्र"), "Mars": ("Mars", "Mangal", "मंगल"), "Mercury": ("Mercury", "Budh", "बुध"),
      "Jupiter": ("Jupiter", "Guru", "गुरु"), "Venus": ("Venus", "Shukra", "शुक्र"), "Saturn": ("Saturn", "Shani", "शनि"),
      "Rahu": ("Rahu", "Rahu", "राहु"), "Ketu": ("Ketu", "Ketu", "केतु")}
LI = {"en": 0, "hg": 1, "hi": 2}


def _d(v: Any) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def periods(chart: Dict[str, Any], today: Optional[_dt.date] = None, years_ahead: float = 6.0) -> List[Dict[str, Any]]:
    """Sub-periods from the running one up to `years_ahead`. [] when the dasha anchor is missing or inconsistent."""
    d = (chart or {}).get("dasha") or {}
    maha, antar = d.get("maha"), d.get("antar")
    antar_end, maha_end = _d(d.get("antar_end")), _d(d.get("maha_end"))
    if maha not in YEARS or antar not in YEARS or not antar_end:
        return []
    today = today or _dt.date.today()
    horizon = today + _dt.timedelta(days=int(years_ahead * YEAR_DAYS))
    rows: List[Dict[str, Any]] = []
    cur_len = _dt.timedelta(days=YEARS[maha] * YEARS[antar] / 120.0 * YEAR_DAYS)
    rows.append({"maha": maha, "antar": antar, "start": antar_end - cur_len, "end": antar_end})
    if maha_end is not None:           # cross-check our timeline with the engine's own Maha end
        seq0 = ORDER[ORDER.index(maha):] + ORDER[:ORDER.index(maha)]
        rest = sum(YEARS[maha] * YEARS[x] / 120.0 * YEAR_DAYS for x in seq0[seq0.index(antar) + 1:])
        if abs((antar_end + _dt.timedelta(days=rest) - maha_end).days) > 60:
            return []
    m, a, t = maha, antar, antar_end
    guard = 0
    while t < horizon and guard < 200:
        guard += 1
        seq = ORDER[ORDER.index(m):] + ORDER[:ORDER.index(m)]
        i = seq.index(a) + 1
        if i >= len(seq):
            m = ORDER[(ORDER.index(m) + 1) % 9]
            a = m
        else:
            a = seq[i]
        span = _dt.timedelta(days=YEARS[m] * YEARS[a] / 120.0 * YEAR_DAYS)
        rows.append({"maha": m, "antar": a, "start": t, "end": t + span})
        t = t + span
    return [r for r in rows if r["end"] >= today]


def windows(chart: Dict[str, Any], involved: Iterable[str], today: Optional[_dt.date] = None, years_ahead: float = 5.0, limit: int = 3) -> List[Dict[str, Any]]:
    rel = set(involved)
    today = today or _dt.date.today()
    out = []
    for r in periods(chart, today, years_ahead):
        if r["antar"] not in rel and r["maha"] not in rel:
            continue
        strength = (2 if r["antar"] in rel else 0) + (1 if r["maha"] in rel else 0)
        if r["antar"] not in rel:
            continue                  # the sub-period lord itself must be tied to the topic
        out.append(dict(r, strength=strength, now=r["start"] <= today <= r["end"], soft=r["antar"] in SOFT))
    out.sort(key=lambda w: (-w["strength"], w["start"]))
    return sorted(out[:limit], key=lambda w: w["start"])


def _mon(dt: _dt.date, lang: str) -> str:
    return f"{MONTHS[lang if lang in MONTHS else 'en'][dt.month - 1]} {dt.year}"


T = {
    "head": ("Looking at your dasha timeline, these stretches switch this area on:", "Aapki dasha timeline dekhein toh yeh daur is kshetra ko jagaate hain:", "आपकी दशा समयरेखा देखें तो ये दौर इस क्षेत्र को सक्रिय करते हैं:"),
    "line": ("{a} to {b}: {antar} inside {maha}. {tone}", "{a} se {b}: {maha} mein {antar}. {tone}", "{a} से {b}: {maha} में {antar}। {tone}"),
    "now": ("(running now)", "(abhi chal raha hai)", "(अभी चल रहा है)"),
    "soft": ("Tends to be a supportive stretch.", "Aam taur par madadgaar daur.", "आम तौर पर सहायक दौर।"),
    "hard": ("Tends to bring this into focus with effort and patience.", "Aam taur par is par dhyaan kheenchta hai, mehnat aur sabr ke saath.", "आम तौर पर इस पर ध्यान खींचता है, मेहनत और धैर्य के साथ।"),
    "tail": ("These are windows of activation, not dates for events. Your choices and the current transits matter as much.", "Yeh sakriyata ke daur hain, ghatnaon ki tarikh nahi. Aapke faisle aur abhi ke gochar utne hi matter karte hain.", "ये सक्रियता के दौर हैं, घटनाओं की तारीख़ नहीं। आपके फ़ैसले और मौजूदा गोचर उतने ही मायने रखते हैं।"),
    "none": ("I do not see a sub-period in the next five years that strongly switches this area on, so progress here will likely come from steady effort rather than a special window.", "Agle paanch saal mein koi aisa uplakshya daur nahi dikhta jo is kshetra ko khaas jagaye, isliye pragati lagatar mehnat se hi aayegi.", "अगले पाँच साल में कोई ऐसा उप-दौर नहीं दिखता जो इस क्षेत्र को खास सक्रिय करे, इसलिए प्रगति लगातार मेहनत से ही आएगी।"),
}


def window_lines(chart: Dict[str, Any], involved: Iterable[str], lang: str, today: Optional[_dt.date] = None) -> List[str]:
    li = LI.get(lang, 0)
    out = []
    for w in windows(chart, involved, today):
        tone = T["soft" if w["soft"] else "hard"][li]
        s = T["line"][li].format(a=_mon(max(w["start"], today or _dt.date.today()), lang), b=_mon(w["end"], lang), antar=PN[w["antar"]][li], maha=PN[w["maha"]][li], tone=tone)
        out.append(s + (" " + T["now"][li] if w["now"] else ""))
    return out


def window_text(chart: Dict[str, Any], involved: Iterable[str], lang: str, today: Optional[_dt.date] = None) -> str:
    """Paragraph for a 'when?' question. '' when there is no usable dasha data."""
    li = LI.get(lang, 0)
    if not periods(chart, today):
        return ""
    lines = window_lines(chart, involved, lang, today)
    if not lines:
        return T["none"][li]
    return T["head"][li] + " " + " ".join(lines) + " " + T["tail"][li]
