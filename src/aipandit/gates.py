"""Deterministic grounding and safety gates. Nothing a composer produces reaches the user unless it
passes. These are plain code (regex, set logic), not a model, so they cannot be talked out of a rule.

Grounding (is it supported by this chart?)
  * a 'reading' statement cites only rules that fired for this chart AND were selected for this answer
  * a 'fact' statement cites only facts present in the store
  * every planet / sign / house / yoga / nakshatra / year / degree a statement mentions must appear in
    the evidence it cites; framing and caveat statements may mention none
Safety (is it appropriate to say?)
  * no death/lifespan, medical, financial, legal, remedy-selling, curse/fear or 'you will' language
  * cautionary readings are only allowed together with the "tendencies, not predictions" caveat
  * minors: no cautionary readings, nothing about marriage or romance
  * uncertain birth time: the answer must say so

Coverage: English and Hindi (Devanagari) names and common Hinglish phrases. Hinglish/Hindi safety
vocabulary is a first cut and needs review by native speakers before launch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .explain import describe_fact
from .hindi import DEV, GRAHA_DEV, NAKSHATRA_DEV, SIGN_DEV, YOGA_DEV, L, W, dev_houses, norm
from .phrasebook import is_system_text

# ---------------------------------------------------------------------------------- vocabulary
GRAHA_FORMS = {
    "Sun": ["sun", "surya", "ravi", "सूर्य", "रवि"],
    "Moon": ["moon", "chandra", "chandrama", "चंद्र", "चन्द्र", "चंद्रमा"],
    "Mars": ["mars", "mangal", "kuja", "मंगल", "कुज"],
    "Mercury": ["mercury", "budh", "budha", "बुध"],
    "Jupiter": ["jupiter", "guru", "brihaspati", "गुरु", "बृहस्पति"],
    "Venus": ["venus", "shukra", "शुक्र"],
    "Saturn": ["saturn", "shani", "शनि"],
    "Rahu": ["rahu", "राहु"],
    "Ketu": ["ketu", "केतु"],
}
SIGN_FORMS = {
    "Mesha": ["mesha", "mesh", "aries", "मेष"], "Vrishabha": ["vrishabha", "vrishabh", "taurus", "वृषभ"],
    "Mithuna": ["mithuna", "mithun", "gemini", "मिथुन"], "Karka": ["karka", "kark", "cancer", "कर्क"],
    "Simha": ["simha", "leo", "सिंह"], "Kanya": ["kanya", "virgo", "कन्या"],
    "Tula": ["tula", "libra", "तुला"], "Vrishchika": ["vrischika", "vrishchika", "vrishchik", "vrischik", "scorpio", "वृश्चिक"],
    "Dhanu": ["dhanu", "sagittarius", "धनु"], "Makara": ["makara", "makar", "capricorn", "मकर"],
    "Kumbha": ["kumbha", "kumbh", "aquarius", "कुंभ", "कुम्भ"], "Meena": ["meena", "meen", "pisces", "मीन"],
}
YOGA_FORMS = {
    "ruchaka": [r"ruchaka"], "bhadra": [r"bhadra"], "hamsa": [r"hamsa"], "malavya": [r"malavya"],
    "shasha": [r"shasha", r"sasa"], "sunapha": [r"sunapha"], "anapha": [r"anapha"],
    "durudhara": [r"durudhara"], "kemadruma": [r"kemadruma"], "vesi": [r"vesi"], "vosi": [r"vosi"],
    "ubhayachari": [r"ubhayachari"], "gajakesari": [r"gaja ?-?kesari", r"gajkesari"],
    "budhaditya": [r"budhaditya"], "chandra_mangala": [r"chandra[- ]mangal\w*"],
    "guru_chandala": [r"guru[- ]chandal\w*"], "angaraka": [r"angaraka"], "shrapit": [r"shrapit"],
    "vish": [r"vish yoga"], "manglik": [r"manglik", r"mangal dosh\w*", r"kuja dosh\w*"],
    "kaal_sarp": [r"kaal ?-?sarp", r"kal ?-?sarp"], "kaal_amrit": [r"kaal ?-?amrit"],
    "rajju": [r"rajju"], "musala": [r"musala"], "nala": [r"nala"], "harsha": [r"harsha"],
    "sarala": [r"sarala"], "vimala": [r"vimala"], "vipareeta": [r"vipareet\w*"],
    "neecha_bhanga": [r"neech\w* ?-?bhang\w*"], "parivartana": [r"parivartan\w*"],
    "dainya": [r"dainya"], "khala": [r"khala"], "yogakaraka": [r"yoga ?-?karaka"],
    "raja_yoga": [r"raja yoga", r"raj yog\w*"], "dhana_yoga": [r"dhana yoga", r"dhan yog\w*"],
    "mahapurusha": [r"mahapurush\w*", r"great person"], "nabhasa": [r"nabhasa"],
}
NAKSHATRAS = ["ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra", "punarvasu", "pushya",
              "ashlesha", "magha", "purva phalguni", "uttara phalguni", "hasta", "chitra", "swati", "vishakha",
              "anuradha", "jyeshtha", "moola", "mula", "purva ashadha", "uttara ashadha", "shravana", "dhanishta",
              "shatabhisha", "purva bhadrapada", "uttara bhadrapada", "revati"]


def _latin(forms):
    return re.compile(r"(?<![a-z])(?:" + "|".join(forms) + r")(?![a-z])", re.I)


_G_LAT = {k: _latin([re.escape(f) for f in v if f.isascii()]) for k, v in GRAHA_FORMS.items()}
_G_DEV = {k: [norm(f) for f in v] for k, v in GRAHA_DEV.items()}
_S_LAT = {k: _latin([re.escape(f) for f in v if f.isascii()]) for k, v in SIGN_FORMS.items()}
_S_DEV = {k: [norm(f) for f in v] for k, v in SIGN_DEV.items()}
_Y = {k: _latin(v) for k, v in YOGA_FORMS.items()}
_Y_DEV = {k: [norm(f) for f in v] for k, v in YOGA_DEV.items()}
_N = _latin([re.escape(n) for n in NAKSHATRAS])
_N_DEV = {k: norm(v) for k, v in NAKSHATRA_DEV.items()}
_ORDS = r"\d{1,2}(?:st|nd|rd|th)"
_HOUSE_LIST = re.compile(rf"((?:{_ORDS}(?:\s*(?:,|and|or|&|aur|ya)\s*)?)+)\s+(?:houses?|bhava|bhaav|bhav|ghar|from)\b", re.I)
_HOUSE = re.compile(r"\bhouses?\s+(\d{1,2})\b", re.I)
_HG_ORD = {1: "pehle|pehla|pehli", 2: "doosre|doosra|doosri|dusre", 3: "teesre|teesra|teesri|tisre", 4: "chauthe|chautha|chauthi",
           5: "paanchve|paanchva|paanchvi|panchve", 6: "chhathe|chhatha|chhathi|chhate", 7: "saatve|saatva|saatvi|satve",
           8: "aathve|aathva|aathvi|athve", 9: "nauve|nauva|nauvi|navve", 10: "dasve|dasva|dasvi|daswe",
           11: "gyarahve|gyarahva|gyarahvi|gyaarahve", 12: "barahve|barahva|barahvi|baarahve"}
_HG_HOUSE = [(n, re.compile(r"(?<![a-z])(?:" + f + r")\s+(?:bhaav|bhav|bhava|ghar)(?![a-z])", re.I)) for n, f in _HG_ORD.items()]
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_DEG = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*(?:°|degrees?|deg\b)", re.I)


def entities(text: str) -> set:
    """Chart-specific things a piece of text claims: planets, signs, yogas, houses, nakshatras, years, degrees.
    English, Latin-script Hindi and Devanagari are all mapped to the same canonical keys."""
    out: set = set()
    t = norm(text or "")
    for k, rx in _G_LAT.items():
        if rx.search(t) or any(f in t for f in _G_DEV[k]):
            out.add(f"graha:{k}")
    for k, rx in _S_LAT.items():
        if rx.search(t) or any(f in t for f in _S_DEV[k]):
            out.add(f"sign:{k}")
    for k, rx in _Y.items():
        if rx.search(t) or any(f in t for f in _Y_DEV.get(k, ())):
            out.add(f"yoga:{k}")
    for m in _N.finditer(t):
        out.add(f"nakshatra:{m.group(0).lower()}")
    for k, f in _N_DEV.items():
        if f in t:
            out.add(f"nakshatra:{k}")
    for m in _HOUSE_LIST.finditer(t):                     # "2nd house", "1st and 11th houses", "7th bhaav", "2nd from the Moon"
        for n in re.findall(r"\d{1,2}", m.group(1)):
            out.add(f"house:{int(n)}")
    for m in _HOUSE.finditer(t):
        out.add(f"house:{int(m.group(1))}")
    for n, rx in _HG_HOUSE:
        if rx.search(t):
            out.add(f"house:{n}")
    for n in dev_houses(t):
        out.add(f"house:{n}")
    for m in _YEAR.finditer(t):
        out.add(f"year:{m.group(0)}")
    for m in _DEG.finditer(t):
        out.add(f"degree:{m.group(0).lower()}")
    return out


# ---------------------------------------------------------------------------------- safety patterns
def _rx(latin: str, dev=()):
    """Latin alternatives (with \\b) plus Devanagari regex fragments (normalised, using W()/L() look-arounds)."""
    parts = [rf"\b(?:{latin})\b"] + [norm(d) for d in dev]
    return re.compile("|".join(parts), re.I)


_FUT = ("ेगा|ेगी|ेंगे|ेगे|ूंगा|ूंगी|ोगा|ोगी|ोगे|एगा|एगी|एंगे|एगे|ाओगे|ाओगी")
SAFETY = {
    "death_lifespan": _rx(r"death|die[sd]?|dying|dead|fatal|lifespan|life[- ]span|longevity|life expectancy|"
                          r"short[- ]lived|maut|mrityu|marna|marne|ayu|dehant|nidhan|jeevan ki (?:seema|avadhi)",
                          ("मृत्यु", "मौत", W("आयु"), "अल्पायु", "दीर्घायु", "मरना", "मरने", "मरेगा", "मरोगे", "देहांत",
                           "निधन", "जीवन[- ]अवधि")),
    "medical": _rx(r"diseases?|illness(?:es)?|cancer|tumou?rs?|surgery|surgical|medic\w*|diagnos\w*|cure[sd]?|"
                   r"pregnan\w*|infertil\w*|miscarriage|diabet\w*|heart attack|stroke|disorder|health\w*|"
                   r"bimari|bimar|dawai|dawa|swasthya|sehat|rog|ilaaj|ilaj|operation|chot|accident\w*|injur\w*",
                   ("बीमारी", "रोग", "दवाई", W("दवा"), "इलाज", "कैंसर", "ऑपरेशन", "सर्जरी", "दुर्घटना", "चोट", "स्वास्थ्य",
                    "सेहत", "गर्भ", "हृदयाघात", "मधुमेह")),
    "guarantee": _rx(r"definitely|certainly|guarantee[ds]?|for sure|without (?:a )?doubt|100 ?%|inevitabl\w*|"
                     r"destined|bound to|surely|pakka|pakki|zaroor|jaroor|avashya|nishchit(?: roop se)?|tay hai|atal",
                     ("गारंटी", "निश्चित रूप से", "निश्चित ही", W("पक्का"), W("पक्की"), W("जरूर"), "अवश्य", "बिना शक",
                      "तय है", "अटल")),
    "future_you": _rx(r"you (?:will|shall|are going to|are sure to)|your (?:wife|husband|spouse|partner|child|"
                      r"children|mother|father|boss|business) (?:will|is going to)|milega|milegi|hoga|hogi|honge|"
                      r"karenge|banega|banegi|(?!challenge\b|omega\b)[a-z]{2,}(?:ega|egi|enge)|[a-z]{2,}(?:unga|ungi)|(?:kar|mil|ban|pa|ja|jaa|ho|dekh|rah|sun|bol|le|de)o(?:ge|gi)",
                      (rf"[{DEV}]+(?:{_FUT})(?![{DEV}])",)),
    "fear_curse": _rx(r"curse[ds]?|doom\w*|ruin\w*|black magic|evil eye|jadu|tona|shraap|shaap|barbaad|tabaah|vinaash|buri nazar",
                      ("श्राप", "शाप", "अभिशाप", "बर्बाद", "तबाह", "काला जादू", "बुरी नजर", "विनाश")),
    "financial_advice": _rx(r"invest\w*|nivesh|share (?:market|bazaar)|stock\w*|crypto\w*|bitcoin|lottery|gambl\w*|satta\w*|trading",
                            ("निवेश", "शेयर", "सट्टा", "लॉटरी", "क्रिप्टो", "बिटकॉइन", "जुआ", "म्यूचुअल फंड")),
    "remedy_sales": _rx(r"gemstones?|gem|ruby|pearl|emerald|sapphire|puja|pooja|havan|yagya|yajna|donat\w*|"
                        r"ritual\w*|talisman|yantra|rudraksha?|mantras?|upay|upaay|ratna|ratan|neelam|pukhraj|manik|moti|moonga|panna|anguthi|jaap|daan|kharid\w*|pehn\w*|dharan|buy|purchase|pay",
                        ("पूजा", "हवन", "यज्ञ", L("दान"), "रत्न", "नीलम", "पुखराज", "माणिक", "मोती", "मूंगा", "पन्ना",
                         "अंगूठी", "उपाय", "मंत्र", "जाप", "यंत्र", "रुद्राक्ष", L("खरीद"), "पहनें", "पहनिए", "धारण")),
    "legal_advice": _rx(r"lawsuit|sue|custody|court case|legal advice|mukadma|mukdama|vakeel|vakil|adalat|kanooni salah", ("मुकदमा", "कानूनी सलाह", "वकील", "अदालत")),
}
MINOR_BLOCK = _rx(r"marri\w*|spouse|wife|husband|dating|romanc\w*|romantic|relationship\w*|partner\w*|"
                  r"shaadi|vivah|rishta|rishte|pati|patni|jeevan ?sa(?:a)?thi|saathi|prem|pyaar|sambandh",
                  ("विवाह", "शादी", "वैवाहिक", L("पति"), "पत्नी", "जीवनसाथी", "जीवन साथी", "रिश्ता", "संबंध", "प्रेम",
                   "साथी"))
NOT_A_PREDICTION = re.compile(r"not (?:a )?predictions?|भविष्यवाणी नहीं|prediction nahi|bhavishyavani nahi", re.I)
TIME_CAVEAT_MARKERS = ("birth time", "जन्म समय", "janm samay")


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str = ""
    index: int = -1


@dataclass
class GateReport:
    violations: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def codes(self) -> list:
        return sorted({v.code for v in self.violations})


@dataclass
class GateContext:
    firings: dict                  # rule_id -> Firing: the ONLY rules a reading statement may cite
    store: object                  # FactStore
    minor: bool = False
    time_uncertain: bool = False
    max_statements: int = 20
    max_chars: int = 700


def text_violations(text: str, minor: bool = False) -> list:
    text = norm(text)
    codes = [c for c, rx in SAFETY.items() if rx.search(text)]
    if minor and MINOR_BLOCK.search(text):
        codes.append("minor_topic")
    return codes


def check_text_only(text: str, minor: bool = False) -> GateReport:
    """For hard-stop replies (crisis / lifespan): safety patterns and 'no chart entities' only."""
    rep = GateReport()
    if not is_system_text(text):
        for c in text_violations(text, minor):
            rep.violations.append(Violation(c, text[:80]))
    if entities(text):
        rep.violations.append(Violation("ungrounded_entity", ", ".join(sorted(entities(text)))))
    return rep


def _allowed_entities(stmt, ctx: GateContext) -> set:
    allowed: set = set()
    for rid in stmt.rule_ids:
        f = ctx.firings.get(rid)
        if f is None:
            continue
        allowed |= entities(f.interpretation)
        allowed |= entities(rid.replace("_", " ").replace(".", " "))
        for fid in f.fact_ids:
            allowed |= entities(describe_fact(ctx.store, fid))
            sys_, subj, pred = fid.split(":", 2)
            allowed |= entities(f"{subj} {ctx.store.value(subj, pred, sys_)}")
    for fid in stmt.fact_ids:
        if fid in ctx.store:
            allowed |= entities(describe_fact(ctx.store, fid))
            sys_, subj, pred = fid.split(":", 2)
            allowed |= entities(f"{subj} {ctx.store.value(subj, pred, sys_)}")
    return allowed


def check(reading, ctx: GateContext) -> GateReport:
    rep = GateReport()
    add = lambda code, detail="", i=-1: rep.violations.append(Violation(code, detail, i))
    stmts = reading.statements
    if not stmts:
        add("empty")
    if len(stmts) > ctx.max_statements:
        add("too_long", f"{len(stmts)} statements")

    adverse_cited = False
    for i, s in enumerate(stmts):
        if len(s.text) > ctx.max_chars:
            add("statement_too_long", f"{len(s.text)} chars", i)
        if not (s.kind in ("framing", "caveat") and is_system_text(s.text)):
            for c in text_violations(s.text, ctx.minor):
                add(c, s.text[:80], i)

        if s.kind == "reading":
            if not s.rule_ids:
                add("uncited_reading", s.text[:80], i)
            if len({ctx.firings[r].system for r in s.rule_ids if r in ctx.firings}) > 1:
                add("mixed_systems", ", ".join(s.rule_ids), i)       # lenses are never blended inside one statement
            for rid in s.rule_ids:
                f = ctx.firings.get(rid)
                if f is None:
                    add("cites_unfired_or_unselected_rule", rid, i)
                elif f.adverse:
                    adverse_cited = True
                    if ctx.minor:
                        add("adverse_for_minor", rid, i)
            extra = entities(s.text) - _allowed_entities(s, ctx)
            if extra:
                add("ungrounded_entity", ", ".join(sorted(extra)), i)
        elif s.kind == "fact":
            missing = [fid for fid in s.fact_ids if fid not in ctx.store]
            if not s.fact_ids or missing:
                add("fact_not_in_store", ", ".join(missing) or "no fact ids", i)
            extra = entities(s.text) - _allowed_entities(s, ctx)
            if extra:
                add("ungrounded_entity", ", ".join(sorted(extra)), i)
        else:   # framing / caveat: must not mention any chart entity or cite anything
            if s.rule_ids or s.fact_ids:
                add("framing_with_citations", s.text[:60], i)
            ents = entities(s.text)
            if ents:
                add("ungrounded_entity", ", ".join(sorted(ents)), i)

    caveats = " ".join(s.text for s in stmts if s.kind == "caveat")
    if adverse_cited and not NOT_A_PREDICTION.search(caveats):
        add("adverse_without_caveat")
    if ctx.time_uncertain and not any(m in caveats.lower() for m in TIME_CAVEAT_MARKERS):
        add("missing_time_uncertainty_caveat")
    return rep
