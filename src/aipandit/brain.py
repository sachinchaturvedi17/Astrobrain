"""AstroMuni v1.0 brain: chart facts + classical rules + retrieval -> a grounded, explainable answer.

Principle (unchanged): the engine computes, the language layer only interprets. This module takes an already
computed `chart` dict (no astronomy here, so it is fully unit-testable) and a question, and returns:

  {title, answer, reasons[], timing, evidence[], followups[], confidence{level,why}, caveats[], composer, safety}

Every statement in `reasons` is derived from a named chart fact. Nothing is random and nothing is scored with a
made-up number: strength is a label with the reasons that produced it. An optional LLM composer may *rewrite* the
final prose, but only from the structured facts and retrieved passages, and the template answer is always kept as
the fallback and as the `reasons` list.

chart = {
  "lagna": "Simha",
  "moon": {"sign": "Karka", "nakshatra": "Pushya"},
  "planets": {"Sun": {"sign": "Simha", "house": 1, "retrograde": False}, ...},
  "dasha": {"maha": "Venus", "antar": "Sun", "maha_end": "2031-05-01", "antar_end": "2027-03-01"},
  "time_certainty": "exact" | "approx_15min" | "part_of_day" | "unknown",
  "withheld": ["Lagna sign", ...],
}
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from . import doshas, retrieval, voice
from .ashtakoota import LORD as SIGN_LORD, RASHIS
from .kb_core import SIGNS as _SIGNS

SIGN_HI = {k: hi for k, _en, hi, *_ in _SIGNS}

TOPICS = {
    "career": {"houses": (10, 6, 2), "karaka": ("Sun", "Saturn", "Mercury")},
    "wealth": {"houses": (2, 11, 9), "karaka": ("Jupiter", "Venus")},
    "marriage": {"houses": (7, 2, 11), "karaka": ("Venus", "Jupiter")},
    "education": {"houses": (4, 5, 9), "karaka": ("Mercury", "Jupiter")},
    "children": {"houses": (5, 9, 2), "karaka": ("Jupiter",)},
    "health": {"houses": (1, 6, 8), "karaka": ("Sun", "Moon")},
    "family": {"houses": (4, 2, 3), "karaka": ("Moon", "Jupiter")},
    "general": {"houses": (1, 5, 9), "karaka": ("Sun", "Moon")},
    "foreign": {"houses": (12, 9, 3), "karaka": ("Rahu", "Saturn")},
    "property": {"houses": (4, 11, 2), "karaka": ("Mars", "Venus")},
}
KEYWORDS = {
    "foreign": r"abroad|foreign|videsh|visa|immigra|settle in|pardes|study in (usa|uk|canada|australia|germany)|विदेश",
    "property": r"property|\bflat\b|\bplot\b|real estate|buy (a |my )?(house|home|car|vehicle|land)|makaan|zameen|jameen|वाहन|जमीन|मकान|संपत्ति",
    "career": r"career|job|naukri|work|profession|business|promotion|office|startup|resign|interview|sarkari|govt|नौकरी|करियर|व्यवसाय",
    "wealth": r"wealth|money|pais[ae]|dhan|income|finance|salary|savings|धन|पैस[ाे]|आय",
    "marriage": r"marri|shaadi|shadi|vivah|spouse|partner|love|relationship|boyfriend|girlfriend|breakup|break up|crush|propose|pyaar|ex back|शादी|विवाह|प्रेम|रिश्त",
    "education": r"educat|study|studi|exam|padhai|college|degree|vidya|neet|jee\b|upsc|admission|scholarship|result|पढ़ाई|शिक्षा|परीक्षा",
    "children": r"child|baby|santan|bachch|pregnan|संतान|बच्च",
    "health": r"health|sehat|swasthya|body|energy|स्वास्थ्य|सेहत",
    "family": r"family|parents|mother|father|home|ghar|परिवार|माता|पिता|घर",
}
INTENT_OTHER = {
    "manglik": r"mangli[ck]|mangal dosh|kuja dosh|मांगलिक|मंगल दोष",
    "kaalsarp": r"kaal ?sarp|kal ?sarp|काल ?सर्प",
    "panchang": r"rahu ?kaal|rahukalam|abhijit|muhurat|muhurta|panchang|tithi|पंचांग|राहु ?काल|मुहूर्त",
    "match": r"kundli ?milan|kundali ?milan|gun ?milan|guna ?milan|matchmaking|match making|compatib|ashtakoota|कुंडली ?मिलान|गुण ?मिलान",
    "dasha": r"dasha|mahadasha|antardasha|period|phase|daur|दौर|दशा|महादशा",
    "transit": r"transit|gochar|gochara|today|this week|abhi|गोचर",
    "sade_sati": r"sade ?sati|साढ़ेसाती|shani.*(sati|dhaiya)",
    "remedy": r"remedy|upay|upaya|totka|उपाय|mantra|gemstone|ratna|puja|pooja|पूजा",
}
EXALT = {"Sun": "Mesha", "Moon": "Vrishabha", "Mars": "Makara", "Mercury": "Kanya", "Jupiter": "Karka", "Venus": "Meena", "Saturn": "Tula"}
DEBIL = {"Sun": "Tula", "Moon": "Vrishchika", "Mars": "Karka", "Mercury": "Meena", "Jupiter": "Makara", "Venus": "Kanya", "Saturn": "Mesha"}
BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFIC = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
GOOD_LORD_HOUSES = {1, 4, 5, 7, 9, 10, 11}
HARD_LORD_HOUSES = {6, 8, 12}
UPACHAYA = {3, 6, 10, 11}

SAFETY = [
    ("self_harm", r"suicide|kill myself|end my life|want to die|aatmahatya|marna chahta|marna chahti|आत्महत्या|जान दे|मरना चाहता|मरना चाहती"),
    ("death", r"when will i die|how long.*live|lifespan|my death|age of death|maut|मृत्यु कब|कब मरूंगा|कब मरूँगा|आयु कितनी"),
    ("medical", r"cancer|diagnos|surgery|medicine|tumou?r|pregnan|miscarr|disease|bimari|बीमारी|इलाज|गर्भ"),
    ("financial", r"stock|shares?|crypto|bitcoin|lottery|satta|gambl|intraday|trading|mutual fund|शेयर|सट्टा|लॉटरी"),
    ("legal", r"court case|verdict|jail|lawsuit|divorce case|fir |मुकदमा|कोर्ट"),
]
SAFETY_TEXT = {
    "self_harm": {"en": "I'm really sorry you are going through this. Please reach out to someone right now: a trusted person near you, or your local emergency number. In India you can call Tele-MANAS at 14416. You do not have to carry this alone, and I would like to know you are safe.",
                  "hg": "Mujhe bahut afsos hai ki aap yeh sab jhel rahe hain. Kripya abhi kisi apne se baat karein ya apne local emergency number par call karein. India mein aap Tele-MANAS 14416 par call kar sakte hain. Aap akele nahi hain.",
                  "hi": "मुझे बहुत दुख है कि आप यह सब झेल रहे हैं। कृपया अभी किसी अपने से बात करें या अपने स्थानीय आपातकालीन नंबर पर कॉल करें। भारत में आप Tele-MANAS 14416 पर कॉल कर सकते हैं। आप अकेले नहीं हैं।"},
    "death": {"en": "Jyotish does not give a trustworthy date or age of death, and I will not guess one. I can instead look at the themes of your current period, your wellbeing habits, or a question about your work or relationships.",
              "hg": "Jyotish mrityu ki tarikh ya umra nahi bata sakta aur main andaaza nahi lagaunga. Main aapki current dasha, sehat ki aadaton, kaam ya rishton ke baare mein bata sakta hoon.",
              "hi": "ज्योतिष मृत्यु की तिथि या आयु का भरोसेमंद अनुमान नहीं देता और मैं अंदाज़ा नहीं लगाऊँगा। मैं आपकी वर्तमान दशा, स्वास्थ्य की आदतों, काम या रिश्तों पर बात कर सकता हूँ।"},
    "medical": {"en": "I can't give medical advice or predict illness or pregnancy from a chart. Please speak to a qualified doctor. I'm happy to talk about the general themes of your health house or your current period.",
                "hg": "Main medical salah nahi de sakta aur chart se bimari ya garbh ki prediction nahi karta. Kripya doctor se milein. Main aapke health bhav ya dasha ki general baatein bata sakta hoon.",
                "hi": "मैं चिकित्सा सलाह नहीं दे सकता और कुंडली से बीमारी या गर्भ की भविष्यवाणी नहीं करता। कृपया डॉक्टर से मिलें। मैं स्वास्थ्य भाव या दशा के सामान्य विषयों पर बात कर सकता हूँ।"},
    "financial": {"en": "I can't tell you what to buy, sell or bet on. A chart shows your general relationship with money and timing themes, not market outcomes. For investments please use a licensed advisor.",
                  "hg": "Main nahi bata sakta ki kya kharidein, bechein ya daanv lagayein. Chart paise ke saath aapke general rishte aur timing dikhata hai, market nahi. Nivesh ke liye licensed advisor se milein.",
                  "hi": "मैं नहीं बता सकता कि क्या खरीदें, बेचें या दाँव लगाएँ। कुंडली पैसे से आपके सामान्य संबंध और समय के विषय दिखाती है, बाज़ार नहीं। निवेश के लिए लाइसेंस प्राप्त सलाहकार से मिलें।"},
    "legal": {"en": "I can't predict the outcome of a court case. Please rely on your lawyer. I can talk about general themes of your current period if that helps.",
              "hg": "Main court case ke nateeje ki prediction nahi kar sakta. Apne vakeel par bharosa karein. Chahein to main dasha ke general themes bata sakta hoon.",
              "hi": "मैं अदालती मामले के नतीजे की भविष्यवाणी नहीं कर सकता। कृपया अपने वकील पर भरोसा करें। चाहें तो मैं दशा के सामान्य विषय बता सकता हूँ।"},
}

T = {
    "title": {"career": ("Career & purpose", "Career aur purpose", "करियर और उद्देश्य"), "wealth": ("Wealth path", "Dhan ka marg", "धन का मार्ग"),
              "marriage": ("Love & marriage", "Pyaar aur vivah", "प्रेम और विवाह"), "education": ("Education", "Shiksha", "शिक्षा"),
              "children": ("Children", "Santan", "संतान"), "health": ("Wellbeing", "Sehat", "स्वास्थ्य"), "family": ("Family & home", "Parivaar aur ghar", "परिवार और घर"),
              "general": ("Your chart in brief", "Aapka chart sankshep mein", "आपकी कुंडली संक्षेप में"), "dasha": ("Your current dasha", "Aapki current dasha", "आपकी वर्तमान दशा"),
              "transit": ("Transits now", "Abhi ke gochar", "अभी के गोचर"), "sade_sati": ("Sade Sati", "Sade Sati", "साढ़ेसाती"),
              "remedy": ("Traditional practices", "Parampara ke upay", "परंपरागत उपाय"), "foreign": ("Going abroad", "Videsh yog", "विदेश योग"),
              "property": ("Property & home", "Property aur ghar", "संपत्ति और घर"), "manglik": ("Manglik check", "Manglik jaanch", "मांगलिक जाँच"),
              "kaalsarp": ("Kaal Sarp check", "Kaal Sarp jaanch", "काल सर्प जाँच"), "panchang": ("Panchang", "Panchang", "पंचांग"), "match": ("Kundli matching", "Kundli milan", "कुंडली मिलान"), "concept": ("From the reference", "Sandarbh se", "संदर्भ से")},
    "lord": ("Your {ho} house ({sign}) is ruled by {lord}, which sits in your {lh}{lhs} house ({lsign}).",
             "Aapka {h}ve bhav ({sign}) ka swami {lord} hai, jo aapke {lh}ve bhav ({lsign}) mein hai.",
             "आपके {h}वें भाव ({sign}) का स्वामी {lord} है, जो आपके {lh}वें भाव ({lsign}) में है।"),
    "good": ("That placement tends to support this area.", "Yeh sthiti is kshetra ko saath deti hai.", "यह स्थिति इस क्षेत्र को सहयोग देती है।"),
    "hard": ("That placement asks for extra effort in this area.", "Yeh sthiti is kshetra mein adhik mehnat maangti hai.", "यह स्थिति इस क्षेत्र में अधिक परिश्रम माँगती है।"),
    "exalted": ("{lord} is exalted, which strengthens it.", "{lord} uchch ka hai, jo ise majboot karta hai.", "{lord} उच्च का है, जो इसे मजबूत करता है।"),
    "own": ("{lord} is in its own sign, which strengthens it.", "{lord} apni rashi mein hai, jo ise majboot karta hai.", "{lord} अपनी राशि में है, जो इसे मजबूत करता है।"),
    "debil": ("{lord} is in its fall, so results here come with extra effort.", "{lord} neech ka hai, isliye is kshetra mein adhik prayas lagta hai.", "{lord} नीच का है, इसलिए इस क्षेत्र में अधिक प्रयास लगता है।"),
    "occ_good": ("{p} in this house is a traditional support.", "Is bhav mein {p} parampara se sahayak mana jata hai.", "इस भाव में {p} परंपरा से सहायक माना जाता है।"),
    "occ_hard": ("{p} in this house adds intensity and calls for patience.", "Is bhav mein {p} tivrata laata hai aur dhairya maangta hai.", "इस भाव में {p} तीव्रता लाता है और धैर्य माँगता है।"),
    "dasha": ("Your {maha}-{antar} period involves {p}, so this area is active now.", "Aapki {maha}-{antar} dasha mein {p} shamil hai, isliye yeh kshetra abhi sakriya hai.", "आपकी {maha}-{antar} दशा में {p} शामिल है, इसलिए यह क्षेत्र अभी सक्रिय है।"),
    "dasha_plain": ("You are in {maha} mahadasha, {antar} antardasha{until}.", "Aap {maha} mahadasha, {antar} antardasha mein hain{until}.", "आप {maha} महादशा, {antar} अंतर्दशा में हैं{until}।"),
    "until": (" (until {d})", " ({d} tak)", " ({d} तक)"),
    "summary_sup": ("Overall the chart supports this area, with the reasons below.", "Kul milakar chart is kshetra ko saath deta hai, kaaran neeche hain.", "कुल मिलाकर कुंडली इस क्षेत्र का साथ देती है, कारण नीचे हैं।"),
    "summary_mix": ("The chart shows a mixed picture for this area, with the reasons below.", "Is kshetra ke liye chart mila-jula chitra dikhata hai, kaaran neeche hain.", "इस क्षेत्र के लिए कुंडली मिला-जुला चित्र दिखाती है, कारण नीचे हैं।"),
    "summary_dem": ("This area asks for patience and steady effort, for the reasons below.", "Yeh kshetra dhairya aur nirantar prayas maangta hai, kaaran neeche hain.", "यह क्षेत्र धैर्य और निरंतर प्रयास माँगता है, कारण नीचे हैं।"),
    "need_chart": ("I would love to answer this from your own chart. Please add your birth details first, it takes about a minute. Meanwhile, here is what tradition says:", "Main isse aapke apne chart se batana chahta hoon. Pehle apni janm details jodein, bas ek minute lagega. Tab tak parampara yeh kehti hai:", "मैं इसे आपकी अपनी कुंडली से बताना चाहता हूँ। पहले अपनी जन्म जानकारी जोड़ें, बस एक मिनट लगेगा। तब तक परंपरा यह कहती है:"),
    "no_hit": ("I could not find a reliable passage for that in my knowledge base. Try asking about a planet, house, sign, nakshatra, dasha or yoga.", "Mere gyaan-aadhar mein iska bharosemand jawab nahi mila. Graha, bhav, rashi, nakshatra, dasha ya yoga ke baare mein poochhein.", "मेरे ज्ञान-आधार में इसका भरोसेमंद उत्तर नहीं मिला। ग्रह, भाव, राशि, नक्षत्र, दशा या योग के बारे में पूछें।"),
}
CAVEATS = {"en": ["Jyotish shows tendencies and timing themes, not certainties."], "hg": ["Jyotish rujhaan aur samay ke sanket deta hai, nishchitata nahi."],
           "hi": ["ज्योतिष रुझान और समय के संकेत देता है, निश्चितता नहीं।"]}
CERT_WHY = {"exact": ("Birth time is exact.", "Janm samay exact hai.", "जन्म समय सटीक है।"),
            "approx_15min": ("Birth time is approximate (within about 15 minutes); house placements near a boundary may change.", "Janm samay lagbhag hai (15 min ke andar); seema ke paas ke bhav badal sakte hain.", "जन्म समय लगभग है (15 मिनट के भीतर); सीमा के पास के भाव बदल सकते हैं।"),
            "part_of_day": ("Only the part of the day is known, so the Lagna and houses are not reliable.", "Sirf din ka hissa pata hai, isliye Lagna aur bhav bharosemand nahi.", "केवल दिन का भाग पता है, इसलिए लग्न और भाव भरोसेमंद नहीं।"),
            "unknown": ("Birth time is unknown, so house-based statements are withheld.", "Janm samay maloom nahi, isliye bhav par aadharit baatein roki gayi hain.", "जन्म समय पता नहीं, इसलिए भाव-आधारित बातें रोकी गई हैं।")}
PL_HI = {"Sun": "सूर्य", "Moon": "चंद्रमा", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}
PL_HG = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"}


def _li(lang: str) -> int:
    return {"en": 0, "hg": 1, "hi": 2}.get(lang, 0)


def _pl(p: str, lang: str) -> str:
    return PL_HI.get(p, p) if lang == "hi" else PL_HG.get(p, p) if lang == "hg" else p


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def check_safety(question: str) -> Optional[str]:
    q = question.lower()
    for kind, pat in SAFETY:
        if re.search(pat, q):
            return kind
    return None


def classify(question: str) -> str:
    q = question.lower()
    for k, pat in INTENT_OTHER.items():
        if re.search(pat, q):
            return k
    for k, pat in KEYWORDS.items():
        if re.search(pat, q):
            return k
    return "concept"


def _tx(key: str, lang: str, **kw: Any) -> str:
    return T[key][_li(lang)].format(**kw)


def analyse_house(chart: Dict[str, Any], house: int, lang: str = "en") -> Dict[str, Any]:
    lagna = chart["lagna"]
    sign = RASHIS[(RASHIS.index(lagna) + house - 1) % 12]
    lord = SIGN_LORD[RASHIS.index(sign)]
    shown = (lambda s: SIGN_HI.get(s, s)) if lang == "hi" else (lambda s: s)
    planets = chart.get("planets", {})
    pts, reasons, basis = 0, [], []
    lp = planets.get(lord)
    if lp and lp.get("house"):
        lh = int(lp["house"])
        reasons.append(_tx("lord", lang, h=house, ho=_ord(house), sign=shown(sign), lord=_pl(lord, lang), lh=lh, lhs=_ord(lh)[len(str(lh)):], lsign=shown(lp["sign"])))
        basis.append(f"{_ord(house)} lord {lord} in house {lh}")
        if lh in GOOD_LORD_HOUSES:
            pts += 1
            reasons.append(_tx("good", lang))
        elif lh in HARD_LORD_HOUSES:
            pts -= 1
            reasons.append(_tx("hard", lang))
        if EXALT.get(lord) == lp["sign"]:
            pts += 1
            reasons.append(_tx("exalted", lang, lord=_pl(lord, lang)))
        elif SIGN_LORD[RASHIS.index(lp["sign"])] == lord:
            pts += 1
            reasons.append(_tx("own", lang, lord=_pl(lord, lang)))
        elif DEBIL.get(lord) == lp["sign"]:
            pts -= 1
            reasons.append(_tx("debil", lang, lord=_pl(lord, lang)))
    occupants = [p for p, v in planets.items() if v.get("house") == house]
    for p in occupants:
        if p in BENEFIC:
            pts += 1
            reasons.append(_tx("occ_good", lang, p=_pl(p, lang)))
        elif house in UPACHAYA and p in MALEFIC:
            pts += 1
            reasons.append(_tx("occ_good", lang, p=_pl(p, lang)))
        else:
            pts -= 1
            reasons.append(_tx("occ_hard", lang, p=_pl(p, lang)))
        basis.append(f"{p} in house {house}")
    return {"house": house, "sign": sign, "lord": lord, "points": pts, "reasons": reasons, "occupants": occupants, "basis": basis}


def _timing(chart: Dict[str, Any], involved: List[str], lang: str) -> List[str]:
    d = chart.get("dasha") or {}
    out: List[str] = []
    if d.get("maha") and d.get("antar"):
        until = _tx("until", lang, d=d["antar_end"]) if d.get("antar_end") else ""
        out.append(_tx("dasha_plain", lang, maha=_pl(d["maha"], lang), antar=_pl(d["antar"], lang), until=until))
        hit = [p for p in (d["maha"], d["antar"]) if p in involved]
        if hit:
            out.append(_tx("dasha", lang, maha=_pl(d["maha"], lang), antar=_pl(d["antar"], lang), p=_pl(hit[0], lang)))
    return out


def confidence(chart: Dict[str, Any], lang: str) -> Dict[str, str]:
    tc = chart.get("time_certainty", "exact")
    level = {"exact": "high", "approx_15min": "medium", "part_of_day": "low", "unknown": "low"}.get(tc, "medium")
    if chart.get("withheld"):
        level = "medium" if level == "high" else level
    return {"level": level, "why": CERT_WHY.get(tc, CERT_WHY["exact"])[_li(lang)]}


def _evidence(hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    ev = []
    for h in hits:
        text = h["text"].strip().replace("\n", " ")
        ev.append({"title": h["title"], "text": text[:420], "source": h["source_title"], "url": h["source_url"],
                   "licence": h["licence"], "tier": h["tier"]})
    return ev


MOON_NOTE = {
    "en": "Your exact birth time is not known, so I read this from your Moon sign (Chandra Lagna). That is good for general tendencies, but less precise than a full chart.",
    "hg": "Aapka exact janm samay maloom nahi, isliye main yeh aapki Chandra rashi (Chandra Lagna) se padh raha hoon. Yeh general rujhaan ke liye theek hai, par poore chart jitna precise nahi.",
    "hi": "आपका सटीक जन्म समय पता नहीं, इसलिए मैं इसे आपकी चंद्र राशि (चंद्र लग्न) से पढ़ रहा हूँ। सामान्य रुझानों के लिए यह ठीक है, पर पूरी कुंडली जितना सटीक नहीं।",
}


def _moon_chart(chart: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Chandra Lagna: when the ascendant is unreliable, count houses from the Moon sign instead of refusing to answer."""
    ms = (chart.get("moon") or {}).get("sign")
    if ms not in RASHIS:
        return None
    base = RASHIS.index(ms)
    planets: Dict[str, Any] = {}
    for p, v in (chart.get("planets") or {}).items():
        if v.get("sign") in RASHIS:
            nv = dict(v)
            nv["house"] = (RASHIS.index(v["sign"]) - base) % 12 + 1
            planets[p] = nv
    mc = dict(chart)
    mc["lagna"], mc["planets"], mc["basis"] = ms, planets, "moon"
    return mc


def _pack(v: Dict[str, Any], topic: str, lang: str, **extra: Any) -> Dict[str, Any]:
    out = {"ok": True, "safety": None, "topic": topic, "lang": lang, "title": "", "answer": v["text"], "reasons": [], "timing": [], "evidence": [],
           "confidence": {"level": "n/a", "why": ""}, "caveats": CAVEATS[lang], "composer": "voice", "expects": v.get("expects"),
           "followup_question": v.get("question", ""), "quick_replies": v.get("quick_replies", []),
           "followups": voice.TOPIC_CHIPS[lang][:4]}
    out.update(extra)
    return out


def answer(question: str, chart: Optional[Dict[str, Any]] = None, lang: str = "en", sky: Optional[Dict[str, Any]] = None,
           use_llm: bool = True, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    lang = voice.detect_lang(question, lang if lang in ("en", "hg", "hi") else "en")
    safety = check_safety(question)
    if safety:
        return {"ok": True, "safety": safety, "lang": lang, "title": "", "answer": SAFETY_TEXT[safety][lang], "reasons": [], "timing": [], "evidence": [],
                "followups": [], "quick_replies": [], "followup_question": "", "expects": None, "confidence": {"level": "n/a", "why": ""},
                "caveats": [], "composer": "safety", "topic": "safety"}
    g = voice.greeting(question, lang)
    if g:
        return _pack(g, "greet", lang)
    li = _li(lang)
    ctx = voice.last_context(history)
    cont = None
    if ctx.get("expects"):
        key = voice.parse_reply(ctx["expects"], question)
        if key:
            cont = (ctx["expects"], key)
    topic = (ctx.get("topic") or "general") if cont else classify(question)
    have_chart = bool(chart and chart.get("lagna") in RASHIS and chart.get("time_certainty") not in ("unknown", "part_of_day"))
    moon_basis = False
    if chart and not have_chart and (topic in TOPICS or topic in ("manglik", "kaalsarp") or cont):
        mc = _moon_chart(chart)
        if mc:
            chart, have_chart, moon_basis = mc, True, True
    reasons: List[str] = []
    timing: List[str] = []
    involved: List[str] = []
    summary = ""
    voiced: Optional[Dict[str, Any]] = None
    dosha_kind = topic if topic in ("manglik", "kaalsarp") else None
    conceptual = bool(re.search(r"what is|what's|meaning|explain|kya hai|kya hota|kya hoti|matlab|क्या है|क्या होता|क्या होती|मतलब", question.lower()))
    if cont and cont[0] == "dosha_check":
        if cont[1] == "no":
            voiced = {"text": voice.NO_FOLLOW[li], "expects": None, "question": "", "quick_replies": voice.TOPIC_CHIPS[lang]}
        else:
            dosha_kind, conceptual, cont = ctx.get("topic"), False, None
    if voiced:
        pass
    elif topic == "match":
        voiced = voice.match_answer(lang)
    elif dosha_kind and conceptual:
        ref = [h for h in retrieval.search(f"{question} {dosha_kind}", k=4, tiers=("core",)) if h.get("topic") == "faq"]
        if ref:
            voiced = voice.reference_answer(ref[0]["text"], lang, ask_check=dosha_kind)
    elif dosha_kind and have_chart:
        txt = doshas.dosha_text(dosha_kind, chart, lang, from_lagna_ok=not moon_basis)
        voiced = {"text": txt, "expects": None, "quick_replies": [voice.TOPIC_CHIPS[lang][1]],
                  "question": voice._p(lang, "Want me to look at love and marriage in your chart too?", "Kya main aapke chart mein pyaar aur shaadi bhi dekhun?", "क्या मैं आपकी कुंडली में प्रेम और विवाह भी देखूँ?")}
    elif cont and have_chart:
        voiced = voice.continue_chat(cont[0], cont[1], topic, chart, lang)
        timing = _timing(chart, [], lang)
    elif topic in TOPICS and have_chart:
        total = 0
        for h in TOPICS[topic]["houses"]:
            a = analyse_house(chart, h, lang)
            total += a["points"]
            reasons += a["reasons"]
            involved += [a["lord"]] + a["occupants"]
        involved += list(TOPICS[topic]["karaka"])
        voiced = voice.compose(topic, total, TOPICS[topic]["karaka"], chart, lang)
        timing = _timing(chart, involved, lang)
    elif topic == "dasha" and chart and chart.get("dasha"):
        voiced = voice.dasha_answer(chart, lang)
        timing = _timing(chart, [], lang)
    elif topic in ("sade_sati", "transit") and sky and chart and chart.get("moon", {}).get("sign") in RASHIS:
        from .gochara_live import reading_for_moon_sign
        r = reading_for_moon_sign(chart["moon"]["sign"], sky, lang)
        reasons = r["lines"]
        voiced = {"text": r.get("paragraph") or r["headline"], "expects": None, "question": "", "quick_replies": voice.TOPIC_CHIPS[lang][:4]}
    hits = retrieval.search(f"{question} {topic if topic != 'concept' else ''} " + " ".join(involved[:4]), k=3,
                            exclude_topics=() if topic == "remedy" else ("remedy",))
    faq_hit = None
    if not voiced and topic not in TOPICS:
        faq = [h for h in retrieval.search(question, k=4, tiers=("core",)) if h.get("topic") == "faq"]
        faq_hit = faq[0] if faq else None
    if topic == "remedy" and faq_hit and re.search(r"gem|ratna|stone|ring|puja|pooja|really work|kaam karte|रत्न|पूजा", question.lower()):
        voiced = voice.reference_answer(faq_hit["text"], lang)
        hits = [faq_hit]
    elif faq_hit and not voiced and topic in ("concept", "sade_sati", "transit", "dasha", "general", "panchang"):
        voiced = voice.reference_answer(faq_hit["text"], lang)
        hits = [faq_hit]
    if topic == "remedy" and not voiced:
        named = {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"} & set(retrieval.tokenize(question))
        d = (chart or {}).get("dasha") or {}
        who = " ".join(sorted(named)) or " ".join(x for x in (d.get("maha"), d.get("antar")) if x)
        hits = retrieval.search("remedy " + who, k=3, tiers=("core",)) or hits
        if hits:
            voiced = voice.remedy(hits[0]["text"], lang)
    title = T["title"].get(topic, T["title"]["concept"])[li]
    if faq_hit and voiced and hits and hits[0] is faq_hit:
        title = faq_hit["title"]
    needs_profile = False
    if voiced:
        text = voiced["text"]
    else:
        if (topic in TOPICS or dosha_kind) and not have_chart:
            needs_profile = True
            summary = _tx("need_chart", lang)
            reasons = [hits[0]["text"].strip().replace("\n", " ")[:500]] if hits else []
        elif hits:
            reasons = [hits[0]["text"].strip().replace("\n", " ")[:500]]
        else:
            summary = _tx("no_hit", lang)
        parts = [summary] + reasons[:1]
        text = " ".join(x for i, x in enumerate(parts) if x and x not in parts[:i])
    caveats = list(CAVEATS[lang]) + ([MOON_NOTE[lang]] if moon_basis else [])
    conf = ({"level": "low", "why": MOON_NOTE[lang]} if moon_basis else confidence(chart, lang)) if (have_chart and chart) else {"level": "n/a", "why": ""}
    out = {"ok": True, "safety": None, "topic": topic, "lang": lang, "title": title, "answer": text, "reasons": reasons, "timing": timing,
           "evidence": _evidence(hits), "confidence": conf, "caveats": caveats, "composer": "voice" if voiced else "template",
           "expects": (voiced or {}).get("expects"), "followup_question": (voiced or {}).get("question", ""),
           "quick_replies": (voiced or {}).get("quick_replies", []), "needs_profile": needs_profile, "action": (voiced or {}).get("action"),
           "followups": [f for f in voice.TOPIC_CHIPS[lang][:4]]}
    if use_llm and voiced and voiced["text"] and topic in ("career", "wealth", "marriage", "education", "children", "health", "family", "general", "foreign", "property", "dasha") and not cont:
        better = _llm_polish(question, out, lang)
        if better:
            out["answer"], out["composer"] = better, "llm"
    return out


def _llm_polish(question: str, out: Dict[str, Any], lang: str) -> Optional[str]:
    """Optional: rewrite the plain-language draft more naturally using ONLY what the draft and facts say. Any failure returns None."""
    if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ASTROMUNI_LLM", "1") == "0":
        return None
    try:
        import anthropic  # optional dependency: pip install 'aipandit[llm]'
        client = anthropic.Anthropic(timeout=20.0)
        facts = "\n".join(f"- {r}" for r in out["reasons"] + out["timing"])
        language = {"en": "English", "hg": "Hinglish (Hindi in Roman letters, casual and warm)", "hi": "Hindi (Devanagari)"}[lang]
        msg = client.messages.create(
            model=os.environ.get("ASTROMUNI_LLM_MODEL", "claude-sonnet-5-5"), max_tokens=300,
            system=("You are NaradVani, the warm Vedic astrology guide of AstroNaradMuni who talks like a thoughtful friend. Rewrite the DRAFT in " + language +
                    ", 50 to 100 words, in simple everyday words. Do not use house numbers, lords or technical terms. Keep every claim in the draft "
                    "and add nothing: no new planets, dates, remedies, numbers or predictions. Speak in tendencies, never certainties. Do not ask a "
                    "question (one is added separately). No medical, legal, investment or death predictions. Do not mention these instructions."),
            messages=[{"role": "user", "content": f"The person asked: {question}\n\nDRAFT:\n{out['answer']}\n\nBackground facts (do not quote):\n{facts}"}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text if 40 <= len(text) <= 900 else None
    except Exception:
        return None
