"""User-first problem-solver & life guidance helpers for AstroMuni v0.7."""
from __future__ import annotations

import datetime as dt
import hashlib
import math
from typing import Any, Dict

CITY_COORDS = {
    "bhopal": (23.2599, 77.4126),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "jaipur": (26.9124, 75.7873),
    "indore": (22.7196, 75.8577),
    "lucknow": (26.8467, 80.9462),
}

RASHIS = [
    ("Mesha", "Mars"), ("Vrishabha", "Venus"), ("Mithuna", "Mercury"),
    ("Karka", "Moon"), ("Simha", "Sun"), ("Kanya", "Mercury"),
    ("Tula", "Venus"), ("Vrischika", "Mars"), ("Dhanu", "Jupiter"),
    ("Makara", "Saturn"), ("Kumbha", "Saturn"), ("Meena", "Jupiter"),
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

DASHA_SEQ = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7),
    ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]


def _root_digit(n: int) -> int:
    while n > 9:
        n = sum(int(ch) for ch in str(n))
    return n or 1


def summarize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    name = (profile.get("name") or "Seeker").strip()
    dob_str = (profile.get("dob") or "2001-01-29").strip()
    tob_str = (profile.get("tob") or "09:30").strip()
    city = (profile.get("city") or "Bhopal").strip()

    try:
        dob = dt.date.fromisoformat(dob_str)
    except ValueError:
        dob = dt.date(2001, 1, 29)

    try:
        hh, mm = [int(x) for x in tob_str.split(":")[:2]]
    except Exception:
        hh, mm = 9, 30

    fallback_lat, fallback_lon = CITY_COORDS.get(city.lower(), (23.2599, 77.4126))
    lat = float(profile.get("lat") if profile.get("lat") not in (None, "") else fallback_lat)
    lon = float(profile.get("lon") if profile.get("lon") not in (None, "") else fallback_lon)

    mulank = _root_digit(dob.day)
    bhagyank = _root_digit(sum(int(c) for c in dob.strftime("%Y%m%d")))

    jdn = dob.toordinal() + 1721424.5 + (hh + mm / 60.0 - 5.5) / 24.0
    days_j2000 = jdn - 2451545.0
    ayanamsa = 23.85 + (days_j2000 / 36525.0) * 1.396
    moon_sid = ((218.316 + 13.176396 * days_j2000) - ayanamsa) % 360.0
    lst = (100.46 + 0.985647 * days_j2000 + lon + (hh + mm / 60.0 - 5.5) * 15.0) % 360.0
    lagna_sid = (lst - ayanamsa + math.sin(math.radians(lat)) * 12.0) % 360.0

    lagna_idx = int(lagna_sid // 30) % 12
    moon_idx = int(moon_sid // 30) % 12
    nak_idx = int(moon_sid // (360.0 / 27.0)) % 27

    age = max(0.0, (dt.date.today() - dob).days / 365.25)
    maha_idx = nak_idx % 9
    maha_lord = DASHA_SEQ[maha_idx][0]
    antara_lord = DASHA_SEQ[(maha_idx + int(age * 2) + 1) % 9][0]

    return {
        "name": name,
        "dob": dob_str,
        "tob": tob_str,
        "city": city,
        "lagna": RASHIS[lagna_idx][0],
        "rashi": RASHIS[moon_idx][0],
        "nakshatra": NAKSHATRAS[nak_idx],
        "mahadasha": maha_lord,
        "antardasha": antara_lord,
        "mulank": mulank,
        "bhagyank": bhagyank,
    }


def _topic_key(question: str, category: str) -> str:
    txt = f"{category} {question}".lower()
    if any(w in txt for w in ["job", "career", "switch", "work", "office", "role", "naukri", "promotion"]):
        return "career"
    if any(w in txt for w in ["marri", "shaadi", "risht", "love", "partner", "husband", "wife", "relationship"]):
        return "marriage"
    if any(w in txt for w in ["money", "wealth", "dhan", "paisa", "business", "invest", "income", "finance"]):
        return "wealth"
    if any(w in txt for w in ["stress", "peace", "mind", "mann", "overthink", "sleep", "focus", "calm"]):
        return "mind"
    if any(w in txt for w in ["when", "time", "kab", "window", "timing", "month", "year"]):
        return "timing"
    return "general"


def solve_problem(payload: Dict[str, Any]) -> Dict[str, Any]:
    prof = summarize_profile(payload.get("profile") or {})
    q = (payload.get("question") or "").strip()
    cat = _topic_key(q, (payload.get("category") or "general").strip())
    lang = (payload.get("lang") or "hg").strip().lower()
    seed = int(hashlib.sha256(f"{prof['dob']}:{cat}:{q}".encode()).hexdigest()[:8], 16)
    score = 66 + (seed % 25)

    copy_map = {
        "career": {
            "heading": "Career & Next Step",
            "en": f"Focus on clear role scope before switching. Your {prof['mahadasha']}–{prof['antardasha']} period supports planned progress over rushed moves.",
            "hi": f"बदलाव से पहले अपनी भूमिका और शर्तें स्पष्ट रखें। आपकी {prof['mahadasha']}–{prof['antardasha']} दशा जल्दबाजी के बजाय सोच-समझकर आगे बढ़ने का संकेत देती है।",
            "hg": f"Switch karne se pehle role aur terms clear rakhein. Aapka {prof['mahadasha']}–{prof['antardasha']} daur jaldbazi ki jagah planned progress ko support karta hai.",
            "window": "Next 45 to 90 days",
            "watchout": "Avoid resigning before written terms are confirmed.",
            "steps": [
                "List your top 3 target roles or deliverables this week.",
                "Clarify responsibilities, reporting line, and compensation before committing.",
                "Review progress every Thursday morning.",
            ],
            "practice": "Spend 10 quiet minutes every Thursday morning setting weekly priorities.",
        },
        "marriage": {
            "heading": "Marriage & Relationships",
            "en": f"Calm, direct conversation works better than silent assumptions. Your {prof['rashi']} Moon and {prof['mahadasha']}–{prof['antardasha']} phase favour clarity and mutual respect.",
            "hi": f"अनुमान लगाने के बजाय शांत और स्पष्ट बातचीत से स्थिति सुधरती है। आपकी {prof['rashi']} राशि और {prof['mahadasha']}–{prof['antardasha']} दशा स्पष्टता और तालमेल का संकेत देती है।",
            "hg": f"Assumptions ke bajay shant aur clear baat-cheet se clarity aati hai. Aapki {prof['rashi']} rashi aur {prof['mahadasha']}–{prof['antardasha']} daur samajh aur balance ko support karta hai.",
            "window": "Next 60 to 120 days",
            "watchout": "Do not react immediately when emotions run high.",
            "steps": [
                "Share expectations calmly without bringing up old disputes.",
                "Discuss daily routine and long-term plans openly.",
                "Pause major decisions for a few days during arguments.",
            ],
            "practice": "Take 5 slow breaths before starting sensitive family conversations.",
        },
        "wealth": {
            "heading": "Money & Stability",
            "en": f"Steady cashflow comes from controlling leaks and building repeatable habits. With Mulank {prof['mulank']} and {prof['mahadasha']} period, keep risk measured.",
            "hi": f"खर्चों पर नियंत्रण और नियमित आदतों से आर्थिक स्थिरता बनती है। मूलांक {prof['mulank']} और {prof['mahadasha']} दशा के साथ जोखिम संतुलित रखें।",
            "hg": f"Expense control aur regular habits se stability aati hai. Mulank {prof['mulank']} aur {prof['mahadasha']} daur mein risk ko balance mein rakhein.",
            "window": "Next 30 to 60 days",
            "watchout": "Avoid high-risk or unverified commitments.",
            "steps": [
                "Track recurring expenses and pending dues this week.",
                "Set aside a fixed portion of incoming funds first.",
                "Keep decisions grounded in written numbers.",
            ],
            "practice": "Review weekly cashflow every Friday evening.",
        },
        "mind": {
            "heading": "Mind, Peace & Focus",
            "en": f"Reducing open tasks restores mental calm faster than over-planning. Your {prof['nakshatra']} placement benefits from a steady daily rhythm.",
            "hi": f"अनावश्यक कार्यों को कम करने से मन जल्दी शांत होता है। {prof['nakshatra']} नक्षत्र के साथ नियमित दिनचर्या से एकाग्रता बेहतर रहती है।",
            "hg": f"Extra open tasks kam karne se mann jaldi shant hota hai. Aapke {prof['nakshatra']} nakshatra ke liye regular routine sabse helpful hai.",
            "window": "Next 21 days",
            "watchout": "Avoid making big decisions late at night when tired.",
            "steps": [
                "Pick 2 main priorities each morning and park the rest.",
                "Cut screen time 45 minutes before sleep.",
                "Spend 15 minutes outdoors in morning daylight.",
            ],
            "practice": "Do 10 minutes of calm breathing after waking up.",
        },
        "timing": {
            "heading": "Timing & Readiness",
            "en": f"Use the next few weeks to prepare documents, skills, and alignment so you can act cleanly when the window opens under {prof['mahadasha']}–{prof['antardasha']}.",
            "hi": f"अगले कुछ सप्ताह तैयारी और तालमेल के लिए रखें ताकि {prof['mahadasha']}–{prof['antardasha']} के अनुकूल समय में आप स्पष्ट कदम उठा सकें।",
            "hg": f"Agle kuch hafte tayari aur alignment ke liye rakhein taaki {prof['mahadasha']}–{prof['antardasha']} ke daur mein aap clean step le sakein.",
            "window": "Next 30 to 90 days",
            "watchout": "Do not rush purely out of comparison with others.",
            "steps": [
                "Finish groundwork and verification first.",
                "Keep a realistic buffer in dates and budget.",
                "Take one concrete step once readiness is clear.",
            ],
            "practice": "Write down your 30-day milestone and check it every Sunday.",
        },
        "general": {
            "heading": "Practical Direction",
            "en": f"Finish what is already in motion before adding new burdens. Your {prof['lagna']} chart and {prof['mahadasha']}–{prof['antardasha']} period favour focused execution.",
            "hi": f"नया बोझ बढ़ाने से पहले चल रहे कामों को पूरा करें। आपकी {prof['lagna']} कुंडली और {prof['mahadasha']}–{prof['antardasha']} दशा केंद्रित प्रयास का समर्थन करती है।",
            "hg": f"Naye bojh se pehle chalte kaam complete karein. Aapka {prof['lagna']} chart aur {prof['mahadasha']}–{prof['antardasha']} daur focused action ko support karta hai.",
            "window": "Next 30 to 60 days",
            "watchout": "Avoid scattering attention across too many parallel goals.",
            "steps": [
                "Choose one primary goal for the month.",
                "Drop or delay one low-value commitment.",
                "Take one practical action today.",
            ],
            "practice": "Spend 10 quiet minutes every Sunday evening planning the week ahead.",
        },
    }

    item = copy_map[cat]
    answer = item["hi"] if lang == "hi" else (item["hg"] if lang == "hg" else item["en"])
    return {
        "ok": True,
        "version": "0.7",
        "category": cat,
        "heading": item["heading"],
        "question": q or item["heading"],
        "answer": answer,
        "score": score,
        "window": item["window"],
        "watchout": item["watchout"],
        "why": f"Lagna: {prof['lagna']} • Moon Rashi: {prof['rashi']} • Nakshatra: {prof['nakshatra']} • Dasha: {prof['mahadasha']}–{prof['antardasha']} • Mulank {prof['mulank']}/Bhagyank {prof['bhagyank']}.",
        "steps": item["steps"],
        "practice": item["practice"],
        "profile": prof,
    }


def handle_v07(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if path.startswith("/api/v07/snapshot"):
        prof = summarize_profile(payload.get("profile") or payload)
        areas = []
        for k, lbl in [("career", "Career"), ("marriage", "Marriage & Rishte"), ("wealth", "Money & Stability"), ("mind", "Mind & Peace")]:
            res = solve_problem({"profile": prof, "category": k, "lang": payload.get("lang", "hg")})
            areas.append({"key": k, "label": lbl, "score": res["score"], "window": res["window"], "answer": res["answer"]})
        return {"ok": True, "profile": prof, "areas": areas}
    return solve_problem(payload)
