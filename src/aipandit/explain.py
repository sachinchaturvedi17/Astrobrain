"""Human-readable descriptions of facts (used for the 'Basis' line). System-generated from the
Fact IR, never written by a model, so the evidence shown to the user is always the evidence used."""
from __future__ import annotations

from .hindi import GRAHA_HG, GRAHA_HI, ORD_HI, RELATION_HI, SIGN_HI
from .jyotish import SIGNS

_REL = {"conjunct": "conjunction", "exchange": "sign exchange", "mutual_aspect": "mutual aspect",
        "one_way_aspect": "one-way aspect", "same_planet": "the same planet", "none": "no relation"}


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _g(x: str) -> str:
    return GRAHA_HI.get(x, x)


def _o(n) -> str:
    return ORD_HI.get(int(n), str(n))


def _describe_hi(store, fact_id: str):
    """Hindi wording of a fact, or None if there is no Hindi template for it (caller falls back to English)."""
    system, subject, predicate = fact_id.split(":", 2)
    v = store.value(subject, predicate, system)
    if predicate == "house":
        return f"{_g(subject)} {_o(v)} भाव में है"
    if predicate == "dignity":
        word = {"exalted": "उच्च राशि", "debilitated": "नीच राशि", "own": "स्वराशि", "neutral": "सम राशि"}.get(v, v)
        return f"{_g(subject)} {word} में है"
    if predicate == "in_own_sign":
        return f"{_g(subject)} अपनी राशि में {'है' if v else 'नहीं है'}"
    if predicate.startswith("house_from_"):
        ref = _g(predicate.removeprefix("house_from_").capitalize())
        return f"{_g(subject)} और {ref} एक ही राशि में हैं" if v == 1 else f"{_g(subject)} {ref} से {_o(v)} स्थान पर है"
    if predicate == "conjunct":
        a, b = subject.split("+")
        return f"{_g(a)} और {_g(b)} {'एक ही राशि में हैं' if v else 'एक राशि में नहीं हैं'}"
    if predicate == "aspects":
        a, b = subject.split(">")
        return f"{_g(a)} की दृष्टि {_g(b)} पर {'है' if v else 'नहीं है'}"
    if predicate == "lord_house":
        return f"{_o(subject.removeprefix('house'))} भाव के स्वामी {_o(v)} भाव में हैं"
    if predicate == "lord":
        return f"{_o(subject.removeprefix('house'))} भाव के स्वामी {_g(v)} हैं"
    if predicate == "relation":
        a, b = subject.replace("lord", "").split("+")
        return f"{_o(a)} और {_o(b)} भाव के स्वामियों में {RELATION_HI.get(v, v)} है"
    if predicate == "nodal_hemming":
        return ("सातों ग्रह राहु-केतु अक्ष के एक ओर हैं" if v != "none" else "ग्रह राहु-केतु अक्ष के दोनों ओर हैं")
    if predicate == "dispositor_house":
        return f"{_g(subject)} की राशि के स्वामी {_o(v)} भाव में हैं"
    if predicate == "sign_index":
        return f"{_g(subject)} {SIGN_HI[SIGNS[v]]} राशि में है"
    return None


_RELATION_HG = {"conjunct": "yuti", "exchange": "rashi-parivartan", "mutual_aspect": "parasparik drishti",
                "one_way_aspect": "ekatarfa drishti", "same_planet": "ek hi grah", "none": "koi sambandh nahi"}
_NUM_EN = {"mulank": "Mulank (birth-day number)", "bhagyank": "Bhagyank (destiny number)",
           "name_number": "Name number (Chaldean)", "personal_year": "Personal-year number"}
_NUM_HG = {"mulank": "Mulank (janm-din ka ank)", "bhagyank": "Bhagyank (bhagya ank)",
           "name_number": "Naam ank (Chaldean)", "personal_year": "Personal-year ank"}
_NUM_HI = {"mulank": "मूलांक (जन्म-दिन का अंक)", "bhagyank": "भाग्यांक", "name_number": "नाम-अंक (कैल्डियन)",
           "personal_year": "व्यक्तिगत-वर्ष अंक"}


def _describe_numerology(store, subject, predicate, v, lang):
    """Description of a numerology fact in en / hg / hi, or None if it is not one."""
    if subject not in _NUM_EN:
        return None
    if predicate == "value":
        if lang == "hi":
            return f"{_NUM_HI[subject]} {v} है"
        return f"{_NUM_HG[subject]} {v} hai" if lang == "hg" else f"{_NUM_EN[subject]} is {v}"
    if predicate == "planet":
        n = store.value(subject, "value", "numerology")
        if lang == "hi":
            return f"{_NUM_HI[subject]} {n} भारतीय अंकशास्त्र में {GRAHA_HI.get(v, v)} से जुड़ा है"
        if lang == "hg":
            return f"{_NUM_HG[subject]} {n} Indian numerology mein {GRAHA_HG.get(v, v)} se juda hai"
        return f"{_NUM_EN[subject]} {n} is linked with {v} in Indian numerology"
    if predicate == "as_of_year":
        return {"hi": f"वर्ष {v} के लिए गणना", "hg": f"{v} saal ke liye ginti"}.get(lang, f"computed for {v}")
    return None


def _describe_hg(store, fact_id: str):
    system, subject, predicate = fact_id.split(":", 2)
    v = store.value(subject, predicate, system)
    g = lambda x: GRAHA_HG.get(x, x)
    o = lambda n: f"{int(n)}th" if not 1 <= int(n) <= 3 else {1: "1st", 2: "2nd", 3: "3rd"}[int(n)]
    if predicate == "house":
        return f"{g(subject)} {o(v)} bhaav mein hai"
    if predicate == "dignity":
        word = {"exalted": "uchch rashi", "debilitated": "neech rashi", "own": "swarashi", "neutral": "sam rashi"}.get(v, v)
        return f"{g(subject)} {word} mein hai"
    if predicate == "in_own_sign":
        return f"{g(subject)} apni rashi mein {'hai' if v else 'nahi hai'}"
    if predicate.startswith("house_from_"):
        ref = g(predicate.removeprefix("house_from_").capitalize())
        return f"{g(subject)} aur {ref} ek hi rashi mein hain" if v == 1 else f"{g(subject)} {ref} se {o(v)} sthaan par hai"
    if predicate == "conjunct":
        a, b = subject.split("+")
        return f"{g(a)} aur {g(b)} {'ek hi rashi mein hain' if v else 'ek rashi mein nahi hain'}"
    if predicate == "aspects":
        a, b = subject.split(">")
        return f"{g(a)} ki drishti {g(b)} par {'hai' if v else 'nahi hai'}"
    if predicate == "lord_house":
        return f"{o(subject.removeprefix('house'))} bhaav ke swami {o(v)} bhaav mein hain"
    if predicate == "lord":
        return f"{o(subject.removeprefix('house'))} bhaav ke swami {g(v)} hain"
    if predicate == "relation":
        a, b = subject.replace("lord", "").split("+")
        return f"{o(a)} aur {o(b)} bhaav ke swamiyon mein {_RELATION_HG.get(v, v)} hai"
    if predicate == "nodal_hemming":
        return ("saaton grah Rahu-Ketu axis ke ek taraf hain" if v != "none" else "grah Rahu-Ketu axis ke dono taraf hain")
    if predicate == "dispositor_house":
        return f"{g(subject)} ki rashi ke swami {o(v)} bhaav mein hain"
    if predicate == "sign_index":
        return f"{g(subject)} {SIGNS[v]} rashi mein hai"
    if subject == "dasha" and predicate in ("maha_lord", "antar_lord"):
        return f"chal rahi {'mahadasha' if predicate == 'maha_lord' else 'antardasha'} {g(v)} ki hai"
    if subject == "dasha" and predicate in ("maha_end", "antar_end"):
        return f"{'mahadasha' if predicate == 'maha_end' else 'antardasha'} {v} tak hai"
    return None


def describe_fact(store, fact_id: str, lang: str = "en") -> str:
    system, subject, predicate = fact_id.split(":", 2)
    if system == "numerology":
        v = store.value(subject, predicate, system)
        t = _describe_numerology(store, subject, predicate, v, lang)
        if t:
            return t
    if lang == "hi":
        t = _describe_hi(store, fact_id)
        if t:
            return t
    if lang == "hg":
        t = _describe_hg(store, fact_id)
        if t:
            return t
    v = store.value(subject, predicate, system)
    if predicate == "house":
        return f"{subject} is in house {v}"
    if predicate == "dignity":
        art = "an" if v[0] in "aeiou" else "a"
        return f"{subject} is in {art} {v} sign"
    if predicate == "in_own_sign":
        return f"{subject} is {'in' if v else 'not in'} its own sign"
    if predicate.startswith("house_from_"):
        ref = predicate.removeprefix("house_from_").capitalize()
        return f"{subject} shares a sign with the {ref}" if v == 1 else f"{subject} is {ordinal(v)} from the {ref}"
    if predicate == "conjunct":
        a, b = subject.split("+")
        return f"{a} and {b} {'share' if v else 'do not share'} a sign"
    if predicate == "aspects":
        a, b = subject.split(">")
        return f"{a} {'aspects' if v else 'does not aspect'} {b}"
    if predicate == "lord_house":
        return f"the lord of house {subject.removeprefix('house')} is in house {v}"
    if predicate == "lord":
        return f"the lord of house {subject.removeprefix('house')} is {v}"
    if predicate == "relation":
        a, b = subject.replace("lord", "").split("+")
        return f"the lords of houses {a} and {b} are in {_REL.get(v, v)}"
    if predicate == "nodal_hemming":
        return "all seven planets lie on one side of the Rahu-Ketu axis" if v != "none" else "the planets straddle the Rahu-Ketu axis"
    if predicate == "dispositor_house":
        return f"the lord of {subject}'s sign is in house {v}"
    if predicate == "sign_index":
        return f"{subject} is in {SIGNS[v]}"
    if subject == "dasha" and predicate == "maha_lord":
        return f"the running main period is {v}"
    if subject == "dasha" and predicate == "antar_lord":
        return f"the running sub-period is {v}"
    if subject == "dasha" and predicate == "maha_end":
        return f"the main period runs until {v}"
    if subject == "dasha" and predicate == "antar_end":
        return f"the sub-period runs until {v}"
    return f"{subject} {predicate} = {v}"
