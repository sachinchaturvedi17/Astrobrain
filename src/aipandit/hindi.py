"""Hindi / Devanagari support shared by the planner and the gates.

Devanagari is matched on *normalised* text: NFC, nukta removed (ज़ -> ज), chandrabindu -> anusvara
(पाँच -> पांच), Devanagari digits -> ASCII. Both the user's text and every pattern go through `norm`, so
spelling variants of the same word match. Python's \\b is unreliable next to Devanagari vowel signs, so
short words use explicit look-around (`W`) instead.
"""
from __future__ import annotations

import re
import unicodedata

DEV = r"\u0900-\u0963\u0966-\u097F"   # raw escapes (so norm() leaves the class alone); excludes the danda
_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def norm(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "")
    t = t.replace("़", "").replace("ँ", "ं")
    return t.translate(_DIGITS)


def W(word: str) -> str:
    """Whole Devanagari word: not preceded or followed by another Devanagari character."""
    return rf"(?<![{DEV}]){word}(?![{DEV}])"


def L(word: str) -> str:
    """Word start only (inflected/suffixed forms allowed)."""
    return rf"(?<![{DEV}]){word}"


# Words that are Hindi, not English, when written in Latin script. Deliberately excludes words that are also common
# English ("main", "is", "me", "to", "in", "or", "do", "hum" is kept: not English).
HINGLISH_MARKERS = re.compile(
    r"\b(?:mera|meri|mere|mujhe|mujhko|meko|hai|hain|nahi|nahin|kya|kyun|kyu|kaise|kaisa|kaisi|kab|kaun|kitna|kitne|kitni|"
    r"batao|bataiye|bataye|bataiyega|bata|batana|aap|aapki|aapka|aapke|tum|tumhara|hum|humara|hamara|ka|ki|ke|ko|se|"
    r"par|pe|mein|bhi|toh|lekin|aur|ya|kuch|koi|sab|bahut|bohot|thoda|zyada|jyada|abhi|aaj|kal|saal|bhai|yaar|ji|"
    r"chahiye|chahta|chahti|karna|karo|kar|karu|hoga|hogi|honge|rahega|rahegi|milega|milegi|lagta|lagti|wala|wali|"
    r"wale|achha|accha|acha|theek|sahi|galat|shaadi|shadi|naukri|paisa|paise|kundli|kundali|janam|janm|rashi|"
    r"dasha|graha|grah|mulank|bhagyank|ank)\b", re.I)
# Strong subset: one of these alone is enough; the weak words (ka, ki, ke, ko, se, par, pe, ji, ya, aur, kar, ...) need company.
_HG_STRONG = re.compile(
    r"\b(?:mera|meri|mere|mujhe|mujhko|hai|hain|nahi|nahin|kya|kyun|kyu|kaise|kaisa|kaisi|kab|kaun|kitna|kitne|kitni|"
    r"batao|bataiye|bataye|aapki|aapka|aapke|tumhara|humara|hamara|bhi|toh|lekin|kuch|bahut|bohot|thoda|zyada|jyada|"
    r"abhi|chahiye|chahta|chahti|hoga|hogi|honge|rahega|rahegi|milega|milegi|lagta|lagti|achha|accha|shaadi|shadi|"
    r"naukri|paisa|paise|janam|janm|mulank|bhagyank)\b", re.I)


def detect_language(text: str) -> str:
    """'hi' if mostly Devanagari; 'hg' for Latin-script Hinglish; else 'en'."""
    dev = sum(1 for c in text or "" if "ऀ" <= c <= "ॿ" and c.isalpha() or "ऀ" <= c <= "ॿ" and c not in "।॥")
    lat = sum(1 for c in text or "" if c.isascii() and c.isalpha())
    if dev and dev >= lat:
        return "hi"
    t = text or ""
    if _HG_STRONG.search(t) or len(HINGLISH_MARKERS.findall(t)) >= 2:
        return "hg"
    return "en"


GRAHA_HI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
            "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}
GRAHA_HG = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra",
            "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"}
SIGN_HI = {"Mesha": "मेष", "Vrishabha": "वृषभ", "Mithuna": "मिथुन", "Karka": "कर्क", "Simha": "सिंह",
           "Kanya": "कन्या", "Tula": "तुला", "Vrischika": "वृश्चिक", "Dhanu": "धनु", "Makara": "मकर",
           "Kumbha": "कुंभ", "Meena": "मीन"}
ORD_HI = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पांचवें", 6: "छठे", 7: "सातवें", 8: "आठवें",
          9: "नौवें", 10: "दसवें", 11: "ग्यारहवें", 12: "बारहवें"}
RELATION_HI = {"conjunct": "युति", "exchange": "राशि-परिवर्तन", "mutual_aspect": "परस्पर दृष्टि",
               "one_way_aspect": "एकतरफ़ा दृष्टि", "same_planet": "एक ही ग्रह", "none": "कोई संबंध नहीं"}
SCOPE_HI = {"career": "करियर", "marriage": "विवाह", "wealth": "धन", "education": "शिक्षा", "children": "संतान",
            "character": "स्वभाव", "mind": "मन", "status": "प्रतिष्ठा", "family": "परिवार", "general": "सामान्य"}

# --- entity vocabularies (all Devanagari forms; matched by substring on normalised text, so inflected
#     forms match. A few weekday words (शनिवार, मंगलवार ...) therefore false-positive: that fails safe) --
GRAHA_DEV = {
    "Sun": ["सूर्य", "रवि"], "Moon": ["चंद्र", "चन्द्र"], "Mars": ["मंगल", "मङ्गल", "कुज"],
    "Mercury": ["बुध"], "Jupiter": ["गुरु", "बृहस्पति", "वृहस्पति"], "Venus": ["शुक्र"], "Saturn": ["शनि"],
    "Rahu": ["राहु"], "Ketu": ["केतु"],
}
SIGN_DEV = {
    "Mesha": ["मेष"], "Vrishabha": ["वृषभ"], "Mithuna": ["मिथुन"], "Karka": ["कर्क"], "Simha": ["सिंह"],
    "Kanya": ["कन्या"], "Tula": ["तुला"], "Vrischika": ["वृश्चिक"], "Dhanu": ["धनु"], "Makara": ["मकर"],
    "Kumbha": ["कुंभ", "कुम्भ"], "Meena": ["मीन"],
}
YOGA_DEV = {
    "ruchaka": ["रुचक"], "bhadra": ["भद्र योग", "भद्र-योग"], "hamsa": ["हंस योग", "हंस-योग"], "malavya": ["मालव्य"],
    "shasha": ["शश योग", "शश-योग"], "sunapha": ["सुनफा"], "anapha": ["अनफा"], "durudhara": ["दुरुधरा", "दुरधरा"],
    "kemadruma": ["केमद्रुम"], "vesi": ["वेशि"], "vosi": ["वोशि"], "ubhayachari": ["उभयचरी"],
    "gajakesari": ["गजकेसरी", "गजकेशरी"], "budhaditya": ["बुधादित्य"], "chandra_mangala": ["चंद्र-मंगल", "चंद्र मंगल"],
    "guru_chandala": ["गुरु चांडाल", "गुरु-चांडाल"], "angaraka": ["अंगारक"], "shrapit": ["श्रापित"],
    "manglik": ["मांगलिक", "मंगल दोष", "कुज दोष", "मंगली"], "kaal_sarp": ["कालसर्प", "काल सर्प"],
    "neecha_bhanga": ["नीचभंग", "नीच भंग"], "parivartana": ["परिवर्तन योग"], "yogakaraka": ["योगकारक"],
    "raja_yoga": ["राजयोग", "राज योग"], "dhana_yoga": ["धनयोग", "धन योग"], "mahapurusha": ["महापुरुष"],
    "vipareeta": ["विपरीत राज"], "harsha": ["हर्ष योग"], "sarala": ["सरल योग"], "vimala": ["विमल योग"],
    "kaal_amrit": ["कालामृत"], "musala": ["मुसल"], "nala": ["नल योग"], "rajju": ["रज्जु"], "vish": ["विष योग"],
    "dainya": ["दैन्य"], "khala": ["खल योग"], "nabhasa": ["नाभस"],
}
NAKSHATRA_DEV = {
    "ashwini": "अश्विनी", "bharani": "भरणी", "krittika": "कृतिका", "rohini": "रोहिणी", "mrigashira": "मृगशिरा",
    "ardra": "आर्द्रा", "punarvasu": "पुनर्वसु", "ashlesha": "आश्लेषा", "magha": "मघा",
    "purva phalguni": "पूर्वाफाल्गुनी", "uttara phalguni": "उत्तराफाल्गुनी", "swati": "स्वाति", "vishakha": "विशाखा",
    "anuradha": "अनुराधा", "jyeshtha": "ज्येष्ठा", "purva ashadha": "पूर्वाषाढा", "uttara ashadha": "उत्तराषाढा",
    "shravana": "श्रवण", "dhanishta": "धनिष्ठा", "shatabhisha": "शतभिषा", "purva bhadrapada": "पूर्वाभाद्रपद",
    "uttara bhadrapada": "उत्तराभाद्रपद", "revati": "रेवती",
}   # not covered (too common as ordinary words): हस्त, मूल, चित्रा, पुष्य

_ORD_FORMS = {
    1: "पहले|पहला|पहली|प्रथम", 2: "दूसरे|दूसरा|दूसरी|द्वितीय", 3: "तीसरे|तीसरा|तीसरी|तृतीय",
    4: "चौथे|चौथा|चौथी|चतुर्थ", 5: "पांचवें|पांचवां|पांचवीं|पंचम|पञ्चम", 6: "छठे|छठा|छठी|छठवें|षष्ठ",
    7: "सातवें|सातवां|सातवीं|सप्तम", 8: "आठवें|आठवां|आठवीं|अष्टम", 9: "नौवें|नौवां|नवें|नवां|नवम",
    10: "दसवें|दसवां|दशम", 11: "ग्यारहवें|ग्यारहवां|एकादश", 12: "बारहवें|बारहवां|द्वादश",
}
_NOUN = r"\s*(?:भाव|घर|स्थान|हाउस)"
HOUSE_DEV = [(n, re.compile(L("(?:" + norm(f) + ")") + _NOUN)) for n, f in _ORD_FORMS.items()]
HOUSE_DEV_NUM = re.compile(r"(\d{1,2})\s*(?:वें|वां|वे|वीं)?" + _NOUN + "|भाव\\s*(\\d{1,2})")


def dev_houses(text_norm: str) -> set:
    out = {n for n, rx in HOUSE_DEV if rx.search(text_norm)}
    for m in HOUSE_DEV_NUM.finditer(text_norm):
        out.add(int(m.group(1) or m.group(2)))
    return out
