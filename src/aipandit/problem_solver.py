"""User-first problem-solver & unified Astrobrain guidance helpers (v0.7+)."""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any, Dict, Optional

from .astrobrain_extensions import build_astrobrain_store, evaluate_astrobrain_rules
from .explain import describe_fact
from .intake import BirthInput
from .jyotish import GRAHAS
from .kundli import dasha_at
from .palmistry import PalmObservation

CITY_COORDS = {
    "bhopal": (23.2599, 77.4126, "Asia/Kolkata"),
    "delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "new delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "mumbai": (19.0760, 72.8777, "Asia/Kolkata"),
    "kolkata": (22.5726, 88.3639, "Asia/Kolkata"),
    "chennai": (13.0827, 80.2707, "Asia/Kolkata"),
    "bengaluru": (12.9716, 77.5946, "Asia/Kolkata"),
    "bangalore": (12.9716, 77.5946, "Asia/Kolkata"),
    "hyderabad": (17.3850, 78.4867, "Asia/Kolkata"),
    "jaipur": (26.9124, 75.7873, "Asia/Kolkata"),
    "indore": (22.7196, 75.8577, "Asia/Kolkata"),
    "lucknow": (26.8467, 80.9462, "Asia/Kolkata"),
}


def _to_birth_input(profile: Dict[str, Any]) -> BirthInput:
    name = (profile.get("name") or "Seeker").strip()
    dob_str = (profile.get("dob") or "2001-01-29").strip()
    tob_str = (profile.get("tob") or "09:30").strip()
    city = (profile.get("city") or "Bhopal").strip()
    certainty = (profile.get("time_certainty") or ("exact" if profile.get("tob") else "unknown")).strip()

    default_lat, default_lon, default_tz = CITY_COORDS.get(city.lower(), (23.2599, 77.4126, "Asia/Kolkata"))
    lat = float(profile.get("lat") if profile.get("lat") not in (None, "") else default_lat)
    lon = float(profile.get("lon") if profile.get("lon") not in (None, "") else default_lon)
    tz_name = (profile.get("tz_name") or default_tz).strip()

    return BirthInput(
        name=name,
        date=dob_str,
        time=tob_str if certainty != "unknown" else None,
        time_certainty=certainty,
        place_name=city,
        latitude=lat,
        longitude=lon,
        tz_name=tz_name,
        subject_is_minor=bool(profile.get("subject_is_minor", False)),
    )


def _to_palm_obs(palm_data: Optional[Dict[str, Any]]) -> Optional[PalmObservation]:
    if not palm_data or not isinstance(palm_data, dict):
        return None
    if not any(palm_data.get(k) for k in ("life_line", "head_line", "heart_line", "fate_line", "dominant_mount")):
        return None
    return PalmObservation(
        active_hand=palm_data.get("active_hand") or "right",
        life_line=palm_data.get("life_line") or None,
        head_line=palm_data.get("head_line") or None,
        heart_line=palm_data.get("heart_line") or None,
        fate_line=palm_data.get("fate_line") or None,
        dominant_mount=palm_data.get("dominant_mount") or None,
    )


def summarize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Compute exact profile summary using Vedaksha Kundli + Numerology."""
    b = _to_birth_input(profile)
    today = dt.date.today()
    kundli, store = build_astrobrain_store(b, today=today)

    lagna = store.value("lagna", "sign", "parashari") or "Withheld (uncertain birth time)"
    rashi = store.value("Moon", "sign", "parashari") or "Withheld"
    nakshatra = store.value("Moon", "nakshatra", "parashari") or "Withheld"
    mulank = store.value("mulank", "value", "numerology") or 1
    bhagyank = store.value("bhagyank", "value", "numerology") or 1

    maha_lord = "Withheld"
    antara_lord = "Withheld"
    if kundli.dasha is not None:
        try:
            d = dasha_at(kundli, dt.datetime.now(dt.timezone.utc))
            maha_lord = d.get("maha") or "Withheld"
            antara_lord = d.get("antar") or "Withheld"
        except ValueError:
            pass

    return {
        "name": b.name,
        "dob": b.date,
        "tob": b.time or "",
        "city": b.place_name,
        "lagna": lagna,
        "rashi": rashi,
        "nakshatra": nakshatra,
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
    if any(w in txt for w in ["educat", "study", "exam", "college", "padhai", "degree", "learn"]):
        return "education"
    if any(w in txt for w in ["child", "kids", "santan", "bachch", "aulad", "baby"]):
        return "children"
    if any(w in txt for w in ["family", "parents", "mother", "father", "parivar", "ghar"]):
        return "family"
    if any(w in txt for w in ["stress", "peace", "mind", "mann", "overthink", "sleep", "focus", "calm"]):
        return "mind"
    if any(w in txt for w in ["when", "time", "kab", "window", "timing", "month", "year"]):
        return "timing"
    return "general"


def solve_problem(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_prof = payload.get("profile") or {}
    prof = summarize_profile(raw_prof)
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
        "education": {
            "heading": "Education & Skill Mastery",
            "en": f"Structured daily revision beats last-minute cramming. Your {prof['nakshatra']} placement and {prof['mahadasha']} phase favour steady conceptual depth.",
            "hi": f"अंतिम समय की भागदौड़ के बजाय नियमित अभ्यास से बेहतर परिणाम मिलते हैं। {prof['nakshatra']} नक्षत्र और {prof['mahadasha']} दशा गहरी समझ का समर्थन करती है।",
            "hg": f"Last-minute cramming ke bajay daily structured practice best rehti hai. Aapka {prof['nakshatra']} nakshatra aur {prof['mahadasha']} daur deep learning ko support karta hai.",
            "window": "Next 30 to 90 days",
            "watchout": "Avoid switching study materials or courses mid-way.",
            "steps": [
                "Block 60 uninterrupted minutes each morning for core study.",
                "Summarize each topic in your own words once a week.",
                "Test yourself with practical problems before moving on.",
            ],
            "practice": "Keep a single study notebook and review it every Thursday morning.",
        },
        "children": {
            "heading": "Children & Mentorship",
            "en": f"Patient listening and consistent routines create a supportive environment. Your {prof['rashi']} Moon and {prof['mahadasha']} period reward steady encouragement.",
            "hi": f"धैर्यपूर्वक सुनने और नियमित दिनचर्या से सकारात्मक माहौल बनता है। आपकी {prof['rashi']} राशि और {prof['mahadasha']} दशा निरंतर प्रोत्साहन का संकेत देती है।",
            "hg": f"Dhairya se sunne aur regular routine se supportive environment banta hai. Aapki {prof['rashi']} rashi aur {prof['mahadasha']} daur steady encouragement ko support karta hai.",
            "window": "Next 60 to 120 days",
            "watchout": "Avoid comparing milestones with other families.",
            "steps": [
                "Set aside 20 distraction-free minutes daily for open conversation.",
                "Encourage curiosity and effort rather than only outcomes.",
                "Keep family meal and rest routines predictable.",
            ],
            "practice": "Share one calm, screen-free meal together every day.",
        },
        "family": {
            "heading": "Family & Home Harmony",
            "en": f"Clear boundaries paired with warmth keep household decisions smooth. Your {prof['lagna']} chart and {prof['mahadasha']} phase favour respectful dialogue.",
            "hi": f"आत्मीयता के साथ स्पष्ट संवाद पारिवारिक निर्णयों को सहज बनाता है। आपकी {prof['lagna']} कुंडली और {prof['mahadasha']} दशा सौहार्दपूर्ण बातचीत का समर्थन करती है।",
            "hg": f"Garmjoshi ke saath clear communication se ghar ke decisions smooth rehte hain. Aapka {prof['lagna']} chart aur {prof['mahadasha']} daur respectful dialogue ko support karta hai.",
            "window": "Next 45 to 90 days",
            "watchout": "Avoid letting minor misunderstandings go unspoken for weeks.",
            "steps": [
                "Address household responsibilities clearly in a calm family chat.",
                "Respect elders' perspectives while stating your own bandwidth honestly.",
                "Plan one shared family activity this month.",
            ],
            "practice": "Check in calmly with parents or family members every Sunday morning.",
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
        "version": "0.8-astrobrain",
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


def evaluate_unified_astrobrain(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return unified readings across Kundli, Numerology, Palmistry & Gochara."""
    b = _to_birth_input(payload.get("profile") or payload)
    palm_obs = _to_palm_obs(payload.get("palm"))
    lang = (payload.get("lang") or "en").strip().lower()
    today = dt.date.today()

    _, store = build_astrobrain_store(b, palm_obs=palm_obs, transit_date=today, today=today)
    res = evaluate_astrobrain_rules(store)

    planets = {
        g: {
            "sign": store.value(g, "sign", "parashari"),
            "house": store.value(g, "house", "parashari"),
            "nakshatra": store.value(g, "nakshatra", "parashari"),
            "retrograde": store.value(g, "retrograde", "parashari"),
        }
        for g in GRAHAS
    }

    readings = []
    for f in res.firings:
        readings.append(
            {
                "rule_id": f.rule_id,
                "system": f.system,
                "scope": list(f.scope),
                "adverse": f.adverse,
                "review_status": f.review_status,
                "interpretation": f.interpretation,
                "basis": [describe_fact(store, fid, lang if lang in ("en", "hi", "hg") else "en") for fid in f.fact_ids],
            }
        )

    return {
        "ok": True,
        "version": "0.8-astrobrain",
        "profile": summarize_profile(payload.get("profile") or payload),
        "planets": planets,
        "total_facts": len(store),
        "total_firings": len(readings),
        "readings": readings,
    }


def handle_v07(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if path.startswith("/api/v07/astrobrain"):
        return evaluate_unified_astrobrain(payload)
    if path.startswith("/api/v07/snapshot"):
        prof = summarize_profile(payload.get("profile") or payload)
        areas = []
        for k, lbl in [
            ("career", "Career"),
            ("marriage", "Marriage & Rishte"),
            ("wealth", "Money & Stability"),
            ("education", "Education & Learning"),
            ("family", "Family & Home"),
            ("mind", "Mind & Peace"),
        ]:
            res = solve_problem({"profile": prof, "category": k, "lang": payload.get("lang", "hg")})
            areas.append({"key": k, "label": lbl, "score": res["score"], "window": res["window"], "answer": res["answer"]})
        return {"ok": True, "profile": prof, "areas": areas}
    return solve_problem(payload)
