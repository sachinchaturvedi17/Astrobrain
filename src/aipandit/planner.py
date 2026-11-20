"""Intent planner (the DEFAULT for Socket B, the consultation planner): keyword-based and deterministic.

It decides what kind of answer a question gets BEFORE any model is involved. Hard stops come first:
  crisis   -> supportive response and helplines, no astrology at all
  death    -> lifespan/death questions are declined (never answered from a chart)
Other sensitive topics (medical, financial, legal) are declined for that part of the question.
English, Latin-script Hindi (Hinglish) and Devanagari. Questions are matched on normalised text (see hindi.norm):
nukta, chandrabindu and Devanagari digits are folded so spelling variants match.
Keyword matching is a floor, not a ceiling: an LLM planner can later improve routing, but cannot override these
hard stops.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .hindi import L, W, norm


def _c(*parts: str) -> "re.Pattern":
    return re.compile(norm("|".join(parts)), re.I)


CRISIS = _c(
    r"kill (my ?self|me)", r"end (my life|it all)", r"\bsuicid", r"want to die", r"wanna die",
    r"don'?t want to (live|be alive)", r"no (reason|point) (to|in) (live|living)", r"better off dead",
    r"marna chah", r"jeena nahi", r"jina nahi", r"mar jana chah", r"khudkushi", r"aatmhatya", r"mar jau", r"mar jaun",
    r"mar jaaun", r"zindagi khatam", r"jindagi khatam", r"jeene ka man nahi", r"jeene ka mann nahi", r"jeene ki ichha nahi",
    r"khud ko khatam", r"jaan de(?:ni|na| dun| du)", r"jeene se thak",
    "आत्महत्या", "आत्म हत्या", "खुदकुशी", "जान दे", "मरना चाह", "मर जाना चाह", "मर जाऊं", "जीना नहीं", "जीने की इच्छा नहीं",
    "जीने का मन नहीं", "जीवन खत्म", "जिंदगी खत्म", "खुद को खत्म", "खुद को नुकसान", "जीने से तंग", "जीना नही")
DEATH = _c(
    r"when (will|am) i (die|going to die)", r"how long (will|do) i live", r"my death", r"age of death",
    r"life ?span", r"life expectancy", r"\bdeath\b", r"\bdie\b", r"\bmaut\b", r"mrityu", r"kab marunga",
    r"kab marungi", r"meri ayu", r"\bayu\b", r"kitna jeeunga", r"kitne saal jeeunga", r"kitne saal jiunga", r"kitna jiunga",
    "मृत्यु", "मौत", W("आयु"), "कब मरूंगा", "कब मरूंगी", "कब मरूँगा", "कितना जीऊंगा", "कितने साल जिऊंगा",
    "कितने दिन जिऊंगा", "कितने साल जीऊंगा", "जीवन[- ]अवधि", "देहांत", "निधन", "अल्पायु", "दीर्घायु")
DECLINE = {
    "medical": _c(r"\brog\b", r"ilaaj", r"\bdawa\b", r"\bdisease", r"illness", r"cancer", r"surgery", r"medicine", r"diagnos", r"pregnan", r"\bdoctor",
                  r"bimari", r"bimar", r"dawai", r"swasthya", r"\bsehat\b", r"operation", r"baby gender",
                  "बीमारी", "रोग", "दवाई", W("दवा"), "इलाज", "कैंसर", "ऑपरेशन", "सर्जरी", "स्वास्थ्य", "सेहत", "गर्भ"),
    "financial": _c(r"\binvest", r"stock", r"share market", r"crypto", r"bitcoin", r"lottery", r"gambl", r"\bsatta",
                    r"trading", r"mutual fund", r"nivesh", r"share bazaar", r"sattebazi", "निवेश", "शेयर", "क्रिप्टो", "बिटकॉइन", "सट्टा", "लॉटरी", "जुआ",
                    "म्यूचुअल फंड"),
    "legal": _c(r"court case", r"mukadma", r"mukdama", r"\bvakeel\b", r"adalat", r"lawsuit", r"\bsue\b", r"custody", r"legal advice", r"\bfir\b",
                "मुकदमा", "कानूनी", "वकील", "अदालत", "कोर्ट"),
}
TIMING = _c(r"\bwhen (will|should|would|do|can|am)\b", r"\bkab\b", r"which year", r"what year", r"how soon",
            r"how long until", r"kitne saal", r"kitne din", r"kis saal", r"kab tak", r"kitni jaldi", r"muhurat", r"muhurta", r"auspicious (date|time)", r"exact date",
            W("कब"), "किस साल", "किस वर्ष", "कितने साल में", "कितने दिन में", "कितनी जल्दी", "मुहूर्त", "तारीख")
DASHA = _c(r"dasha", r"mahadasha", r"antardasha", r"current period", r"running period", r"which period",
           r"planetary period", "दशा")
OVERVIEW = _c(r"overview", r"summary", r"summari[sz]e", r"my (kundli|kundali|chart|horoscope)", r"about me",
              r"tell me about", r"janam ?kundal", r"janmakundal", r"general", r"kundli", r"kundali", r"janmapatri", r"future", r"bhavishya", r"rashifal",
              "कुंडली", "जन्मपत्री", "जन्म पत्री", "मेरे बारे में", "सामान्य", "भविष्य")

NUMEROLOGY = _c(r"numerolog", r"\bmoolank\b", r"\bmulank\b", r"\bmulyank\b", r"bhagyank", r"bhagyaank", r"\bank\b", r"ankshastr",
                r"ank jyotish", r"lucky (?:number|no\b)", r"name number", r"naam ank", r"destiny number", r"birth number",
                r"personal year", r"\bankon\b", "अंकशास्त्र", "अंक ज्योतिष", "मूलांक", "भाग्यांक", "नामांक", "नाम अंक", W("अंक"), "शुभ अंक")
KUNDLI = _c(r"kundli", r"kundali", r"janmakundali", r"janam ?kundal\w*", r"\bchart\b", r"jyotish", r"parashari", r"horoscope",
            "कुंडली", "जन्मपत्री", "ज्योतिष")

SCOPE_WORDS = {
    "marriage": [r"marri", r"marital", r"wife", r"husband", r"spouse", r"partner", r"relationship", r"shaadi",
                 r"shadi", r"vivah", r"rishta", r"manglik", r"mangal dosh", r"love life", r"jeevan ?sa(a)?thi",
                 "विवाह", "शादी", "वैवाहिक", L("पति"), "पत्नी", "जीवनसाथी", "जीवन साथी", "रिश्ता", "मांगलिक",
                 "मंगल दोष", "कुज दोष", "प्रेम"],
    "career": [r"career", r"\bjob\b", r"profession", r"business", r"naukri", r"\bkaam\b", r"promotion", r"vyapar",
               r"vyavsay", r"vyavasay", r"karobar", r"rojgar", r"workplace",
               "करियर", "कैरियर", "नौकरी", "व्यवसाय", "व्यापार", "कारोबार", "रोजगार", W("काम"), "पदोन्नति",
               "प्रमोशन", "जॉब", "बिजनेस"],
    "wealth": [r"\bmoney", r"wealth", r"financ", r"income", r"earning", r"\bdhan\b", r"paisa", r"paise", r"savings",
               r"prosper", r"kamai",
               W("धन"), W("पैसा"), W("पैसे"), "संपत्ति", W("आय"), "कमाई", "दौलत", "आर्थिक", "अमीर"],
    "education": [r"educat", r"\bstudy", r"studies", r"exam", r"college", r"padhai", r"padhaai", r"degree",
                  "शिक्षा", "पढ़ाई", "पढ़ना", "परीक्षा", "विद्या", "कॉलेज", "डिग्री", "अध्ययन"],
    "children": [r"\bchild", r"children", r"\bkids?\b", r"\bbaby\b", r"santan", r"bachch", r"bachhe", r"bachche",
                 r"aulad", r"\bbeta\b", r"\bbeti\b",
                 "संतान", "बच्चे", "बच्चा", "बच्चों", "औलाद", "पुत्र", "बेटा", "बेटी"],
    "character": [r"personality", r"character", r"nature", r"temperament", r"swabhav", r"swabhaav",
                  "स्वभाव", "व्यक्तित्व", "चरित्र", "आदत", "प्रकृति"],
    "mind": [r"\bmind\b", r"mental", r"emotion", r"thinking", r"intellect", W("मन"), "मानसिक", "भावना", "सोच"],
    "status": [r"status", r"fame", r"reputation", r"respect", r"power", r"authority", r"name and fame",
               "प्रतिष्ठा", "मान[- ]सम्मान", "सम्मान", "यश", W("पद"), W("नाम"), "शोहरत", "प्रसिद्धि", "रुतबा"],
    "family": [r"family", r"parents", r"mother", r"father", r"siblings", r"brother", r"sister", r"parivar",
               r"\bmaa\b", r"\bpapa\b", r"\bbhai\b", r"\bbehan\b",
               "परिवार", "माता", "पिता", W("मां"), "पापा", "भाई", "बहन"],
}
SCOPE_RE = {k: _c(*v) for k, v in SCOPE_WORDS.items()}


@dataclass(frozen=True)
class Intent:
    kind: str                       # "crisis" | "death" | "readings"
    scopes: frozenset = frozenset()
    dasha: bool = False
    timing: bool = False
    declined: tuple = ()
    unclear: bool = False           # nothing recognisable: give an overview and invite a narrower question
    numerology: bool = False        # the user asked about numbers / numerology explicitly
    kundli: bool = False            # the user named the kundli / chart explicitly (keeps the Parashari lens on beside numerology)

    @property
    def overview(self) -> bool:
        return (self.kind == "readings" and not self.scopes and not self.dasha and not self.declined
                and not self.numerology)

    @property
    def numerology_only(self) -> bool:
        """Asked about numerology without naming the kundli: answer from the numerology lens alone."""
        return self.numerology and not self.kundli


def classify(question: str) -> Intent:
    q = norm(question or "")
    if CRISIS.search(q):
        return Intent("crisis")
    if DEATH.search(q):
        return Intent("death")
    declined = tuple(t for t, rx in DECLINE.items() if rx.search(q))
    scopes = frozenset(k for k, rx in SCOPE_RE.items() if rx.search(q))
    dasha = bool(DASHA.search(q))
    timing = bool(TIMING.search(q))
    numerology = bool(NUMEROLOGY.search(q))
    kundli = bool(KUNDLI.search(q))
    unclear = not (scopes or dasha or declined or numerology or OVERVIEW.search(q) or timing)
    return Intent("readings", scopes, dasha, timing, declined, unclear, numerology, kundli)
