"""AstroMuni v0.9 Unified Vedic Data, Calculation & Consultation Engine."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .astrobrain_extensions import build_astrobrain_store, evaluate_astrobrain_rules
from .engines.vedaksha_engine import VedakshaEngine
from .explain import describe_fact
GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
from .problem_solver import CITY_COORDS, _to_birth_input, _to_palm_obs, solve_problem, summarize_profile

ROOT_DIR = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT_DIR / "knowledge_base" / "shastra_corpus.jsonl"

RASHI_META: Dict[str, Dict[str, Any]] = {
    "Mesha": {"en": "Aries", "hi": "\u092e\u0947\u0937", "lord": "Mars", "element": "Fire", "symbol": "\u2648", "theme": "courage and decisive clarity"},
    "Vrishabha": {"en": "Taurus", "hi": "\u0935\u0943\u0937\u092d", "lord": "Venus", "element": "Earth", "symbol": "\u2649", "theme": "steadiness and patient building"},
    "Mithuna": {"en": "Gemini", "hi": "\u092e\u093f\u0925\u0941\u0928", "lord": "Mercury", "element": "Air", "symbol": "\u264a", "theme": "curiosity and adaptable thinking"},
    "Karka": {"en": "Cancer", "hi": "\u0915\u0930\u094d\u0915", "lord": "Moon", "element": "Water", "symbol": "\u264b", "theme": "emotional warmth and intuition"},
    "Simha": {"en": "Leo", "hi": "\u0938\u093f\u0902\u0939", "lord": "Sun", "element": "Fire", "symbol": "\u264c", "theme": "heart-led leadership and dignity"},
    "Kanya": {"en": "Virgo", "hi": "\u0915\u0928\u094d\u092f\u093e", "lord": "Mercury", "element": "Earth", "symbol": "\u264d", "theme": "discernment and practical craft"},
    "Tula": {"en": "Libra", "hi": "\u0924\u0941\u0932\u093e", "lord": "Venus", "element": "Air", "symbol": "\u264e", "theme": "harmony and thoughtful partnership"},
    "Vrishchika": {"en": "Scorpio", "hi": "\u0935\u0943\u0936\u094d\u091a\u093f\u0915", "lord": "Mars", "element": "Water", "symbol": "\u264f", "theme": "depth and quiet transformation"},
    "Dhanu": {"en": "Sagittarius", "hi": "\u0927\u0928\u0941", "lord": "Jupiter", "element": "Fire", "symbol": "\u2650", "theme": "wisdom and long-horizon vision"},
    "Makara": {"en": "Capricorn", "hi": "\u092e\u0915\u0930", "lord": "Saturn", "element": "Earth", "symbol": "\u2651", "theme": "discipline and earned mastery"},
    "Kumbha": {"en": "Aquarius", "hi": "\u0915\u0941\u0902\u092d", "lord": "Saturn", "element": "Air", "symbol": "\u2652", "theme": "perspective and original insight"},
    "Meena": {"en": "Pisces", "hi": "\u092e\u0940\u0928", "lord": "Jupiter", "element": "Water", "symbol": "\u2653", "theme": "compassion and spiritual trust"},
}

_NAK_RAW = [
    ("Ashwini", "Ketu", "Ashwini Kumaras", "Deva", "Adi", "Horse", "Swift healing and fresh beginnings."),
    ("Bharani", "Venus", "Yama", "Manushya", "Madhya", "Elephant", "Creative endurance and responsibility."),
    ("Krittika", "Sun", "Agni", "Rakshasa", "Antya", "Sheep", "Purifying clarity and sharp discrimination."),
    ("Rohini", "Moon", "Brahma", "Manushya", "Antya", "Serpent", "Growth, artistic grace, and emotional richness."),
    ("Mrigashira", "Mars", "Soma", "Deva", "Madhya", "Serpent", "Gentle curiosity and perceptive sensitivity."),
    ("Ardra", "Rahu", "Rudra", "Manushya", "Adi", "Dog", "Emotional depth and analytical insight."),
    ("Punarvasu", "Jupiter", "Aditi", "Deva", "Adi", "Cat", "Resilience, generosity, and philosophical calm."),
    ("Pushya", "Saturn", "Brihaspati", "Deva", "Madhya", "Sheep", "Nourishment, steady dharma, and loyalty."),
    ("Ashlesha", "Mercury", "Nagas", "Rakshasa", "Antya", "Cat", "Intuitive strategy and psychological depth."),
    ("Magha", "Ketu", "Pitris", "Rakshasa", "Antya", "Rat", "Ancestral dignity and natural authority."),
    ("Purva Phalguni", "Venus", "Bhaga", "Manushya", "Madhya", "Rat", "Warmth, creative joy, and social ease."),
    ("Uttara Phalguni", "Sun", "Aryaman", "Manushya", "Adi", "Cow", "Reliability and supportive leadership."),
    ("Hasta", "Moon", "Savitar", "Deva", "Adi", "Buffalo", "Skillful hands, wit, and practical mastery."),
    ("Chitra", "Mars", "Tvastar", "Rakshasa", "Madhya", "Tiger", "Architectural vision and aesthetics."),
    ("Swati", "Rahu", "Vayu", "Deva", "Antya", "Buffalo", "Independence, diplomacy, and adaptability."),
    ("Vishakha", "Jupiter", "Indra-Agni", "Rakshasa", "Antya", "Tiger", "Single-pointed ambition and determination."),
    ("Anuradha", "Saturn", "Mitra", "Deva", "Madhya", "Deer", "Devotion, friendship, and perseverance."),
    ("Jyeshtha", "Mercury", "Indra", "Rakshasa", "Adi", "Deer", "Protective responsibility and strategic mind."),
    ("Mula", "Ketu", "Nirriti", "Rakshasa", "Adi", "Dog", "Root-level inquiry and truth-seeking."),
    ("Purva Ashadha", "Venus", "Apas", "Manushya", "Madhya", "Monkey", "Invincible optimism and creative flow."),
    ("Uttara Ashadha", "Sun", "Vishvadevas", "Manushya", "Antya", "Mongoose", "Enduring integrity and principled leadership."),
    ("Shravana", "Moon", "Vishnu", "Deva", "Antya", "Monkey", "Deep listening, learning, and counsel."),
    ("Dhanishta", "Mars", "Vasus", "Rakshasa", "Madhya", "Lion", "Rhythm, resourcefulness, and ambition."),
    ("Shatabhisha", "Rahu", "Varuna", "Rakshasa", "Adi", "Horse", "Independent insight and healing research."),
    ("Purva Bhadrapada", "Jupiter", "Aja Ekapada", "Manushya", "Adi", "Lion", "Idealism and transformative perspective."),
    ("Uttara Bhadrapada", "Saturn", "Ahir Budhnya", "Manushya", "Madhya", "Cow", "Grounded depth, compassion, and patience."),
    ("Revati", "Mercury", "Pushan", "Deva", "Antya", "Elephant", "Safe guidance, empathy, and creativity."),
]
NAKSHATRA_DATA = [{"name": n, "lord": l, "deity": d, "gana": g, "nadi": nd, "yoni": y, "nature": nt} for n, l, d, g, nd, y, nt in _NAK_RAW]
TITHI_NAMES = (["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"] * 2)
TITHI_NAMES[-1] = "Amavasya"
NITYA_YOGAS = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"]

ASTROPEDIA_TOPICS: List[Dict[str, Any]] = [
    {"keys": ["lagna", "ascendant", "first house"], "title": "Ascendant (Lagna)", "en": "Your Ascendant (Lagna) is the eastern horizon sign at birth, setting the 12-house map of your Janam Kundli.", "hg": "Aapka Lagna janam ke samay poorvi kshitij ki rashi hai jo 12 gharon ka map set karti hai.", "hi": "\u0932\u0917\u094d\u0928 \u091c\u0928\u094d\u092e \u0915\u0947 \u0938\u092e\u092f \u0909\u0926\u093f\u0924 \u0939\u094b\u0928\u0947 \u0935\u093e\u0932\u0940 \u0930\u093e\u0936\u093f \u0939\u0948 \u091c\u094b \u0915\u0941\u0902\u0921\u0932\u0940 \u0915\u0947 12 \u092d\u093e\u0935\u094b\u0902 \u0915\u0940 \u0926\u093f\u0936\u093e \u0924\u092f \u0915\u0930\u0924\u0940 \u0939\u0948\u0964"},
    {"keys": ["moon", "rashi", "chandra"], "title": "Moon Sign (Chandra Rashi)", "en": "Your Moon sign (Chandra Rashi) reflects emotional rhythm and daily mental weather; daily horoscopes are read from it.", "hg": "Chandra Rashi aapke emotional rhythm aur daily mood ko dikhati hai; daily horoscope isi se dekha jaata hai.", "hi": "\u091a\u0902\u0926\u094d\u0930 \u0930\u093e\u0936\u093f \u092e\u0928 \u0914\u0930 \u0926\u0948\u0928\u093f\u0915 \u092e\u093e\u0928\u0938\u093f\u0915 \u0938\u094d\u0925\u093f\u0924\u093f \u0915\u094b \u0926\u0930\u094d\u0936\u093e\u0924\u0940 \u0939\u0948\u0964"},
    {"keys": ["dasha", "mahadasha", "antardasha", "vimshottari"], "title": "Vimshottari Dasha", "en": "Vimshottari Dasha is a 120-year planetary timeline showing which planet's chapter is currently active in your chart.", "hg": "Vimshottari Dasha 120 saal ki planetary timeline hai jo current active grah ka chapter dikhati hai.", "hi": "\u0935\u093f\u0902\u0936\u094b\u0924\u094d\u0924\u0930\u0940 \u0926\u0936\u093e \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u092e\u0947\u0902 \u0938\u0915\u094d\u0930\u093f\u092f \u0917\u094d\u0930\u0939 \u0915\u0940 \u0905\u0935\u0927\u093f \u0915\u094b \u0926\u0930\u094d\u0936\u093e\u0924\u0940 \u0939\u0948\u0964"},
    {"keys": ["sade sati", "shani", "saturn"], "title": "Saturn & Sade Sati", "en": "Sade Sati occurs when transiting Saturn moves through the 12th, 1st, and 2nd signs from your natal Moon over 7.5 years, building discipline and patience.", "hg": "Sade Sati mein gochar Shani janam Chandra se 12ven, 1st aur 2nd ghar se guzarte hain (7.5 saal) aur discipline aur sabr sikhaate hain.", "hi": "\u0938\u093e\u0922\u093c\u0947\u0938\u093e\u0924\u0940 \u092e\u0947\u0902 \u0917\u094b\u091a\u0930 \u0936\u0928\u093f \u091a\u0902\u0926\u094d\u0930 \u0938\u0947 12\u0935\u0947\u0902, 1st \u0914\u0930 2nd \u092d\u093e\u0935 \u0938\u0947 \u0917\u0941\u091c\u0930\u0924\u0947 \u0939\u0948\u0902 \u0914\u0930 \u0905\u0928\u0941\u0936\u093e\u0938\u0928 \u092c\u0928\u093e\u0924\u0947 \u0939\u0948\u0902\u0964"},
    {"keys": ["nakshatra", "star", "pada"], "title": "The 27 Nakshatras", "en": "Each 13°20' lunar mansion is a Nakshatra with its own ruling planet and deity, revealing subtle instincts beyond your zodiac sign.", "hg": "Har 13°20' ka chandrama mandal ek Nakshatra hota hai jo rashi se bhi gehra swabhav dikhata hai.", "hi": "\u092a\u094d\u0930\u0924\u094d\u092f\u0947\u0915 13°20' \u0915\u093e \u091a\u0902\u0926\u094d\u0930 \u092e\u0902\u0921\u0932 \u0928\u0915\u094d\u0937\u0924\u094d\u0930 \u0915\u0939\u0932\u093e\u0924\u093e \u0939\u0948\u0964"},
    {"keys": ["compatibility", "gun", "ashtakoota", "marriage"], "title": "Ashtakoota Gun Milan", "en": "Ashtakoota evaluates 8 dimensions of harmony between two birth charts out of 36 points (Gunas).", "hg": "Ashtakoota do kundliyon ke beech 36 gunon ke 8 pehluon ka talmel dekhta hai.", "hi": "\u0905\u0937\u094d\u091f\u0915\u0942\u091f \u092e\u093f\u0932\u093e\u0928 \u0926\u094b \u0915\u0941\u0902\u0921\u0932\u093f\u092f\u094b\u0902 \u0915\u0947 \u092c\u0940\u091a 36 \u0917\u0941\u0923\u094b\u0902 \u0915\u093e \u0906\u0915\u0932\u0928 \u0915\u0930\u0924\u093e \u0939\u0948\u0964"},
]

JOURNAL_ARTICLES: List[Dict[str, Any]] = [
    {"id": "saturn-building", "category": "PLANETS", "read_time": "8 MIN", "symbol": "\u2644", "theme": "dark", "title": "Saturn isn't punishing you. It's asking you to build.", "subtitle": "A gentler way to understand discipline, delay, and the gift of staying power.", "body": ["In classical Parashari texts, Saturn (Shani) is the karaka of endurance, honesty, and structures that last across decades.", "When Saturn aspects your Moon or activates your 10th house, delays invite stronger foundations and clearer routines."]},
    {"id": "moon-remembers", "category": "NAKSHATRAS", "read_time": "6 MIN", "symbol": "\u263e", "theme": "amber", "title": "What your Moon remembers", "subtitle": "Your nakshatra reveals the emotional home you instinctively return to.", "body": ["Your Moon moves through 27 Nakshatras, shaping how you process stress and what restores your inner calm."]},
    {"id": "week-with-planets", "category": "VEDIC LIVING", "read_time": "5 MIN", "symbol": "\u2609", "theme": "gold", "title": "Planning your week with the planets", "subtitle": "Work with each day's ruling graha instead of pushing against it.", "body": ["Align analytical work with Wednesday (Mercury), big-picture planning with Thursday (Jupiter), and rest/review with Saturday (Saturn)."]},
]

_CORPUS_CACHE: Optional[List[Dict[str, Any]]] = None


def search_shastra_corpus(query: str, limit: int = 2) -> List[Dict[str, Any]]:
    global _CORPUS_CACHE
    if _CORPUS_CACHE is None:
        rows: List[Dict[str, Any]] = []
        if CORPUS_PATH.exists():
            for ln in CORPUS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
                if ln.strip():
                    try:
                        rows.append(json.loads(ln))
                    except json.JSONDecodeError:
                        pass
        _CORPUS_CACHE = rows
    words = {w.lower().strip("?,.'\"") for w in query.split() if len(w.strip("?,.'\"")) >= 4}
    if not words:
        return []
    scored = [(sum(1 for w in words if w in (r.get("text") or "").lower()), r) for r in _CORPUS_CACHE]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: -x[0])
    out = []
    for _, rec in scored[:limit]:
        snip = (rec.get("text") or "").strip().replace("\n", " ")[:200]
        out.append({"source": rec.get("source_title", "Classical Jyotish Corpus"), "snippet": snip})
    return out


def _jd_now(ref_dt: Optional[dt.datetime] = None) -> float:
    now_utc = (ref_dt or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    y, m = now_utc.year, now_utc.month
    d = now_utc.day + (now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + (a // 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def compute_panchang(city: str = "Bhopal", profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    lat, lon, _ = CITY_COORDS.get((city or "Bhopal").strip().lower(), (23.2599, 77.4126, "Asia/Kolkata"))
    now_ist = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    sky = VedakshaEngine().natal(_jd_now(now_ist), lat, lon)
    sun_lon, moon_lon = sky.planets["Sun"].longitude, sky.planets["Moon"].longitude
    diff = (moon_lon - sun_lon) % 360.0
    tithi_idx = int(diff // 12.0) % 30
    paksha = "Shukla Paksha" if tithi_idx < 15 else "Krishna Paksha"
    nak_idx = int(moon_lon // (360.0 / 27.0)) % 27
    nak_info = NAKSHATRA_DATA[nak_idx]
    moon_rashi = RASHIS[int(moon_lon // 30.0) % 12]
    yoga_idx = int(((sun_lon + moon_lon) % 360.0) // (360.0 / 27.0)) % 27
    karana = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"][int(diff // 6.0) % 7]
    wd = now_ist.weekday()
    guiding = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"][wd]
    focus = ["Emotional clarity", "Decisive action", "Communication", "Wisdom & growth", "Harmony & craft", "Discipline", "Purpose"][wd]
    user_rashi = summarize_profile(profile).get("rashi") if (profile and profile.get("dob")) else None
    active_rashi = user_rashi if user_rashi in RASHI_META else moon_rashi
    ameta = RASHI_META[active_rashi]
    energy = 74 + ((tithi_idx * 3 + nak_idx) % 21)
    sky_planets = {g: {"sign": RASHIS[int(sky.planets[g].longitude // 30.0) % 12], "degree": round(sky.planets[g].longitude % 30.0, 2), "retrograde": sky.planets[g].retrograde} for g in GRAHAS}
    return {"ok": True, "date_label": now_ist.strftime("%A, %d %B %Y"), "city": city or "Bhopal", "paksha": paksha, "tithi": f"{paksha.split()[0]} {TITHI_NAMES[tithi_idx]}", "nakshatra": nak_info["name"], "nakshatra_lord": nak_info["lord"], "yoga": NITYA_YOGAS[yoga_idx], "karana": karana, "abhijit": "11:52 - 12:38", "rahu_kaal": ["07:30 - 09:00", "15:00 - 16:30", "12:00 - 13:30", "13:30 - 15:00", "10:30 - 12:00", "09:00 - 10:30", "16:30 - 18:00"][wd], "lucky_hour": "10:30 AM", "guiding_planet": guiding, "focus": focus, "energy": energy, "energy_label": "Radiant & decisive" if energy >= 82 else "Grounded & steady", "active_rashi": active_rashi, "active_rashi_en": ameta["en"], "active_symbol": ameta["symbol"], "sky_planets": sky_planets}

def compute_compatibility(person_a: Dict[str, Any], person_b: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    b1, b2 = _to_birth_input(person_a), _to_birth_input(person_b)
    _, s1 = build_astrobrain_store(b1)
    _, s2 = build_astrobrain_store(b2)
    r1, r2 = s1.value("Moon", "sign", "parashari") or "Simha", s2.value("Moon", "sign", "parashari") or "Tula"
    n1, n2 = s1.value("Moon", "nakshatra", "parashari") or "Magha", s2.value("Moon", "nakshatra", "parashari") or "Swati"
    ri1, ri2 = RASHIS.index(r1), RASHIS.index(r2)
    nnames = [x["name"] for x in NAKSHATRA_DATA]
    ni1, ni2 = nnames.index(n1) if n1 in nnames else 9, nnames.index(n2) if n2 in nnames else 14
    d1, d2 = NAKSHATRA_DATA[ni1], NAKSHATRA_DATA[ni2]
    l1, l2 = RASHI_META[r1]["lord"], RASHI_META[r2]["lord"]
    kootas = [
        {"name": "Varna", "obtained": 1.0 if (ri1 % 4) <= (ri2 % 4) else 0.5, "max": 1, "note": "Spiritual alignment"},
        {"name": "Vashya", "obtained": 2.0 if ri1 == ri2 else 1.5, "max": 2, "note": "Mutual warmth"},
        {"name": "Tara", "obtained": 3.0 if (((ni2 - ni1) % 27) % 9) in (1, 3, 5, 7, 0) else 1.5, "max": 3, "note": "Wellbeing rhythm"},
        {"name": "Yoni", "obtained": 4.0 if d1["yoni"] == d2["yoni"] else 2.5, "max": 4, "note": "Instinctual bond"},
        {"name": "Graha Maitri", "obtained": 5.0 if l1 == l2 else 4.0, "max": 5, "note": f"{l1} & {l2} rapport"},
        {"name": "Gana", "obtained": 6.0 if d1["gana"] == d2["gana"] else 4.5, "max": 6, "note": f"{d1['gana']} & {d2['gana']}"},
        {"name": "Bhakoot", "obtained": 0.0 if (((ri2 - ri1) % 12) + 1) in (2, 6, 8, 12) else 7.0, "max": 7, "note": "Emotional flow"},
        {"name": "Nadi", "obtained": 8.0 if d1["nadi"] != d2["nadi"] else 0.0, "max": 8, "note": f"{d1['nadi']} / {d2['nadi']}"},
    ]
    total = round(sum(k["obtained"] for k in kootas), 1)
    pct = min(98, max(42, int(round((total / 36.0) * 100))))
    summary = f"{b1.name} ({RASHI_META[r1]['en']}) and {b2.name} ({RASHI_META[r2]['en']}) score {total}/36 ({pct}%) in Ashtakoota Gun Milan."
    return {"ok": True, "person_a": {"name": b1.name, "rashi": r1, "rashi_en": RASHI_META[r1]["en"], "nakshatra": n1}, "person_b": {"name": b2.name, "rashi": r2, "rashi_en": RASHI_META[r2]["en"], "nakshatra": n2}, "total_points": total, "max_points": 36, "percentage": pct, "summary": summary, "kootas": kootas, "strengths": [f"Mental rapport between {l1} and {l2}.", f"Complementary lunar rhythm across {n1} and {n2}."], "growth_areas": ["Keep expectations spoken clearly during busy periods."]}


def run_calculator(calc_type: str, profile: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    prof = summarize_profile(profile)
    b = _to_birth_input(profile)
    _, store = build_astrobrain_store(b)
    panchang = compute_panchang(b.place_name, profile)
    rashi = prof.get("rashi") if prof.get("rashi") in RASHI_META else "Simha"
    rmeta = RASHI_META[rashi]
    lagna = prof.get("lagna") if prof.get("lagna") in RASHI_META else rashi
    lmeta = RASHI_META[lagna]
    nak = prof.get("nakshatra", "Magha")
    ninfo = next((x for x in NAKSHATRA_DATA if x["name"] == nak), NAKSHATRA_DATA[0])
    pada = min(4, max(1, int((float(store.value("Moon", "degree", "parashari") or 12.4) % (360.0 / 27.0)) // (360.0 / 108.0)) + 1))
    sat_sign = panchang["sky_planets"]["Saturn"]["sign"]
    rel = (RASHIS.index(sat_sign) - RASHIS.index(rashi)) % 12
    ss_map = {11: ("Rising Phase (1st Dhaiya)", "Saturn is in the 12th sign from your Moon, encouraging simpler commitments."), 0: ("Peak Phase (2nd Dhaiya)", "Saturn is over your natal Moon, building emotional maturity and steady focus."), 1: ("Setting Phase (3rd Dhaiya)", "Saturn is in the 2nd sign from your Moon, stabilizing responsibilities.")}
    ss_phase, ss_desc = ss_map.get(rel, ("Not Currently Active", f"Saturn is in {RASHI_META[sat_sign]['en']}, outside Sade Sati houses for your {rmeta['en']} Moon."))
    ct = (calc_type or "moon").strip().lower()
    if ct in ("ascendant", "lagna"):
        return {"ok": True, "calculator": "Ascendant (Lagna)", "headline": f"{lmeta['en']} ({lagna}) Ascendant", "subline": f"Lord: {lmeta['lord']} | Element: {lmeta['element']}", "summary": f"Your rising sign is {lmeta['en']} ({lagna}), ruled by {lmeta['lord']}, emphasizing {lmeta['theme']}.", "highlights": [f"Ascendant: {lmeta['en']}", f"Lagna Lord: {lmeta['lord']}", f"Dasha: {prof['mahadasha']}-{prof['antardasha']}"]}
    if ct == "nakshatra":
        return {"ok": True, "calculator": "Nakshatra & Pada", "headline": f"{nak} - Pada {pada}", "subline": f"Lord: {ninfo['lord']} | Deity: {ninfo['deity']}", "summary": f"Your Moon rests in {nak} (Pada {pada}), governed by {ninfo['lord']}. {ninfo['nature']}", "highlights": [f"Nakshatra: {nak} Pada {pada}", f"Gana/Nadi: {ninfo['gana']}/{ninfo['nadi']}", f"Lord: {ninfo['lord']}"]}
    if ct in ("sade_sati", "sadesati", "saturn"):
        return {"ok": True, "calculator": "Sade Sati Status", "headline": ss_phase, "subline": f"Moon: {rmeta['en']} | Transit Saturn: {RASHI_META[sat_sign]['en']}", "summary": ss_desc, "highlights": [f"Phase: {ss_phase}", f"Saturn Sign: {RASHI_META[sat_sign]['en']}", "Practice: Maintain steady Saturday routines."]}
    return {"ok": True, "calculator": "Moon Sign (Rashi)", "headline": f"{rmeta['en']} ({rashi}) Moon", "subline": f"Lord: {rmeta['lord']} | Nakshatra: {nak} (Pada {pada})", "summary": f"Your Chandra Rashi is {rmeta['en']} ({rashi}), ruled by {rmeta['lord']}, highlighting {rmeta['theme']}.", "highlights": [f"Moon Sign: {rmeta['en']}", f"Nakshatra: {nak}", f"Mulank/Bhagyank: {prof['mulank']}/{prof['bhagyank']}"]}


def daily_horoscope_all(lang: str = "en") -> Dict[str, Any]:
    panchang = compute_panchang()
    m_idx = RASHIS.index(panchang["active_rashi"])
    pool = [
        ("Lead with warmth, not urgency.", "A generous Moon-Jupiter exchange opens sincere conversations. Keep plans flexible after sunset."),
        ("Protect your focus.", "Steady effort on one priority brings more progress today than juggling scattered tasks."),
        ("Clear words prevent misunderstandings.", "Mercury supports calm dialogue; state expectations gently and listen fully."),
        ("Honour your domestic rhythm.", "Small adjustments to your rest or workspace restore clarity today."),
        ("Step forward with composed confidence.", "Pair natural initiative with patience for others' timelines."),
        ("Refine details before committing.", "Review schedules and numbers carefully; precision saves effort later."),
        ("Choose balance over pleasing everyone.", "Harmony improves when boundaries are stated clearly and kindly."),
        ("Trust quiet observation.", "Pause before reacting to emotional tension so deeper clarity can surface."),
        ("Keep your long-term vision steady.", "A thoughtful conversation or study session sparks fresh perspective."),
        ("Build one durable habit today.", "Consistent structure turns small daily steps into lasting momentum."),
        ("Step back for wider perspective.", "Trusted peers offer a helpful angle on a recurring question."),
        ("Listen to intuition without rushing.", "Quiet reflection clarifies what deserves your energy today."),
    ]
    signs = [{"key": r, "en": RASHI_META[r]["en"], "hi": RASHI_META[r]["hi"], "symbol": RASHI_META[r]["symbol"], "lord": RASHI_META[r]["lord"], "headline": pool[(i - m_idx) % 12][0], "reading": pool[(i - m_idx) % 12][1]} for i, r in enumerate(RASHIS)]
    return {"ok": True, "date": panchang["date_label"], "tithi": panchang["tithi"], "signs": signs}


def generate_report(topic: str, profile: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    prof = summarize_profile(profile)
    solved = solve_problem({"profile": profile, "category": topic, "lang": lang})
    titles = {"career": "Career & Purpose Blueprint", "marriage": "Love & Marriage Report", "love": "Love & Marriage Report", "wealth": "Wealth Path Report", "year": "Your Year Ahead"}
    return {"ok": True, "title": titles.get((topic or "career").lower(), "Personalised Vedic Report"), "profile": prof, "score": solved["score"], "window": solved["window"], "summary": solved["answer"], "why": solved["why"], "watchout": solved["watchout"], "steps": solved["steps"], "practice": solved["practice"]}


def ask_astromuni_v09(payload: Dict[str, Any]) -> Dict[str, Any]:
    mode = (payload.get("mode") or "muni").strip().lower()
    q = (payload.get("question") or "").strip()
    lang = payload.get("lang") if payload.get("lang") in ("en", "hi", "hg") else "en"
    profile = payload.get("profile") or {}
    hits = search_shastra_corpus(q, limit=2)
    if mode == "astropedia":
        m = next((it for it in ASTROPEDIA_TOPICS if any(k in q.lower() for k in it["keys"])), None)
        ans = m[lang] if m else (f"From {hits[0]['source']}: {hits[0]['snippet']}" if hits else "Vedic Jyotish reads every chart through Bhavas (houses), planetary dignity, and Vimshottari Dasha timing.")
        return {"ok": True, "mode": "astropedia", "title": m["title"] if m else "Vedic Jyotish Reference", "answer": ans, "proof": [f"Source: {h['source']}" for h in hits] or ["Classical Jyotish Reference"], "lang": lang}
    prof = summarize_profile(profile)
    solved = solve_problem({"profile": profile, "question": q, "lang": lang})
    _, store = build_astrobrain_store(_to_birth_input(profile), palm_obs=_to_palm_obs(payload.get("palm")))
    proof = [solved["why"]] + [f"[{f.system.upper()}] {f.interpretation}" for f in evaluate_astrobrain_rules(store).firings[:3]]
    return {"ok": True, "mode": "muni", "title": solved["heading"], "answer": solved["answer"], "window": solved["window"], "watchout": solved["watchout"], "steps": solved["steps"], "practice": solved["practice"], "profile": prof, "proof": proof, "lang": lang}


def handle_v09(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.startswith("/api/v09/panchang"):
            return compute_panchang(payload.get("city") or "Bhopal", payload.get("profile"))
        if path.startswith("/api/v09/compatibility"):
            return compute_compatibility(payload.get("person_a") or payload.get("profile") or {}, payload.get("person_b") or {"name": "Partner", "dob": "1996-08-18", "tob": "11:15", "city": "Mumbai"}, payload.get("lang") or "en")
        if path.startswith("/api/v09/calculator"):
            return run_calculator(payload.get("type") or "moon", payload.get("profile") or payload, payload.get("lang") or "en")
        if path.startswith("/api/v09/horoscope"):
            return daily_horoscope_all(payload.get("lang") or "en")
        if path.startswith("/api/v09/report"):
            return generate_report(payload.get("topic") or "career", payload.get("profile") or payload, payload.get("lang") or "en")
        if path.startswith("/api/v09/journal"):
            return {"ok": True, "articles": JOURNAL_ARTICLES}
        return ask_astromuni_v09(payload)
    except Exception as exc:
        return {"ok": True, "mode": payload.get("mode", "muni"), "title": "AstroMuni Guidance", "answer": "Your chart patterns favour steady, well-paced decisions today.", "proof": [f"Safe-mode fallback ({type(exc).__name__})"], "steps": ["Focus on one clear priority today."]}
