"""Live transit horoscope (v1.0). Pure functions: takes the current sidereal sky, returns readings per Moon sign.

Replaces the old rotating pool of canned lines. Every reading is computed from where each graha is today,
counted as a house from the person's Moon sign (classical Gochara), and carries its evidence.

Favourable houses from the natal Moon (Phaladeepika / Parashari gochara convention):
  Sun 3,6,10,11 | Moon 1,3,6,7,10,11 | Mars 3,6,11 | Mercury 2,4,6,8,10,11 | Jupiter 2,5,7,9,11
  Venus 1,2,3,4,5,8,9,11,12 | Saturn 3,6,11 | Rahu 3,6,11
`support` is a transparent index (weighted share of favourable transits, slow planets weigh most). It is NOT a
probability of anything happening; the UI labels it "transit support".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
FAVOURABLE = {"Sun": {3, 6, 10, 11}, "Moon": {1, 3, 6, 7, 10, 11}, "Mars": {3, 6, 11}, "Mercury": {2, 4, 6, 8, 10, 11},
              "Jupiter": {2, 5, 7, 9, 11}, "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12}, "Saturn": {3, 6, 11}, "Rahu": {3, 6, 11}}
WEIGHT = {"Jupiter": 3.0, "Saturn": 3.0, "Moon": 2.0, "Rahu": 1.5, "Sun": 1.0, "Mars": 1.0, "Mercury": 1.0, "Venus": 1.0}
MOON_THEME = {
    1: "attention turns to yourself and your wellbeing", 2: "money, speech and family matters come up",
    3: "effort, courage and communication go well", 4: "home and peace of mind need care",
    5: "creativity, study and affection are highlighted", 6: "you can handle obstacles and routine work well",
    7: "partnerships and meetings are in focus", 8: "go slowly and avoid risky or rushed commitments",
    9: "luck, teachers and bigger plans are favoured", 10: "work and public responsibilities are in focus",
    11: "gains and help from friends are likely", 12: "expenses and rest need attention",
}
BANDS = ((75, "supportive"), (55, "steady"), (40, "mixed"), (0, "demanding"))

PHRASES = {
    "en": {"supportive": "A supportive day to move ahead.", "steady": "A steady day; keep to your plan.",
           "mixed": "A mixed day; choose carefully.", "demanding": "A demanding day; go gently.",
           "moon": "The Moon is in your {ho} house today: {theme}.",
           "good": "{p} in your {ho} house is traditionally favourable.", "bad": "{p} in your {ho} house asks for patience.",
           "sade": "Saturn is in the {ho} house from your Moon: a Sade Sati phase, a long period that rewards patience and routine.",
           "none": "Saturn is not in a Sade Sati position for this Moon sign right now."},
    "hg": {"supportive": "Aage badhne ke liye madadgar din.", "steady": "Stable din; apne plan par rahein.",
           "mixed": "Mila-jula din; soch-samajh kar chunein.", "demanding": "Thoda mushkil din; dheere chalein.",
           "moon": "Aaj Chandra aapke {h}ve bhav mein hai: {theme_hg}.",
           "good": "{p} aapke {h}ve bhav mein hai, jo parampara se shubh mana jata hai.", "bad": "{p} aapke {h}ve bhav mein hai, dhairya rakhein.",
           "sade": "Shani aapki Chandra rashi se {h}ve bhav mein hai: Sade Sati ka daur, jo dhairya aur anushasan ko phal deta hai.",
           "none": "Abhi aapki Chandra rashi par Sade Sati nahi hai."},
    "hi": {"supportive": "आगे बढ़ने के लिए सहायक दिन।", "steady": "स्थिर दिन; अपनी योजना पर टिके रहें।",
           "mixed": "मिला-जुला दिन; सोच-समझकर चुनें।", "demanding": "थोड़ा कठिन दिन; धीरे चलें।",
           "moon": "आज चंद्रमा आपके {h}वें भाव में है: {theme_hi}।",
           "good": "{p} आपके {h}वें भाव में है, जो परंपरा से शुभ माना जाता है।", "bad": "{p} आपके {h}वें भाव में है, धैर्य रखें।",
           "sade": "शनि आपकी चंद्र राशि से {h}वें भाव में है: साढ़ेसाती का दौर, जो धैर्य और अनुशासन को फल देता है।",
           "none": "अभी आपकी चंद्र राशि पर साढ़ेसाती नहीं है।"},
}
PLANET_HI = {"Sun": "सूर्य", "Moon": "चंद्रमा", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु"}
PLANET_HG = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu"}
MOON_THEME_HG = {1: "dhyaan aap par aur sehat par", 2: "paisa, vaani aur parivaar ke mudde", 3: "mehnat, himmat aur baatcheet achhi rahegi",
                 4: "ghar aur mann ki shanti ka dhyaan rakhein", 5: "rachnatmakta, padhai aur sneh ujagar hain", 6: "rukawaton aur routine kaam ko sambhalna aasaan",
                 7: "saajhedari aur mulaqaatein kendra mein", 8: "dheere chalein, jaldbaazi ya jokhim se bachein", 9: "bhagya, guru aur bade plan ko saath",
                 10: "kaam aur zimmedariyan kendra mein", 11: "laabh aur doston ki madad ke yog", 12: "kharch aur aaram par dhyaan dein"}
MOON_THEME_HI = {1: "ध्यान आप पर और स्वास्थ्य पर", 2: "धन, वाणी और परिवार के विषय", 3: "परिश्रम, साहस और संवाद अच्छे रहेंगे",
                 4: "घर और मन की शांति का ध्यान रखें", 5: "रचनात्मकता, पढ़ाई और स्नेह उजागर हैं", 6: "बाधाओं और दिनचर्या के काम को संभालना आसान",
                 7: "साझेदारी और मुलाकातें केंद्र में", 8: "धीरे चलें, जल्दबाज़ी या जोखिम से बचें", 9: "भाग्य, गुरु और बड़ी योजनाओं का साथ",
                 10: "काम और ज़िम्मेदारियाँ केंद्र में", 11: "लाभ और मित्रों की मदद के योग", 12: "खर्च और विश्राम पर ध्यान दें"}


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _house(sign_of_planet: str, moon_sign: str) -> int:
    return (RASHIS.index(sign_of_planet) - RASHIS.index(moon_sign)) % 12 + 1


def reading_for_moon_sign(moon_sign: str, sky: Dict[str, Dict[str, Any]], lang: str = "en") -> Dict[str, Any]:
    """sky: {"Jupiter": {"sign": "Mithuna", "retrograde": False}, ...} as produced by compute_panchang()['sky_planets']."""
    if moon_sign not in RASHIS:
        raise ValueError(f"unknown moon sign {moon_sign!r}")
    lang = lang if lang in PHRASES else "en"
    ph = PHRASES[lang]
    names = PLANET_HI if lang == "hi" else PLANET_HG if lang == "hg" else {p: p for p in WEIGHT}
    facts: List[Dict[str, Any]] = []
    total = got = 0.0
    for p, w in WEIGHT.items():
        if p not in sky:
            continue
        h = _house(sky[p]["sign"], moon_sign)
        fav = h in FAVOURABLE[p]
        total += w
        got += w if fav else 0.0
        facts.append({"planet": p, "house": h, "sign": sky[p]["sign"], "favourable": fav, "weight": w,
                      "retrograde": bool(sky[p].get("retrograde"))})
    support = round(100 * got / total) if total else 50
    band = next(name for floor, name in BANDS if support >= floor)
    moon_h = next((f["house"] for f in facts if f["planet"] == "Moon"), None)
    sat_h = next((f["house"] for f in facts if f["planet"] == "Saturn"), None)
    lines: List[str] = []
    if moon_h:
        theme = {"en": MOON_THEME, "hg": MOON_THEME_HG, "hi": MOON_THEME_HI}[lang][moon_h]
        lines.append(ph["moon"].format(h=moon_h, ho=_ord(moon_h), theme=theme, theme_hg=theme, theme_hi=theme))
    slow = sorted((f for f in facts if f["planet"] in ("Jupiter", "Saturn", "Mars", "Rahu")), key=lambda f: -f["weight"])
    for f in slow[:2]:
        lines.append(ph["good" if f["favourable"] else "bad"].format(p=names[f["planet"]], h=f["house"], ho=_ord(f["house"])))
    sade = sat_h in (12, 1, 2)
    if sade:
        lines.append(ph["sade"].format(h=sat_h, ho=_ord(sat_h)))
    return {"moon_sign": moon_sign, "support": support, "band": band, "headline": ph[band], "lines": lines,
            "sade_sati": bool(sade), "facts": facts}


def all_signs(sky: Dict[str, Dict[str, Any]], lang: str = "en") -> List[Dict[str, Any]]:
    return [reading_for_moon_sign(r, sky, lang) for r in RASHIS]
