"""AstroMuni curated core knowledge (v1.0).

Plain reference facts of Vedic astrology, written in our own words from widely shared classical
convention (Parashari tradition). Nothing here is copied from a copyrighted translation, so it is safe
to ship and to quote in answers. Each passage carries topic tags and a `confidence` of "convention":
these are traditional definitions, not statistical claims about people's lives.

`core_passages()` returns retrieval-ready dicts; `tools/build_core_kb.py` can dump them to JSONL.
"""
from __future__ import annotations

from typing import Dict, List

SRC = "AstroMuni curated reference (Parashari convention, own words)"

SIGNS = [
    # key, english, hindi, lord, element, modality
    ("Mesha", "Aries", "मेष", "Mars", "fire", "movable"),
    ("Vrishabha", "Taurus", "वृषभ", "Venus", "earth", "fixed"),
    ("Mithuna", "Gemini", "मिथुन", "Mercury", "air", "dual"),
    ("Karka", "Cancer", "कर्क", "Moon", "water", "movable"),
    ("Simha", "Leo", "सिंह", "Sun", "fire", "fixed"),
    ("Kanya", "Virgo", "कन्या", "Mercury", "earth", "dual"),
    ("Tula", "Libra", "तुला", "Venus", "air", "movable"),
    ("Vrishchika", "Scorpio", "वृश्चिक", "Mars", "water", "fixed"),
    ("Dhanu", "Sagittarius", "धनु", "Jupiter", "fire", "dual"),
    ("Makara", "Capricorn", "मकर", "Saturn", "earth", "movable"),
    ("Kumbha", "Aquarius", "कुंभ", "Saturn", "air", "fixed"),
    ("Meena", "Pisces", "मीन", "Jupiter", "water", "dual"),
]
SIGN_THEME = {
    "Mesha": "initiative, courage and a direct style", "Vrishabha": "steadiness, comfort and patient building",
    "Mithuna": "curiosity, speech and quick learning", "Karka": "feeling, care and attachment to home",
    "Simha": "dignity, leadership and warmth", "Kanya": "analysis, service and attention to detail",
    "Tula": "balance, relationship and fair dealing", "Vrishchika": "depth, intensity and transformation",
    "Dhanu": "philosophy, optimism and long vision", "Makara": "discipline, structure and earned results",
    "Kumbha": "ideas, community and independent thinking", "Meena": "compassion, imagination and surrender",
}

# graha: day, nature, significations, exaltation, debilitation, own signs, dasha years
GRAHAS = {
    "Sun": ("Sunday", "malefic by nature", "soul, vitality, father, authority, government, confidence",
            "Mesha", "Tula", "Simha", 6),
    "Moon": ("Monday", "benefic when waxing", "mind, emotions, mother, public, nourishment, memory",
             "Vrishabha", "Vrishchika", "Karka", 10),
    "Mars": ("Tuesday", "malefic by nature", "energy, courage, siblings, land, conflict, technical skill",
             "Makara", "Karka", "Mesha and Vrishchika", 7),
    "Mercury": ("Wednesday", "neutral, takes the nature of its company", "intellect, speech, trade, learning, analysis",
                "Kanya", "Meena", "Mithuna and Kanya", 17),
    "Jupiter": ("Thursday", "natural benefic", "wisdom, teachers, children, fortune, dharma, wealth of knowledge",
                "Karka", "Makara", "Dhanu and Meena", 16),
    "Venus": ("Friday", "natural benefic", "love, marriage, comfort, art, vehicles, refinement",
              "Meena", "Kanya", "Vrishabha and Tula", 20),
    "Saturn": ("Saturday", "malefic by nature", "discipline, delay, labour, longevity, service, detachment",
               "Tula", "Mesha", "Makara and Kumbha", 19),
    "Rahu": ("no ruling day", "shadow planet, acts like Saturn", "obsession, foreign matters, ambition, unconventional paths",
             "Vrishabha (by some schools)", "Vrishchika (by some schools)", "none (by some schools Kumbha)", 18),
    "Ketu": ("no ruling day", "shadow planet, acts like Mars", "detachment, past-life themes, spirituality, sudden endings",
             "Vrishchika (by some schools)", "Vrishabha (by some schools)", "none (by some schools Vrishchika)", 7),
}

HOUSES = {
    1: ("Lagna / Tanu bhava", "the self, body, temperament, health and how you begin things"),
    2: ("Dhana bhava", "wealth saved, family, speech, food and early values"),
    3: ("Sahaja bhava", "effort, courage, siblings, short travel, skills and communication"),
    4: ("Sukha bhava", "mother, home, vehicles, inner peace and formal education"),
    5: ("Putra bhava", "children, creativity, intelligence, romance and merit from past action"),
    6: ("Ripu bhava", "debts, disease, enemies, daily service and competition"),
    7: ("Kalatra bhava", "marriage, partnerships, business partners and public dealings"),
    8: ("Ayu bhava", "longevity, sudden change, secrets, inheritance and research"),
    9: ("Dharma bhava", "fortune, father, teachers, higher learning, long journeys and belief"),
    10: ("Karma bhava", "career, status, public duty and the results of action"),
    11: ("Labha bhava", "gains, income, networks, elder siblings and fulfilment of desires"),
    12: ("Vyaya bhava", "expenses, loss, foreign residence, sleep, retreat and liberation"),
}

# (name, lord, deity, symbol, sign span)
NAKSHATRAS = [
    ("Ashwini", "Ketu", "Ashwini Kumaras", "horse's head", "Mesha 0°–13°20'"),
    ("Bharani", "Venus", "Yama", "yoni, the bearer", "Mesha 13°20'–26°40'"),
    ("Krittika", "Sun", "Agni", "razor or flame", "Mesha 26°40' to Vrishabha 10°"),
    ("Rohini", "Moon", "Prajapati Brahma", "cart or chariot", "Vrishabha 10°–23°20'"),
    ("Mrigashira", "Mars", "Soma", "deer's head", "Vrishabha 23°20' to Mithuna 6°40'"),
    ("Ardra", "Rahu", "Rudra", "teardrop", "Mithuna 6°40'–20°"),
    ("Punarvasu", "Jupiter", "Aditi", "bow and quiver", "Mithuna 20° to Karka 3°20'"),
    ("Pushya", "Saturn", "Brihaspati", "flower or udder", "Karka 3°20'–16°40'"),
    ("Ashlesha", "Mercury", "Nagas", "coiled serpent", "Karka 16°40'–30°"),
    ("Magha", "Ketu", "Pitris", "royal throne", "Simha 0°–13°20'"),
    ("Purva Phalguni", "Venus", "Bhaga", "front legs of a bed", "Simha 13°20'–26°40'"),
    ("Uttara Phalguni", "Sun", "Aryaman", "back legs of a bed", "Simha 26°40' to Kanya 10°"),
    ("Hasta", "Moon", "Savitar", "open hand", "Kanya 10°–23°20'"),
    ("Chitra", "Mars", "Tvashtar", "bright jewel", "Kanya 23°20' to Tula 6°40'"),
    ("Swati", "Rahu", "Vayu", "young shoot in wind", "Tula 6°40'–20°"),
    ("Vishakha", "Jupiter", "Indra and Agni", "triumphal arch", "Tula 20° to Vrishchika 3°20'"),
    ("Anuradha", "Saturn", "Mitra", "lotus", "Vrishchika 3°20'–16°40'"),
    ("Jyeshtha", "Mercury", "Indra", "circular amulet", "Vrishchika 16°40'–30°"),
    ("Mula", "Ketu", "Nirriti", "bunch of roots", "Dhanu 0°–13°20'"),
    ("Purva Ashadha", "Venus", "Apas", "winnowing fan", "Dhanu 13°20'–26°40'"),
    ("Uttara Ashadha", "Sun", "Vishvadevas", "elephant tusk", "Dhanu 26°40' to Makara 10°"),
    ("Shravana", "Moon", "Vishnu", "ear", "Makara 10°–23°20'"),
    ("Dhanishta", "Mars", "Eight Vasus", "drum", "Makara 23°20' to Kumbha 6°40'"),
    ("Shatabhisha", "Rahu", "Varuna", "empty circle", "Kumbha 6°40'–20°"),
    ("Purva Bhadrapada", "Jupiter", "Aja Ekapada", "front of a funeral cot", "Kumbha 20° to Meena 3°20'"),
    ("Uttara Bhadrapada", "Saturn", "Ahir Budhnya", "back of a funeral cot", "Meena 3°20'–16°40'"),
    ("Revati", "Mercury", "Pushan", "fish or drum", "Meena 16°40'–30°"),
]

YOGAS = [
    ("Gajakesari yoga", ["gajakesari", "jupiter", "moon", "kendra"],
     "Jupiter placed in a kendra (1st, 4th, 7th or 10th house) from the Moon. Tradition reads it as good reputation, "
     "sound judgement and lasting respect. It is fairly common, so its strength depends on dignity and aspects."),
    ("Budha-Aditya yoga", ["budhaditya", "sun", "mercury"],
     "Sun and Mercury in the same sign. Read as sharp intellect and skill with words. Mercury is always close to the "
     "Sun, so this is very common; it is weak if Mercury is too near the Sun (combust)."),
    ("Pancha Mahapurusha yogas", ["mahapurusha", "ruchaka", "bhadra", "hamsa", "malavya", "shasha"],
     "Five yogas formed when Mars (Ruchaka), Mercury (Bhadra), Jupiter (Hamsa), Venus (Malavya) or Saturn (Shasha) "
     "sits in its own or exalted sign in a kendra from the Lagna. Traditionally linked with a distinguished career."),
    ("Raja yoga", ["raja", "yoga", "kendra", "trikona", "status"],
     "A link between the lord of a kendra and the lord of a trikona (5th or 9th), by conjunction, aspect or exchange. "
     "Tradition reads it as rise in status; its fruit is timed by the dashas of the planets involved."),
    ("Dhana yoga", ["dhana", "wealth", "money", "yoga"],
     "A link between lords of the wealth houses (2nd, 5th, 9th, 11th). Read as capacity to earn and accumulate; "
     "the dasha of the involved planets is when it tends to show."),
    ("Neecha Bhanga Raja yoga", ["neecha", "bhanga", "debilitation", "cancellation"],
     "Cancellation of a planet's debilitation, for example when the lord of its sign of fall is in a kendra. "
     "Tradition says the weakness turns into late but real strength."),
    ("Viparita Raja yoga", ["viparita", "dusthana", "6th", "8th", "12th"],
     "Lords of the 6th, 8th and 12th houses placed in each other's houses. Read as gain that arrives after difficulty."),
    ("Kemadruma yoga", ["kemadruma", "moon", "isolation"],
     "No planet (other than the Sun) in the signs beside the Moon and none with it. Read as emotional isolation or "
     "fluctuating support; cancelled by several classical conditions, so it is not judged alone."),
    ("Guru-Chandala yoga", ["guru", "chandala", "jupiter", "rahu"],
     "Jupiter conjunct Rahu. Read as an unconventional or questioning attitude to belief and teachers. Its outcome "
     "depends heavily on the sign and houses involved."),
    ("Mangal dosha (Kuja dosha)", ["manglik", "mangal", "kuja", "dosha", "mars", "marriage"],
     "Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house from the Lagna (some schools also use the Moon or Venus). "
     "Used in marriage matching to flag intensity in partnership. Many classical cancellations exist, so it is never "
     "a verdict by itself, and a pandit should weigh it with the whole chart."),
    ("Kaal Sarp dosha", ["kaal", "sarp", "rahu", "ketu", "kalsarpa"],
     "All seven planets between Rahu and Ketu. It is a later, regional idea not found in the oldest texts, and many "
     "astrologers treat it with caution."),
    ("Sade Sati", ["sade", "sati", "saturn", "moon", "shani"],
     "The roughly seven-and-a-half-year period when Saturn passes through the 12th, 1st and 2nd signs from the natal "
     "Moon. Tradition links it with pressure, restructuring and lessons in patience; it is a theme, not a fixed event."),
]

DASHA_SEQ = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

CONCEPTS = [
    ("Janam Kundli", ["kundli", "chart", "birth", "horoscope", "janam"],
     "A kundli is the map of the sky at the exact time and place of birth, drawn as twelve houses with the nine "
     "grahas placed in signs. Accuracy depends on a correct birth time: a few minutes can change the Lagna."),
    ("Lagna (Ascendant)", ["lagna", "ascendant", "rising"],
     "The sign rising on the eastern horizon at birth. It sets the first house and so the layout of the whole chart. "
     "It changes sign about every two hours, which is why birth time matters."),
    ("Chandra Rashi (Moon sign)", ["moon", "rashi", "chandra", "sign"],
     "The sign the Moon occupied at birth. Vedic daily and transit readings are made from the Moon sign. It reflects "
     "mind, mood and instinct more than outward behaviour."),
    ("Vimshottari Dasha", ["dasha", "vimshottari", "mahadasha", "antardasha", "timing", "period"],
     "A 120-year cycle that divides life into planetary periods, started from the Moon's nakshatra at birth. The "
     "sequence is Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 years. "
     "Each mahadasha is split into antardashas; the ruling planet's placement colours that period."),
    ("Gochara (transits)", ["gochara", "transit", "gochar", "current"],
     "Gochara reads where planets are now against the natal Moon sign. Classically Jupiter is favourable from the "
     "2nd, 5th, 7th, 9th and 11th; Saturn, Mars and the nodes from the 3rd, 6th and 11th; the Sun from the 3rd, 6th, "
     "10th and 11th. Transits colour a period; the dasha says which areas are active."),
    ("Panchang", ["panchang", "tithi", "nakshatra", "yoga", "karana", "vara"],
     "The five limbs of the Hindu calendar: tithi (lunar day, each 12° of Moon–Sun distance), vara (weekday), "
     "nakshatra (Moon's star), yoga (Sun+Moon sum in 13°20' steps) and karana (half a tithi)."),
    ("Navamsa (D9)", ["navamsa", "d9", "divisional", "varga"],
     "A ninth-part divisional chart used to judge the real strength of planets and the quality of marriage. A planet "
     "strong in both the birth chart and the navamsa is considered reliably strong."),
    ("Ashtakoota Gun Milan", ["gun", "milan", "ashtakoota", "matching", "compatibility", "marriage", "36"],
     "Eight-fold matching on 36 points from the two Moon positions: Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, "
     "Gana 6, Bhakoot 7, Nadi 8. About 18 points is usually the minimum quoted and 24 or more is called good. It "
     "compares temperaments only; it does not replace comparing the full charts."),
    ("Abhijit Muhurta", ["abhijit", "muhurta", "auspicious", "time"],
     "The auspicious window around local midday, about 24 minutes either side of solar noon in common practice. "
     "It is avoided on Wednesdays by many panchang traditions."),
    ("Retrograde (vakri)", ["retrograde", "vakri", "backward"],
     "A planet appears to move backwards from Earth. Tradition treats a retrograde planet as strong but inward or "
     "delayed in its results."),
    ("Combustion (asta)", ["combust", "asta", "sun", "close"],
     "A planet too close to the Sun loses visibility and is called combust. Its significations are read as "
     "overshadowed by the Sun."),
    ("Numerology (Mulank and Bhagyank)", ["numerology", "mulank", "bhagyank", "number"],
     "Mulank is the digit sum of the birth day; Bhagyank is the digit sum of the full birth date. Each digit is "
     "tied to a planet (1 Sun, 2 Moon, 3 Jupiter, 4 Rahu, 5 Mercury, 6 Venus, 7 Ketu, 8 Saturn, 9 Mars)."),
    ("How to read this guidance", ["accuracy", "prediction", "certainty", "guidance", "trust"],
     "Jyotish gives tendencies and timing themes, not guarantees. AstroMuni computes the chart with an astronomy "
     "engine and only states what the chart supports; where birth time is uncertain it withholds details. "
     "Medical, legal and financial decisions should always involve a qualified professional."),
]

# Remedies are framed as traditional practices, never as cures.
REMEDIES = {
    "Sun": "Traditional practice: rise early, offer water to the Sun at sunrise, respect elders and authority figures.",
    "Moon": "Traditional practice: keep a calm routine, spend time near water, care for your mother or maternal figures.",
    "Mars": "Traditional practice: regular physical exercise, patience in conflict, service to siblings and the Hanuman tradition on Tuesdays.",
    "Mercury": "Traditional practice: reading and learning, clear speech, honesty in trade, green foods and charity on Wednesdays.",
    "Jupiter": "Traditional practice: respect teachers, study, generosity, simple fasting or temple visits on Thursdays.",
    "Venus": "Traditional practice: honour partners and women, keep surroundings clean and beautiful, charity on Fridays.",
    "Saturn": "Traditional practice: steady discipline, fair treatment of workers, service to the poor and elders, regularity on Saturdays.",
    "Rahu": "Traditional practice: avoid shortcuts and intoxicants, keep routines, recite your family's chosen mantra consistently.",
    "Ketu": "Traditional practice: meditation, quiet time, humility and spiritual study.",
}


def core_passages() -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []

    def add(pid: str, title: str, tags: List[str], text: str, topic: str) -> None:
        out.append({"id": pid, "title": title, "topic": topic, "tags": tags, "text": text, "source_title": SRC,
                    "source_url": "", "licence": "own-words", "confidence": "convention", "tier": "core"})

    for key, en, hi, lord, el, mod in SIGNS:
        add(f"sign_{key.lower()}", f"{en} ({key})", [key.lower(), en.lower(), hi, "rashi", "sign", lord.lower()],
            f"{key} ({en}, {hi}) is a {mod}, {el} sign ruled by {lord}. It stands for {SIGN_THEME[key]}.", "sign")
    for g, (day, nature, sig, exalt, deb, own, yrs) in GRAHAS.items():
        add(f"graha_{g.lower()}", g, [g.lower(), "graha", "planet", day.lower()],
            f"{g} is {nature}. It signifies {sig}. Day: {day}. Exalted in {exalt}, debilitated in {deb}, "
            f"owns {own}. Vimshottari dasha length: {yrs} years.", "graha")
        add(f"remedy_{g.lower()}", f"{g} traditional practices", [g.lower(), "remedy", "upaya", "practice"],
            REMEDIES[g] + " These are traditional practices for reflection, not guaranteed cures.", "remedy")
    for n, (name, sig) in HOUSES.items():
        add(f"house_{n}", f"House {n}: {name}", [f"house{n}", f"{n}th house", "bhava", "house"],
            f"The {n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'} house ({name}) concerns {sig}.", "house")
    for name, lord, deity, symbol, span in NAKSHATRAS:
        add(f"nak_{name.lower().replace(' ', '_')}", f"{name} nakshatra", [name.lower(), "nakshatra", "star", lord.lower()],
            f"{name} spans {span}. Ruling planet {lord} (so the dasha starts from {lord} for a Moon here); deity {deity}; "
            f"symbol {symbol}.", "nakshatra")
    for title, tags, text in YOGAS:
        add("yoga_" + title.lower().split()[0].strip("()"), title, tags + ["yoga"], text, "yoga")
    for title, tags, text in CONCEPTS:
        add("concept_" + title.lower().split()[0].strip("()"), title, tags, text, "concept")
    from .kb_faq import FAQ
    for i, (title, tags, text) in enumerate(FAQ):
        add(f"faq_{i:02d}", title, tags, text, "faq")
    return out
