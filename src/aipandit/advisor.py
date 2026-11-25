"""NaradVani's astrologer procedure: understand the question (topic + sub-question), remember what the person has told us,
work the chart the classical way (reasoner.Sheet), then answer from what was computed and show the working.

Public API (used by brain.answer):
    detect_intent(question, topic) -> str
    extract_slots(texts) -> {"rel": ..., "work": ...}
    advise(topic, question, chart, lang, sky=None, history=None, ephem=None, today=None) -> dict | None
Pure: no ephemeris access here (an `ephem` callable is injected for future transit windows), so it is unit-testable.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Dict, List, Optional, Tuple

from . import reasoner as R
from . import timeline
from .reasoner import Sheet, Item, Txt, ordinal

WHEN_RE = r"\bwhen\b|\bkab\b|how soon|how long|kitne (din|saal|mahine)|timing|कब|कितने (दिन|साल|महीने)"
INTENTS: List[Tuple[str, str]] = [
    ("trouble", r"problem|issue|fight|fighting|tension|break ?up|dikkat|jhag[ad]|unhappy|not happy|toxic|cheat|distance|misunderstand|argu|ego|dispute|crisis|stress|परेशान|दिक्कत|झगड़"),
    ("love_arr", r"love (or|vs|marriage)|arranged|prem vivah|inter.?caste|love ya|love-arranged"),
    ("type", r"partner type|type of (partner|spouse|husband|wife)|kind of (partner|spouse|husband|wife)|who will i marry|life ?partner|jeevansathi|what (kind|type|sort)|which (kind|type)|kaisa|kaisi|kis tarah|describe|looks? like|nature of|personality of|kya karta|kaun sa|कैसा|कैसी"),
    ("caution", r"careful|avoid|beware|caution|watch out|red flag|sambhal|dhyan|savdhan|सावधान"),
    ("delay", r"delay|\blate\b|still not|why (not|hasn|haven|isn|aren)|der se|kyun nahi|देर"),
    ("switch", r"switch|chang(e|ing) (my |the )?(job|company|field|career)|new job|leave my|resign|quit|job change|naukri badal|नौकरी बदल"),
    ("growth", r"promotion|growth|hike|raise|tarakki|badh|appraisal|senior|growth|उन्नति|तरक्की"),
    ("business", r"business|startup|start-up|own (company|work|venture)|self.?employ|apna kaam|व्यवसाय"),
    ("govt", r"govt|government|sarkari|upsc|\bssc\b|\bias\b|सरकारी"),
    ("debt", r"debt|loan|karz|karj|emi\b|udhaar|कर्ज"),
    ("savings", r"\bsav(e|ing|ings)\b|bachat|invest|जमा|बचत"),
    ("income", r"earn|income|salary|kamaa|more money|कमा"),
    ("abroad", r"abroad|foreign|videsh|overseas|visa|विदेश"),
    ("exam", r"exam|result|marks|rank|\bpass\b|neet|jee\b|upsc|board|परीक्षा|रिज़ल्ट"),
    ("focus", r"concentrat|focus|distract|dhyan nahi|mann nahi|lazy|procrastin"),
    ("field", r"which (field|line|stream|course|subject|branch)|field suits|kaun si (field|line)|career option|what (field|should i study|should i become)|medical|engineering|\bcommerce\b|\barts\b"),
    ("reconcile", r"ex back|come back|patch ?up|reconcil|wapas aayeg|second chance|purana pyar"),
    ("crush", r"\bcrush\b|propose|confess|attraction|like someone|pasand karta|pasand karti|date someone|true love"),
    ("vitality", r"vitality|stamina|tired|fatigue|low energy|weakness|exhaust|thakan|kamzori|urja|energy level"),
    ("routine", r"routine|sleep|diet|habit|lifestyle|dincharya|neend|aahar|daily habit"),
    ("phase", r"\bphase\b|dasha|daur|current situation|abhi kya chal|right now|these days|aaj kal|दशा|दौर"),
    ("explain", r"\bwhy\b|how do you know|how did you|reason|kaaran|kyun|explain|calculation|show me (the )?(math|working)|proof|basis"),
    ("advice", r"what should i do|what can i do|advice|suggest|solution|kya karu|kya karun|guide me|help me|next step|समाधान"),
    ("when", WHEN_RE),
]
_REL = r"relationship|marriage|husband|wife|spouse|partner|girlfriend|boyfriend|rishta|rishte|shaadi|pati|patni"
_TRB = r"problem|issue|trouble|fight|dikkat|tension|break ?up|not (happy|talking)|unhappy|toxic|crisis|jhag"
STATUS: List[Tuple[str, str]] = [
    ("trouble", rf"(?=.*({_REL}))(?=.*({_TRB}))"),
    ("single", r"\b(i am|i'?m|im|am|main|still)\s+(still\s+)?(single|alone|unmarried)|single hoon|akela hoon|akeli hoon|no (girlfriend|boyfriend|partner)|^(?:i'?m\s+|i am\s+)?(single|alone|unmarried|akela|akeli)$|अकेला हूँ|अकेली हूँ|अविवाहित"),
    ("relationship", r"in a relationship|\bdating\b|\bin love\b|i have a (girlfriend|boyfriend|partner)|rishte mein|relationship mein|प्रेम में|रिश्ते में"),
    ("married", r"\b(i am|i'?m|im|am)\s+(already\s+)?married|my (husband|wife|spouse)|shaadi ho (chuki|gayi|gai)|shaadi.?shuda|विवाहित हूँ|शादी हो चुकी"),
]
WORK: List[Tuple[str, str]] = [
    ("working", r"i (have|got) a job|i work|i'?m working|working (in|at|as)|job mein|naukri mein|employed|नौकरी में|my (job|boss|company|office)"),
    ("student", r"i'?m (a )?(student|studying)|i study|padh raha|padh rahi|college mein|student hoon|छात्र"),
    ("jobseeker", r"looking for (a )?job|job search|jobless|unemployed|no job|naukri nahi|naukri dhoondh|नौकरी नहीं"),
    ("business", r"my (own )?business|i run|i own|apna business|startup of mine|मेरा व्यवसाय"),
]


def extract_slots(texts: List[str]) -> Dict[str, str]:
    """Facts the person has told us, latest statement wins."""
    slots: Dict[str, str] = {}
    for t in texts:
        low = (t or "").lower()
        if len(low) > 400:
            continue
        for key, table in (("rel", STATUS), ("work", WORK)):
            for val, pat in table:
                if re.search(pat, low):
                    slots[key] = val
                    break
    return slots


def detect_intent(question: str, topic: str) -> str:
    q = question.lower()
    for name, pat in INTENTS:
        if re.search(pat, q):
            return name
    return "overview"


VALID = {
    "marriage": ("overview", "when", "type", "love_arr", "crush", "reconcile", "caution", "trouble", "delay", "advice", "explain", "phase"),
    "love": ("overview", "when", "type", "love_arr", "crush", "reconcile", "caution", "trouble", "delay", "advice", "explain", "phase"),
    "career": ("overview", "when", "switch", "growth", "business", "govt", "advice", "explain", "phase", "field", "delay"),
    "wealth": ("overview", "when", "savings", "income", "debt", "advice", "explain", "phase", "delay"),
    "education": ("overview", "when", "exam", "abroad", "focus", "field", "advice", "explain", "phase", "delay"),
    "health": ("overview", "when", "vitality", "routine", "caution", "trouble", "delay", "advice", "explain", "phase"),
    "children": ("overview", "when", "advice", "explain", "phase", "delay"),
}
FOLLOW: Dict[str, List[Tuple[str, str, str]]] = {
    "marriage": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
                 ("when", "When will I get married?", "Meri shaadi kab hogi?"), ("type", "What kind of partner suits me?", "Kaisa jeevansathi mere liye theek hai?"),
                 ("love_arr", "Love or arranged marriage?", "Love marriage ya arranged?"), ("caution", "What should I be careful about?", "Mujhe kis baat se savdhaan rehna chahiye?"),
                 ("delay", "Is there any delay?", "Kya shaadi mein der hai?"), ("trouble", "Why are there problems in relationships?", "Rishton mein dikkat kyun aati hai?")],
    "love": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
             ("when", "When will love blossom?", "Pyaar ke liye achha samay kab hai?"), ("type", "What kind of partner suits me?", "Kaisa saathi mere liye theek hai?"),
             ("crush", "How does romance work in my chart?", "Mere chart mein pyaar aur aakarshan kaisa hai?"), ("caution", "What should I be careful about?", "Mujhe kis baat se savdhaan rehna chahiye?"),
             ("trouble", "Why do misunderstandings happen?", "Rishton mein galatfahmi kyun aati hai?"), ("advice", "What should I do next?", "Ab mujhe kya karna chahiye?")],
    "career": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
               ("when", "When will my career grow?", "Mera career kab badhega?"), ("switch", "Should I change my job?", "Kya mujhe job badalni chahiye?"),
               ("business", "Job or business?", "Job ya business?"), ("field", "Which field suits me?", "Kaun si field mere liye theek hai?"),
               ("growth", "Will I get a promotion?", "Kya promotion milega?"), ("advice", "What should I do next?", "Ab mujhe kya karna chahiye?")],
    "wealth": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
               ("income", "How can I earn more?", "Main zyada kaise kamaun?"), ("savings", "Will I be able to save?", "Kya main bachat kar paunga?"),
               ("debt", "What about loans and debt?", "Karz ke baare mein kya?"), ("when", "When will money improve?", "Paisa kab badhega?"), ("advice", "What should I do next?", "Ab mujhe kya karna chahiye?")],
    "education": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
                  ("exam", "How will my exams go?", "Meri exams kaisi rahengi?"), ("field", "Which field suits me?", "Kaun si field mere liye theek hai?"),
                  ("abroad", "Will I study abroad?", "Kya main videsh mein padhunga?"), ("focus", "Why can't I concentrate?", "Mera dhyan kyun nahi lagta?"), ("when", "When will I succeed?", "Mujhe safalta kab milegi?")],
    "health": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
               ("vitality", "How is my overall vitality?", "Meri urja aur stamina kaisa hai?"), ("routine", "What daily routine suits me?", "Kaun si dincharya mere liye theek hai?"),
               ("caution", "What drains my energy?", "Meri urja kis baat se kam hoti hai?"), ("when", "When does my energy improve?", "Meri urja kab behtar hogi?"),
               ("advice", "What habits help most?", "Kaun si aadatein sabse zyada madad karengi?")],
    "children": [("phase", "Which phase am I in now?", "Abhi main kaunse daur mein hoon?"),
                ("when", "When is a good time?", "Achha samay kab hai?"), ("advice", "What should I do next?", "Ab mujhe kya karna chahiye?")],
}
STATUS_FLOW = {"single": ["type", "when", "caution"], "relationship": ["caution", "love_arr", "when"], "married": ["caution", "advice"], "trouble": ["trouble", "advice"],
               "working": ["switch", "growth"], "student": ["field", "when"], "jobseeker": ["when", "field"], "business": ["growth", "advice"]}
STATUS_CHIPS = {"marriage": [("single", "I'm single", "Main single hoon"), ("relationship", "I'm in a relationship", "Main relationship mein hoon"), ("married", "I'm married", "Meri shaadi ho chuki hai")],
                "love": [("single", "I'm single", "Main single hoon"), ("relationship", "I'm in a relationship", "Main relationship mein hoon"), ("married", "I'm married", "Meri shaadi ho chuki hai")],
                "career": [("working", "I have a job", "Meri job hai"), ("student", "I'm a student", "Main student hoon"), ("jobseeker", "I'm looking for a job", "Main job dhoondh raha hoon")]}

TOPIC_SPEC = {
    "marriage": dict(primary=7, houses=(7, 2, 11), label=("marriage and partnership", "vivah aur saajhedari")),
    "love": dict(primary=5, houses=(5, 7, 11), label=("love and romance", "pyaar aur rishte")),
    "career": dict(primary=10, houses=(10, 6, 11), label=("career", "career")),
    "wealth": dict(primary=2, houses=(2, 11, 9), label=("money and wealth", "dhan")),
    "education": dict(primary=5, houses=(5, 4, 9), label=("studies", "padhai")),
    "children": dict(primary=5, houses=(5, 9, 2), label=("children and family growth", "santan")),
    "family": dict(primary=4, houses=(4, 2, 3), label=("home and family", "ghar aur parivaar")),
    "property": dict(primary=4, houses=(4, 11, 2), label=("property and home", "property aur ghar")),
    "foreign": dict(primary=12, houses=(12, 9, 3), label=("going abroad", "videsh")),
    "health": dict(primary=1, houses=(1, 6, 8), label=("general wellbeing", "general sehat")),
    "general": dict(primary=1, houses=(1, 5, 9), label=("life in general", "jeevan")),
}
KARAKAS = {"marriage": ("Venus", "Jupiter"), "love": ("Venus", "Moon", "Mars"), "career": ("Sun", "Saturn", "Mercury"), "wealth": ("Jupiter", "Venus"), "education": ("Mercury", "Jupiter"),
           "children": ("Jupiter",), "family": ("Moon", "Jupiter"), "property": ("Mars", "Venus"), "foreign": ("Rahu", "Saturn"), "health": ("Sun", "Moon"), "general": ("Sun", "Moon")}

PLACEMENT = {  # what it means for the matter when its lord sits in house N
    1: ("it is closely tied to you and your own effort", "yeh seedha aap aur aapke apne prayas se juda hai"),
    2: ("family, savings and speech play a big part", "parivaar, bachat aur vaani ka bada role hai"),
    3: ("your own initiative, communication and short travel drive it", "aapki pehal, baat-cheet aur chhoti yatrayein ise chalati hain"),
    4: ("home, comfort and emotional security shape it", "ghar, sukh aur bhavnatmak suraksha ise aakaar deti hain"),
    5: ("romance, learning and creativity feed into it", "pyaar, seekhna aur creativity ise poshit karte hain"),
    6: ("service, daily routine and handling friction are central, and results come through effort", "seva, rozmarra aur ghisaav sambhalna kendra mein hai, nateeje mehnat se aate hain"),
    7: ("partnerships and dealings with other people are central", "saajhedari aur logon ke saath lena-dena kendra mein hai"),
    8: ("sudden turns, hidden matters and transformation are involved, so it matures through changes", "achaanak mod, chhipi baatein aur parivartan jude hain, isliye badlaavon se pakta hai"),
    9: ("luck, mentors, higher learning and distant places help it", "bhagya, guru, uchch shiksha aur door ki jagahein ise madad karti hain"),
    10: ("status, profession and public standing are linked to it", "pad, vyavsaay aur samaaj mein sthaan ise jude hain"),
    11: ("friends, networks and fulfilment of wishes support it", "dost, network aur ichhaon ki poorti ise sahara deti hain"),
    12: ("distance, foreign links, privacy or expenses are involved, so it can come from afar or after some letting go", "doori, videsh se jod, nijta ya kharch jude hain, isliye door se ya kuch chhodne ke baad aa sakta hai"),
}
SIGN_PARTNER = {
    "Mesha": ("energetic, direct and independent", "urjavaan, seedha aur swatantra"), "Vrishabha": ("calm, loyal and comfort-loving", "shaant, wafadaar aur sukh-pasand"),
    "Mithuna": ("talkative, witty and curious", "baatuni, hazir-jawab aur jigyasu"), "Karka": ("caring, emotional and home-loving", "pareshaan karne ki jagah dekhbhaal karne wala, bhavuk aur ghar-pasand"),
    "Simha": ("proud, warm-hearted and a natural leader", "swabhimaani, dil ka garam aur naisargik leader"), "Kanya": ("practical, detail-minded and service-oriented", "vyavaharik, baareek nazar wala aur sevabhaavi"),
    "Tula": ("charming, balanced and relationship-minded", "aakarshak, santulit aur rishte ko mahatva dene wala"), "Vrishchika": ("intense, private and deeply loyal", "gehra, nijta pasand aur bahut wafadaar"),
    "Dhanu": ("open-minded, philosophical and fond of freedom", "khule vichar wala, darshanik aur azaadi-pasand"), "Makara": ("serious, responsible and ambitious", "gambhir, zimmedaar aur mahatvakanksha wala"),
    "Kumbha": ("friendly, unconventional and independent in thinking", "dostana, alag soch wala aur swatantra vichar wala"), "Meena": ("gentle, intuitive and sensitive", "komal, antarjnaani aur samvedansheel"),
}
PLANET_FIELDS = {
    "Sun": ("government, administration, leadership, medicine", "sarkari kaam, prashasan, leadership, medicine"),
    "Moon": ("care-giving, hospitality, public-facing work, food, nursing", "dekhbhaal, hospitality, janata se juda kaam, khaana, nursing"),
    "Mars": ("engineering, defence, police, sports, surgery, real estate", "engineering, raksha, police, khel, surgery, real estate"),
    "Mercury": ("tech, commerce, accounts, writing, analytics, trade", "tech, commerce, accounts, lekhan, analytics, vyapaar"),
    "Jupiter": ("teaching, law, finance, advisory, counselling", "shikshan, kaanoon, finance, salah, counselling"),
    "Venus": ("design, arts, media, fashion, hospitality, luxury goods", "design, kala, media, fashion, hospitality, luxury"),
    "Saturn": ("operations, infrastructure, manufacturing, research, long-haul service", "operations, infrastructure, manufacturing, research, lambi seva"),
    "Rahu": ("technology, foreign-linked work, media, unconventional fields", "technology, videsh se jude kaam, media, alag tarah ki fields"),
    "Ketu": ("research, spiritual work, coding, back-end and specialist roles", "research, adhyatmik kaam, coding, specialist bhoomikayein"),
}
OBSTACLE_ADVICE = {
    "Saturn": ("go slowly and be consistent; delay here is about maturity, not denial", "dheere aur lagataar chaliye; yahan der parakhne ke liye hai, inkaar nahi"),
    "Mars": ("keep arguments cool and pause before reacting; channel the heat into exercise or work", "behes thandi rakhein aur react karne se pehle ruk jaayein; garmi ko vyayam ya kaam mein lagayein"),
    "Rahu": ("check facts, avoid idealising or hiding things; clarity beats excitement", "tathya jaanchein, aadarsh banane ya chhupane se bachein; spashtata josh se behtar hai"),
    "Ketu": ("stay emotionally present and say what you feel; withdrawal is the trap", "bhavnaon mein maujood rahein aur apni baat kahein; door ho jaana hi jaal hai"),
    "Sun": ("watch ego and let the other side be heard fully", "ahankaar par nazar rakhein aur doosre ko poori tarah sunein"),
}


def _facts_for(sheet: Sheet, topic: str):
    spec = TOPIC_SPEC.get(topic, TOPIC_SPEC["general"])
    kar = KARAKAS.get(topic, ("Sun", "Moon"))
    if topic == "marriage":
        kar = ("Jupiter", "Venus") if sheet.gender == "female" else ("Venus", "Jupiter")
    return spec, kar


def _verdict_word(sheet: Sheet, label: str) -> str:
    return {"strong": sheet.t("strongly supportive", "kaafi madadgaar"), "good": sheet.t("supportive", "madadgaar"),
            "mixed": sheet.t("mixed", "mila-jula"), "demanding": sheet.t("demanding (needs patience and effort)", "mushkil (sabr aur mehnat maangta hai)")}[label]


def _bul(lines: List[str]) -> str:
    return "".join("\n• " + x for x in lines)


def _number(lines: List[Item]) -> List[str]:
    out = []
    for i, (tag, txt) in enumerate(lines, 1):
        out.append(f"{i}. {'+' if tag == '+' else '−' if tag == '-' else '•'} {txt}")
    return out


def _lord_meaning(sheet: Sheet, house: int) -> str:
    lh = sheet.house_of(sheet.lord(house))
    if not lh:
        return ""
    en, hg = PLACEMENT[lh]
    return sheet.t("In your chart, this area works like this: {m}.", "Aapke chart mein yeh kshetra aise kaam karta hai: {m}.", m=en if sheet.lang == "en" else hg)


def _obstacle_planets(sheet: Sheet, h: int) -> List[str]:
    ps = [p for p in sheet.occupants(h) + sheet.aspectors(h) if p in R.MALEFIC]
    return list(dict.fromkeys(ps))


def _advice_for(sheet: Sheet, planets: List[str]) -> List[str]:
    return [OBSTACLE_ADVICE[p][0 if sheet.lang == "en" else 1] for p in planets if p in OBSTACLE_ADVICE]


# ------------------------------------------------------------------------------------------ follow-up continuity
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", (s or "").lower()).strip()


def _already_said(line: str, previous: str) -> bool:
    """True when this paragraph was already sent to this person about this subject.

    Compares a normalised prefix, so a reworded tail does not hide a duplicate opening. Keeping the previous text in
    the signature lets the caller drop it from the next answer instead of repeating the same verdict or explanation.
    """
    a, b = _norm(line), _norm(previous)
    if len(a) < 28 or not b:
        return False
    return a[:80] in b


# A short answer like "Marketing/Sales" is a request for that field, not a new topic.
FIELD_HINT = re.compile(
    r"\b(tech|software|coding|developer|programm|engineer|\bit\b|data|analytics|\bai\b|"
    r"medical|doctor|mbbs|nurs|pharma|dental|"
    r"teach|professor|lecturer|research|academ|phd|"
    r"law|legal|lawyer|advocate|judge|"
    r"design|artist|\bart\b|music|film|media|fashion|content|writ|journal|"
    r"govt|government|sarkari|upsc|\bssc\b|\bias\b|police|army|defence|defense|civil service|"
    r"business|startup|entrepreneur|self.?employ|"
    r"market|marketing|sales|advertis|brand|\bhr\b|human resource|recruit|"
    r"finance|bank|account|commerce|audit|\bca\b|cfa|econom)\b", re.I)
FIELD_PLANETS: List[Tuple[str, Tuple[str, ...], str, str]] = [
    (r"market|sales|advertis|brand|\bhr\b|human resource|recruit|communicat", ("Mercury", "Venus", "Mars"),
     "marketing, sales and people-facing work", "marketing, sales aur logon se jude kaam"),
    (r"tech|software|coding|developer|programm|engineer|\bit\b|data|analytics|\bai\b", ("Mercury", "Rahu", "Saturn"),
     "technology and analytical work", "technology aur analytical kaam"),
    (r"medical|doctor|mbbs|nurs|pharma|dental", ("Sun", "Mars", "Jupiter"),
     "medicine and care work", "medicine aur dekhbhaal ka kaam"),
    (r"teach|professor|lecturer|research|academ|phd", ("Jupiter", "Mercury", "Moon"),
     "teaching and research", "shikshan aur research"),
    (r"law|legal|lawyer|advocate|judge", ("Jupiter", "Saturn", "Mercury"),
     "law and advisory work", "kaanoon aur salah ka kaam"),
    (r"design|artist|\bart\b|music|film|media|fashion|content|writ|journal", ("Venus", "Moon", "Mercury"),
     "creative, design and media work", "creative, design aur media ka kaam"),
    (r"govt|government|sarkari|upsc|\bssc\b|\bias\b|police|army|defence|defense|civil service", ("Sun", "Mars", "Saturn"),
     "government and uniformed service", "sarkari aur vardi wali seva"),
    (r"business|startup|entrepreneur|self.?employ", ("Mercury", "Venus", "Jupiter"),
     "business and self-employment", "business aur apna kaam"),
    (r"finance|bank|account|commerce|audit|\bca\b|cfa|econom", ("Mercury", "Jupiter", "Venus"),
     "finance, accounts and commerce", "finance, accounts aur commerce"),
]


def _field_note(sheet: Sheet, question: str, dom: List[str]) -> str:
    """A specific read of the field the person just named, from the chart's own planet strengths."""
    q = (question or "").lower()
    for pat, planets, en, hg in FIELD_PLANETS:
        if not (re.search(pat, q) or re.search(pat, question or "", re.I)):
            continue
        present = [p for p in planets if p in sheet.pl]
        if not present:
            return ""
        fits = [sheet.t("{p} is {s}", "{p} {s} hai", p=p, s=sheet.sw(p)) for p in present]
        linked = [p for p in present if p in dom and sheet.strength(p) != "weak"]
        text = sheet.t("You asked about {w}. That field draws on {p}; in your chart {f}. ",
                       "Aapne {w} ke baare mein poochha. Yeh kshetra {p} par tikta hai; aapke chart mein {f}. ",
                       w=en if sheet.lang == "en" else hg, p=sheet.plist(present), f=", ".join(fits))
        if linked:
            text += sheet.t("It also lines up with the planets that already hold up this area for you, so it is a natural direction to test.",
                            "Yeh un grahon se bhi mel khaata hai jo aapke chart mein is kshetra ko saath de rahe hain, isliye ise aazmaana swabhavik hai.")
        else:
            text += sheet.t("It is workable, but it will ask you to build the weak part on purpose rather than rely on natural ease.",
                            "Yeh possible hai, par kamzor hisse ko jaan-boojhkar banana padega, sirf swabhavik aasani par nahi chhodna.")
        return text
    # older keyword loop: a field word that maps through the classical planet significations
    m = re.search(r"\b\w*?(tech|software|coding|engineer|doctor|medic|teach|law\b|design|\bart|govt|government|business|financ|bank|media|writ|commerce|sport|music)\w*", q)
    if not m:
        return ""
    word, key = m.group(0), m.group(1).strip()
    for p, (fe, fh) in PLANET_FIELDS.items():
        if key in fe.lower() or key in fh.lower():
            st = sheet.strength(p)
            fit = {"strong": sheet.t("looks like a natural fit for you", "aapke liye swabhavik mel lagta hai"), "ok": sheet.t("is workable for you, with steady effort", "aapke liye possible hai, lagataar mehnat ke saath"),
                   "weak": sheet.t("is possible but will ask for extra effort and a strong routine", "possible hai par adhik mehnat aur pakka routine maangega")}[st]
            return sheet.t("You asked about {w}: it {f}" + (" and it matches the strengths of your chart." if p in dom else "."), "Aapne {w} ke baare mein poochha: yeh {f}" + (" aur aapke chart ki taakat se mel khaata hai." if p in dom else "."), w=word, f=fit)
    return ""


def _transit_until(sheet: Sheet, planet: str, ephem, years: float = 3.0):
    """(sign now, date it changes) for a transiting planet, from the same calendar the Panchang uses."""
    cur = (sheet.sky.get(planet) or {}).get("sign")
    if cur not in R.RASHIS or ephem is None:
        return None
    d, end = sheet.today, sheet.today + _dt.timedelta(days=int(years * 365.25))
    step = 10
    while d <= end:
        d += _dt.timedelta(days=step)
        try:
            s = ephem(d).get(planet)
        except Exception:
            return None
        if s in R.RASHIS and s != cur:
            return cur, d
    return cur, None



# ------------------------------------------------------------------------------------------ topic procedures
def _manglik(sheet: Sheet) -> Optional[Item]:
    h = sheet.house_of("Mars")
    if not h:
        return None
    base = sheet.t("your Moon sign", "Chandra rashi") if sheet.moon_basis else sheet.t("the lagna", "lagna")
    if h in (1, 2, 4, 7, 8, 12):
        return ("-", sheet.tp("Mars sits in the {h} counted from {b}: this is the classical Mangal (Kuja) dosha pattern. Traditional cancellations exist and are not evaluated here.",
                              "Mangal {b} se {h} mein hai: yeh parampara ka Mangal (Kuja) dosh yog hai. Parampara mein iske parihaar hain jinhe yahan nahi parakha gaya.",
                              "Mars is placed the way traditional astrology calls Mangal dosha. It is very common, has well-known traditional answers, and matters most when matching with a partner's chart.",
                              "Mangal us sthiti mein hai jise parampara Mangal dosh kehti hai. Yeh bahut aam hai, iske jaane-maane parampara ke upay hain, aur sabse zyada jeevansathi ki kundli milaate samay mayne rakhta hai.",
                              h=sheet.ho(h), b=base))
    return ("+", sheet.tp("Mars is in the {h} counted from {b}, so the classical Mangal dosha pattern is not present.", "Mangal {b} se {h} mein hai, isliye Mangal dosh ka yog nahi banta.", "", "", h=sheet.ho(h), b=base))


def _love_signals(sheet: Sheet) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """(technical, plain) indicator pairs for a love-led and for a family-arranged marriage."""
    love: List[Tuple[str, str]] = []
    arr: List[Tuple[str, str]] = []
    l5, l7 = sheet.lord(5), sheet.lord(7)
    rel = sheet.relation(l5, l7) if l5 != l7 else "same"
    if rel in ("conjunct", "exchange", "mutual", "same"):
        love.append((sheet.t("the lords of the 5th (romance) and 7th (marriage) are directly linked ({r})", "5ve (pyaar) aur 7ve (vivah) bhav ke swami seedhe jude hain ({r})", r=rel),
                     sheet.t("romance and marriage are directly connected in your chart", "aapke chart mein pyaar aur vivah seedhe jude hain")))
    elif rel in ("a_on_b", "b_on_a"):
        love.append((sheet.t("the lords of the 5th and 7th influence each other by aspect", "5ve aur 7ve bhav ke swami drishti se ek-doosre ko prabhavit karte hain"),
                     sheet.t("romance and marriage influence each other in your chart", "aapke chart mein pyaar aur vivah ek-doosre ko prabhavit karte hain")))
    if "Venus" in sheet.pl and sheet.relation("Venus", "Mars") in ("conjunct", "mutual", "a_on_b", "b_on_a"):
        love.append((sheet.t("Venus and Mars are connected, which favours attraction-led bonds", "Shukra aur Mangal ka sambandh hai, jo aakarshan se bane rishte ko badhawa deta hai"),
                     sheet.t("the planets of love and passion are linked, which favours bonds that begin with attraction", "pyaar aur junoon ke graha jude hain, jo aakarshan se shuru hone wale rishte ko badhawa dete hain")))
    if "Venus" in sheet.pl and sheet.relation("Venus", "Rahu") in ("conjunct", "mutual", "a_on_b", "b_on_a"):
        love.append((sheet.t("Venus is linked with Rahu, which favours unconventional or inter-community bonds", "Shukra ka Rahu se sambandh hai, jo alag ya doosre samaaj ke rishte ko badhawa deta hai"),
                     sheet.t("the planet of love is linked with Rahu, which favours unconventional or inter-community bonds", "pyaar ka graha Rahu se juda hai, jo alag ya doosre samaaj ke rishte ko badhawa deta hai")))
    if "Rahu" in sheet.occupants(5) + sheet.occupants(7):
        love.append((sheet.t("Rahu is in the 5th or 7th house", "Rahu 5ve ya 7ve bhav mein hai"),
                     sheet.t("Rahu sits in the area of romance or marriage, which often brings an unusual or self-chosen partner", "Rahu pyaar ya vivah ke kshetra mein hai, jo aksar alag ya khud chuna hua saathi laata hai")))
    lh7 = sheet.house_of(l7)
    if lh7 in (2, 4, 9, 11):
        arr.append((sheet.t("the 7th lord sits in the {h}, a family and community house, which favours introductions through family", "7ve ka swami {h} mein hai, jo parivaar aur samaaj ka bhav hai aur parivaar ke zariye parichay ko badhawa deta hai", h=sheet.ho(lh7)),
                    sheet.t("marriage is linked to family and community in your chart, which favours introductions through family", "aapke chart mein vivah parivaar aur samaaj se juda hai, jo parivaar ke zariye parichay ko badhawa deta hai")))
    if "Jupiter" in sheet.aspectors(7) + sheet.occupants(7):
        arr.append((sheet.t("Jupiter influences the 7th house, which favours a traditional, family-blessed match", "Guru 7ve bhav ko prabhavit karta hai, jo parampara se, parivaar ki dua wale rishte ko badhawa deta hai"),
                    sheet.t("Jupiter, the planet of blessings, watches over marriage, which favours a traditional, family-blessed match", "Guru, aashirwad ka graha, vivah par nazar rakhta hai, jo parampara wale, parivaar ki dua wale rishte ko badhawa deta hai")))
    if "Saturn" in sheet.aspectors(7) + sheet.occupants(7):
        arr.append((sheet.t("Saturn influences the 7th house, which favours a slower, more formal route", "Shani 7ve bhav ko prabhavit karta hai, jo dheemi aur aupcharik raah ko badhawa deta hai"),
                    sheet.t("Saturn influences marriage, which favours a slower and more formal route", "Shani vivah ko prabhavit karta hai, jo dheemi aur aupcharik raah ko badhawa deta hai")))
    return love, arr


def _sade_sati_note(sheet: Sheet, ephem) -> str:
    """When the current Sade Sati phase ends and when the whole 7.5 years finish (Saturn's sign counted from the Moon sign)."""
    ms = (sheet.chart.get("moon") or {}).get("sign")
    cur = sheet.sade_sati()
    if not (ephem and cur and ms in R.RASHIS):
        return ""
    start = {"rising": 12, "peak": 1, "setting": 2}[cur]
    phase_end = all_end = None
    d = sheet.today
    for _ in range(int(9 * 365 / 15)):
        d += _dt.timedelta(days=15)
        try:
            s = ephem(d).get("Saturn")
        except Exception:
            return ""
        if s not in R.RASHIS:
            return ""
        rel = (R.RASHIS.index(s) - R.RASHIS.index(ms)) % 12 + 1
        if phase_end is None and rel != start and rel in (12, 1, 2, 3) and ((rel - start) % 12) in (1, 2, 3):
            phase_end = d
        if rel == 3 and ((3 - start) % 12) in (1, 2, 3):
            all_end = d
            break
    if not all_end:
        return ""
    return sheet.t("By the movement of the planets, this phase changes around {a} and the whole 7.5-year period completes around {b}; the pressure usually lightens step by step toward that.",
                   "Gochar calendar ke hisaab se yeh charan {a} ke aas-paas badlega aur poora saade saat saal ka daur {b} ke aas-paas poora hoga; dabaav aksar us taraf dheere-dheere halka hota hai.",
                   a=timeline._mon(phase_end or all_end, sheet.lang), b=timeline._mon(all_end, sheet.lang))


def _jupiter_windows(sheet: Sheet, primary: int, ephem, label: str) -> Tuple[List[str], List[str]]:
    """(technical, plain) lines for the date ranges in which Jupiter supports the house."""
    wins = R.transit_windows(sheet, "Jupiter", primary, ephem)
    tech = [sheet.t("Jupiter (the great supporter) passes through or looks at your {h} during {r}.", "Guru {h} par aata ya drishti daalta hai: {r}.", h=sheet.ho(primary), r=R.fmt_range(a, b, sheet.lang)) for a, b in wins]
    plain = [sheet.t("{r}: a favourable stretch for {t}", "{r}: {t} ke liye anukool daur", r=R.fmt_range(a, b, sheet.lang), t=label) for a, b in wins]
    return tech, plain


def _nice_date(v, lang):
    try:
        return timeline._mon(_dt.date.fromisoformat(str(v)[:10]), lang)
    except Exception:
        return str(v or "")


def _dasha_plain(sheet: Sheet, houses: Tuple[int, ...], karakas: Tuple[str, ...]) -> str:
    from .voice import DASHA_THEME
    d = sheet.dasha()
    if not d:
        return ""
    li = 0 if sheet.lang == "en" else 1
    linked = sheet.roles(d["antar"], houses, karakas) or sheet.roles(d["maha"], houses, karakas)
    th = DASHA_THEME.get(d["antar"], DASHA_THEME["Jupiter"])[li]
    base = sheet.t("You are in a {ma}-{an} phase" + (", running until {u}" if d.get("antar_end") else "") + ". This phase is mostly about {th}",
                   "Aap {ma}-{an} ke daur mein hain" + (", jo {u} tak chalega" if d.get("antar_end") else "") + ". Is daur ka mudda hai {th}",
                   ma=sheet.p(d["maha"]), an=sheet.p(d["antar"]), u=_nice_date(d.get("antar_end"), sheet.lang), th=th)
    return base + (sheet.t(", and it is directly linked to this area.", ", aur yeh seedha is kshetra se juda hai.") if linked else ".")


def _plain_windows(sheet: Sheet, involved: List[str], label: str, limit: int = 3) -> List[str]:
    if not sheet.dasha():
        return []
    out = []
    for w in timeline.windows(sheet.chart, involved, sheet.today, years_ahead=6, limit=limit):
        a, b = max(w["start"], sheet.today), w["end"]
        out.append(sheet.t("{a} - {b}: your {an} phase, which switches {t} on{now}", "{a} - {b}: aapka {an} ka daur, jo {t} ko sakriya karta hai{now}",
                           a=timeline._mon(a, sheet.lang), b=timeline._mon(b, sheet.lang), an=sheet.p(w["antar"]), t=label,
                           now=sheet.t(" (running now)", " (abhi chal raha hai)") if w["now"] else ""))
    return out


def advise(topic: str, question: str, chart: Dict[str, Any], lang: str = "en", sky: Optional[Dict[str, Any]] = None,
           history: Optional[List[Dict[str, Any]]] = None, ephem=None, today: Optional[_dt.date] = None,
           intent: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if topic not in TOPIC_SPEC or not chart or chart.get("lagna") not in R.RASHIS:
        return None
    if lang == "hi":
        return None      # this layer is written in English and Hinglish; Hindi is answered by the Hindi voice path
    history = history or []
    sheet = Sheet(chart, lang, sky, today)
    L = sheet.lang
    spec, karakas = _facts_for(sheet, topic)
    primary, houses = spec["primary"], spec["houses"]
    user_texts = [m.get("text", "") for m in history if m.get("role") == "user"] + [question]
    slots = extract_slots(user_texts)
    cur = extract_slots([question])
    prev_text = "\n".join(m.get("text", "") for m in history
                          if m.get("role") in ("bot", "assistant", "ai") and (m.get("topic") or topic) == topic)
    valid = VALID.get(topic, ("overview", "when", "advice", "explain", "phase"))
    bot_intents = [m.get("intent") for m in history if m.get("role") == "bot" and m.get("intent")]
    answered = set(bot_intents) | ({detect_intent(m.get("text", ""), topic) for m in history if m.get("role") == "user"} if not bot_intents else set())
    if intent is None:
        intent = detect_intent(question, topic)
        if re.match(r"^\s*(yes|yeah|yep|sure|ok|okay|please|haan|han|ha|bilkul|zaroor|go ahead|tell me|batao|bataiye|हाँ|हां|जी)\W*(tell me|please|go ahead|batao|bataiye)?\W*$", question.lower()):
            last = bot_intents[-1] if bot_intents else None
            nxt = [k for k, _e, _h in FOLLOW.get(topic, []) if k not in answered]
            intent = "phase" if last in ("trouble", "caution") and "phase" not in answered else (nxt[0] if nxt else "advice")
        stat = cur.get("rel") if topic in ("marriage", "love") else cur.get("work") if topic == "career" else None
        if intent == "overview" and stat:
            order = STATUS_FLOW.get(stat, ["overview"])
            intent = next((k for k in order if k not in answered), order[-1])
        if intent == "trouble" and topic not in ("marriage", "love", "health"):
            intent = "advice"
        if intent == "field" and topic not in ("career", "education"):
            intent = "overview"
    # "Marketing/Sales" or "tech" after a studies answer is a field follow-up, not a fresh overview.
    if intent == "overview" and topic in ("career", "education") and FIELD_HINT.search(question or "") and len((question or "").split()) <= 8:
        intent = "field"

    if intent not in valid:
        intent = "overview" if intent not in ("when", "advice", "explain", "phase") else intent
    repeat = intent in answered and intent not in ("explain", "phase", "overview") and not (cur.get("rel") or cur.get("work"))
    # ---------------- 1. the working (technical; shown only under "Why this answer?")
    L = sheet.lang
    T = sheet.t
    label_topic = spec["label"][0 if L == "en" else 1]
    basis = (T("Basis: your birth time is not exact, so I count houses from your Moon sign {m} as the 1st house (Chandra Lagna). House-based reading is good for tendencies but less precise.",
               "Aadhaar: aapka janm samay exact nahi hai, isliye main Chandra rashi {m} ko 1st bhav maankar ginta hoon (Chandra Lagna). Yeh rujhaan ke liye theek hai par kam precise.", m=sheet.sg(chart["lagna"]))
             if sheet.moon_basis else T("Basis: your lagna is {m}; houses are counted from it.", "Aadhaar: aapka lagna {m} hai; bhav usi se ginte hain.", m=sheet.sg(chart["lagna"])))
    items: List[Item] = []
    for h in houses:
        items += sheet.judge(h, full=(h == primary))
    items += sheet.karaka_items(karakas)
    extra: List[Item] = []
    mg = _manglik(sheet) if topic == "marriage" else None
    if mg:
        extra.append(mg)
    love, arr = _love_signals(sheet) if topic in ("marriage", "love") else ([], [])
    if topic in ("marriage", "love") and intent in ("love_arr", "crush"):
        extra += [("+", sheet.tp(T("Love-marriage indicator: ", "Love-marriage sanket: ") + x[0] + ".", T("Love-marriage indicator: ", "Love-marriage sanket: ") + x[0] + ".", x[1] + ".", x[1] + ".")) for x in love]
        extra += [("+", sheet.tp(T("Arranged-marriage indicator: ", "Arranged-marriage sanket: ") + x[0] + ".", T("Arranged-marriage indicator: ", "Arranged-marriage sanket: ") + x[0] + ".", x[1] + ".", x[1] + ".")) for x in arr]
    if topic == "health":
        l1, l6 = sheet.lord(1), sheet.lord(6)
        if sheet.house_of(l1) in R.GOOD_HOUSES and sheet.strength(l1) != "weak":
            extra.append(("+", sheet.tp("The 1st lord {L} is well placed, supporting baseline stamina and recovery.",
                                        "Lagna swami {L} achhi sthiti mein hai, jo mool urja aur recovery ko sahara deta hai.",
                                        "Your core stamina and bounce-back capacity are well supported.",
                                        "Aapki mool urja aur wapas sambhalne ki kshamta ko achha sahara mila hai.", L=sheet.p(l1))))
        if sheet.house_of(l6) in (1, 8, 12):
            extra.append(("-", sheet.tp("The 6th lord {L} connects with the 1st/8th/12th house, showing sensitivity to irregular routine and overwork.",
                                        "6ve bhav ka swami {L} 1/8/12 bhav se juda hai, jo aniyamit dincharya aur thakan ke prati samvedansheelta dikhata hai.",
                                        "Irregular sleep or overwork drains your energy faster than average, so pacing matters.",
                                        "Aniyamit neend ya zyada kaam aapki urja ko jaldi kam karta hai, isliye santulan zaroori hai.", L=sheet.p(l6))))
    if topic == "career":
        l10 = sheet.lord(10)
        s10 = sheet.sign_of(l10)
        if s10:
            kind = "movable" if s10 in R.MOVABLE else "fixed" if s10 in R.FIXED else "dual"
            extra.append(("·", sheet.tp("The 10th lord is in a {k} sign: " + {"movable": "careers of this kind tend to involve change and movement.", "fixed": "careers of this kind tend to be steady and long-lasting.", "dual": "careers of this kind tend to be flexible and multi-skilled."}[kind],
                                        "10ve ka swami {k} rashi mein hai: " + {"movable": "aise career mein badlaav aur gatishilta rehti hai.", "fixed": "aise career sthir aur lambe chalte hain.", "dual": "aise career lachile aur bahu-kaushal wale hote hain."}[kind],
                                        {"movable": "Your career pattern is changeable: movement and change come naturally to you.", "fixed": "Your career pattern is steady: you do best staying and building over the long term.", "dual": "Your career pattern is flexible: you can handle several skills and directions."}[kind],
                                        {"movable": "Aapka career pattern badalta rehne wala hai: badlaav aur gati aapko swabhavik lagte hain.", "fixed": "Aapka career pattern sthir hai: aap lambe samay tak tikkar banane mein behtar hain.", "dual": "Aapka career pattern lachila hai: aap kai kaushal aur dishayein sambhal sakte hain."}[kind],
                                        k=sheet.t(kind, {"movable": "chara", "fixed": "sthir", "dual": "dwisvabhav"}[kind]))))
    if topic == "wealth":
        l2, l11 = sheet.lord(2), sheet.lord(11)
        rel = sheet.relation(l2, l11) if l2 != l11 else "same"
        if rel in ("conjunct", "exchange", "mutual", "same", "a_on_b", "b_on_a"):
            extra.append(("+", sheet.tp("The lords of the 2nd (savings) and 11th (income) are connected ({r}), a classical sign of money flowing and staying.",
                                        "2ve (bachat) aur 11ve (aay) ke swami jude hain ({r}), jo paisa aane aur tikne ka parampara ka sanket hai.",
                                        "Your earning area and your saving area are connected in your chart, a classical sign of money both coming in and staying.",
                                        "Aapke chart mein kamai aur bachat ke kshetra jude hain, jo paisa aane aur tikne ka parampara ka sanket hai.", r=rel)))
        else:
            extra.append(("·", sheet.tp("The lords of the 2nd (savings) and 11th (income) are not linked, so income and savings need to be connected by deliberate planning.",
                                        "2ve (bachat) aur 11ve (aay) ke swami jude nahi hain, isliye aay aur bachat ko soch-samajhkar jodna padega.",
                                        "Your earning and saving areas are not directly linked, so income will not turn into savings by itself; it needs a deliberate plan.",
                                        "Aapke chart mein kamai aur bachat ke kshetra seedhe jude nahi hain, isliye aay apne aap bachat nahi banegi; soch-samajhkar plan chahiye.")))
        l12 = sheet.house_of(sheet.lord(12))
        if l12 in (2, 11):
            extra.append(("-", sheet.tp("The 12th lord (expenses) sits in the {h}, so spending tends to eat into earning and saving.", "12ve (kharch) ka swami {h} mein hai, isliye kharch kamai aur bachat ko khaata hai.",
                                        "Spending pulls hard on your earning and saving, so expenses need watching.", "Kharch aapki kamai aur bachat ko zor se kheenchta hai, isliye kharch par nazar rakhni hogi.", h=sheet.ho(l12))))
    items += extra
    dl = sheet.dasha_lines(houses, karakas)
    tr = sheet.transit_lines(primary)
    ss = sheet.sade_sati()
    ss_item: List[Item] = []
    if ss and (intent in ("trouble", "phase", "delay", "explain", "advice") or topic in ("career", "marriage", "love", "health")):
        ss_item = [("-", sheet.tp("Saturn is transiting " + {"rising": "the 12th from your Moon: the first phase of Sade Sati (a 7.5-year Saturn period of tests and restructuring).",
                                                              "peak": "over your Moon sign: the middle phase of Sade Sati, usually the most demanding for mind and routine.",
                                                              "setting": "the 2nd from your Moon: the last phase of Sade Sati, where pressure gradually eases."}[ss],
                                  "Shani " + {"rising": "Chandra se 12ve mein hai: Sade Sati ka pehla charan (saade saat saal ka Shani ka daur, pareeksha aur punarrachna).",
                                              "peak": "aapki Chandra rashi par hai: Sade Sati ka beech ka charan, jo aam taur par man aur dincharya ke liye sabse kadak hota hai.",
                                              "setting": "Chandra se 2ve mein hai: Sade Sati ka antim charan, jahan dabaav dheere-dheere kam hota hai."}[ss],
                                  {"rising": "Saturn has begun its 7.5-year pass around your Moon sign (known as Sade Sati). This is the early phase, where pressure slowly builds.",
                                   "peak": "Saturn is passing right over your Moon sign (known as Sade Sati), a long stretch that tests patience and matures you. It usually feels heaviest on the mind and daily routine.",
                                   "setting": "Saturn is finishing its 7.5-year pass around your Moon sign (Sade Sati). This is the last phase, where pressure gradually eases."}[ss],
                                  {"rising": "Shani ne aapki Chandra rashi ke aas-paas apna saade saat saal ka chakkar shuru kiya hai (Sade Sati). Yeh shuruaati charan hai, jahan dabaav dheere-dheere badhta hai.",
                                   "peak": "Shani seedha aapki Chandra rashi par se guzar raha hai (Sade Sati), ek lamba daur jo sabr ki pareeksha leta hai aur parakv banata hai. Yeh aam taur par man aur dincharya par sabse bhaari lagta hai.",
                                   "setting": "Shani aapki Chandra rashi ke aas-paas apna saade saat saal ka chakkar poora kar raha hai (Sade Sati). Yeh antim charan hai, jahan dabaav dheere-dheere kam hota hai."}[ss]))]
    main_items = sheet.judge(primary, full=True)
    plus, minus, label = R.tally(items + main_items + tr + ss_item)       # the main house counts double
    stepped = False
    pl_h = sheet.house_of(sheet.lord(primary))
    if pl_h in R.DUSTHANA and label in ("strong", "good") and sheet.lord(primary) in sheet.pl and not sheet.neecha_bhanga(sheet.lord(primary)):
        label, stepped = ("good" if label == "strong" else "mixed"), True
    calc = _number([("·", Txt(basis))] + items + dl + tr + ss_item)
    if stepped:
        calc.append(T("Adjustment: the lord of the main house sits in a difficult house (6/8/12), so I step the verdict down one level.", "Samayojan: mukhya bhav ka swami kathin bhav (6/8/12) mein hai, isliye natije ko ek star neeche karta hoon."))
    calc.append(T("Tally (the main house counts double): {p} supports and {m} obstacles found, so the chart reads as {v} for this question.",
                  "Joda-ghata (mukhya bhav do baar ginta hoon): {p} sahayak aur {m} baadhak mile, isliye is sawaal ke liye chart {v} dikhta hai.", p=plus, m=minus, v=_verdict_word(sheet, label)))
    # ---------------- 2. timing
    involved = [sheet.lord(h) for h in houses] + list(karakas) + [p for h in houses for p in sheet.occupants(h)]
    if topic == "career" and intent == "switch":
        involved += [sheet.lord(9), sheet.lord(3), sheet.lord(12)]
    involved = list(dict.fromkeys(involved))
    timing: List[str] = sheet.dasha_windows(involved, limit=3)
    plain_wins: List[str] = _plain_windows(sheet, involved, label_topic, 3)
    jt, jp = _jupiter_windows(sheet, primary, ephem, label_topic)
    timing += jt
    plain_wins += jp
    if topic == "career" and intent in ("growth", "when", "switch"):
        jt2, jp2 = _jupiter_windows(sheet, 11, ephem, T("income and gains", "aay aur laabh"))
        timing += jt2[:1]
        plain_wins += jp2[:1]
    # ---------------- 3. the answer, in plain words
    sup = [x.plain for t, x in items + tr if t == "+" and getattr(x, "plain", "")]
    obs = [x.plain for t, x in items + tr + ss_item if t == "-" and getattr(x, "plain", "")]
    pl_mal = _obstacle_planets(sheet, primary)
    lm = _lord_meaning(sheet, primary)
    rel, work = slots.get("rel"), slots.get("work")
    status_note = ""
    if topic in ("marriage", "love") and rel and cur.get("rel"):
        status_note = {"single": T("You said you are single, so I am reading this as what is coming for you.", "Aapne kaha ki aap single hain, isliye main ise aage aane wale ke roop mein padh raha hoon."),
                       "relationship": T("You said you are in a relationship, so I am reading this for that bond.", "Aapne kaha ki aap relationship mein hain, isliye main ise us rishte ke liye padh raha hoon."),
                       "married": T("You said you are married, so I am reading this for your marriage.", "Aapne kaha ki aapki shaadi ho chuki hai, isliye main ise aapke vivah ke liye padh raha hoon."),
                       "trouble": T("You mentioned trouble in the relationship, so I focused on what is straining it.", "Aapne rishte mein dikkat bataai, isliye main dekh raha hoon ki use kya kheench raha hai.")}.get(rel, "")
    if topic == "career" and work and cur.get("work"):
        status_note = {"working": T("You said you are working, so this is about growth or change, not a fresh start.", "Aapne kaha ki aap kaam kar rahe hain, isliye yeh tarakki ya badlaav ki baat hai, nayi shuruaat ki nahi."),
                       "student": T("You said you are studying, so this is about direction and skill-building.", "Aapne kaha ki aap padh rahe hain, isliye yeh disha aur skill banane ki baat hai."),
                       "jobseeker": T("You said you are looking for a job, so this is about when and where doors open.", "Aapne kaha ki aap job dhoondh rahe hain, isliye yeh us samay aur jagah ki baat hai jab darwaze khulenge."),
                       "business": T("You said you run a business, so this is about growth and stability.", "Aapne kaha ki aapka business hai, isliye yeh vriddhi aur sthirta ki baat hai.")}.get(work, "")
    tl = label_topic
    OPEN = {"strong": T("Good news first: your chart is strongly supportive for {t}.", "Pehle achhi baat: {t} ke liye aapka chart kaafi madadgaar hai.", t=tl),
            "good": T("Your chart is supportive for {t}.", "{t} ke liye aapka chart madadgaar hai.", t=tl),
            "mixed": T("Your chart shows a mixed picture for {t}: some real strengths and some things that need care.", "{t} ke liye aapka chart mila-jula chitra dikhata hai: kuch asli taakat aur kuch baatein jinme dhyaan chahiye.", t=tl),
            "demanding": T("{t} asks for extra patience and effort in your chart, but it is workable with the right approach.", "{t} mein aapke chart mein zyada sabr aur mehnat lagti hai, par sahi tareeke se yeh ho sakta hai.", t=tl)}
    OPEN = {k: v[:1].upper() + v[1:] for k, v in OPEN.items()}
    head = OPEN[label]
    if intent in ("trouble", "caution"):
        head = T("I am sorry if things feel heavy. Here is what your chart says about the pressure points in {t}; overall the picture is {v}.", "Agar sab bhaari lag raha hai toh mujhe afsos hai. Yeh raha ki {t} mein aapke chart ke dabaav ke bindu kya hain; kul milakar chitra {v} hai.",
                 t=tl, v=T({"strong": "good", "good": "fairly good", "mixed": "mixed", "demanding": "demanding"}[label], {"strong": "achha", "good": "theek-thaak achha", "mixed": "mila-jula", "demanding": "mushkil"}[label]))
    elif intent == "explain":
        head = ""
    elif _already_said(head, prev_text):
        head = ""       # the verdict was already given for this subject: answer the new sub-question instead
    helps = sup[0] if sup else ""
    cares = obs[0] if obs else ""
    advice_planets = pl_mal
    body: List[str] = []
    advice: List[str] = []
    wins_block = (lambda title: [title + _bul([w for w in plain_wins if not _already_said(w, prev_text)])] if any(not _already_said(w, prev_text) for w in plain_wins) else [])
    no_dates = T("I cannot give dated stretches right now: exact timing needs your exact birth time, and the planetary calendar was not available. What I can say rests on the strengths above.",
                 "Abhi tareekh wale daur nahi de sakta: exact dasha ke liye aapka exact janm samay chahiye aur gochar calendar uplabdh nahi tha. Jo kehta hoon woh upar ki taakat par aadharit hai.")
    patient = (T("Because your chart supports this, the tendency is for it to happen once a supportive stretch arrives and you act on it.", "Chart is vishay ka saath deta hai, isliye rujhaan hai ki sahayak daur aate hi aur aapke kadam uthane par yeh ho.")
               if label in ("strong", "good") else T("Your chart asks for patience here: a mature, well-chosen path tends to work better than a quick one.", "Aapka chart yahan sabr maangta hai: soch-samajhkar chuna hua raasta jaldi wale se behtar chalta hai."))
    if intent == "overview":
        body += [helps and T("What helps most: {x}", "Sabse zyada madad: {x}", x=helps), cares and T("What needs care: {x}", "Kis baat mein dhyaan: {x}", x=cares), lm]
        body += wins_block(T("Favourable stretches ahead:", "Aage ke anukool daur:"))[:1]
    if intent in ("when", "delay"):
        body += wins_block(T("Favourable stretches ahead (these show when this area is switched on, not exact dates):", "Aage ke anukool daur (yeh dikhate hain ki yeh kshetra kab sakriya hai, exact tarikh nahi):")) or [no_dates]
        if pl_mal and (intent == "delay" or label in ("mixed", "demanding")):
            body.append(T("The main thing slowing this down is {p}.", "Ise dheema karne wala mukhya kaaran {p} hai.", p=sheet.plist(pl_mal)))
        if topic in ("marriage", "love") or intent == "delay":
            body.append(patient)
    # ---- topic specifics
    if topic in ("marriage", "love"):
        if intent == "type":
            target_h = 5 if topic == "love" else 7
            en, hg = SIGN_PARTNER[sheet.sign(target_h)]
            line_t = T("A partner who is {a} tends to suit you best.", "{a} jeevansathi aapko sabse achha suit karta hai.", a=en if L == "en" else hg)
            body.append(line_t[:1].upper() + line_t[1:])
            body.append(lm)
            kv = sheet.sign_of("Venus")
            if kv:
                body.append(T("The way you love is {a}.", "Aapke pyaar karne ka tareeka {a} hai.", a=SIGN_PARTNER[kv][0] if L == "en" else SIGN_PARTNER[kv][1]))
            occ_t = sheet.occupants(target_h)
            if occ_t:
                body.append(T("{p} adds its own flavour to the kind of partner you attract.", "{p} aapke jeevansathi ke swabhav mein apna rang jodta hai.", p=sheet.plist(occ_t)))
        if intent == "love_arr":
            lean = "love" if len(love) > len(arr) else "arranged" if len(arr) > len(love) else "either"
            body.append({"love": T("Your chart leans towards a love or self-chosen marriage.", "Aapka chart love ya khud chuni hui shaadi ki taraf jhukta hai."),
                         "arranged": T("Your chart leans towards an arranged or family-introduced marriage.", "Aapka chart arranged ya parivaar dwara parichit shaadi ki taraf jhukta hai."),
                         "either": T("Your chart does not lean strongly either way, so both routes can work. Meeting through friends or family and then choosing for yourself suits you best.", "Aapka chart kisi ek taraf zyada nahi jhukta, isliye dono raste chal sakte hain. Dost ya parivaar ke zariye milkar khud chunna aapko sabse behtar rahega.")}[lean])
            why = [x[1] for x in (love if lean == "love" else arr if lean == "arranged" else love + arr)]
            if why:
                body.append(T("Why: ", "Kyun: ") + "; ".join(w[:1].upper() + w[1:] for w in why[:3]) + ".")
        if intent == "crush":
            kv = sheet.sign_of("Venus")
            style = (SIGN_PARTNER[kv][0] if L == "en" else SIGN_PARTNER[kv][1]) if kv else (SIGN_PARTNER[sheet.sign(5)][0] if L == "en" else SIGN_PARTNER[sheet.sign(5)][1])
            body.append(T("In romance and attraction, your natural style is {a}.", "Pyaar aur aakarshan mein aapka swabhavik tareeka {a} hai.", a=style))
            if love:
                body.append(T("What supports romance in your chart: ", "Aapke chart mein pyaar ko kya sahara deta hai: ") + "; ".join(x[1] for x in love[:2]) + ".")
            body.append(lm)
            advice.append(T("Let attraction grow through shared conversations and steady time together rather than rushing a confession.", "Jaldbaazi mein izhaar karne ke bajaye baat-cheet aur saath bitaye samay se aakarshan ko badhne dein."))
        if intent == "reconcile":
            steady = sheet.strength("Venus") != "weak" and "Saturn" not in pl_mal
            body.append(T("Your chart favours repairing a bond when both sides are willing to talk calmly and address what caused the distance.", "Jab dono taraf se shaant baat-cheet aur doori ke kaaran ko suljhane ki ichha ho, tab aapka chart rishta sudhaarne ka saath deta hai.")
                        if steady else
                        T("Rebuilding an old bond asks for patience and changed habits here; if the same pattern repeats, clarity is kinder than forcing it.", "Purane rishte ko phir se jodna yahan sabr aur badli hui aadatein maangta hai; agar wahi purana pattern dohrata hai, toh zabardasti se behtar saaf baat hai."))
            advice.append(T("Give space first, then have one honest conversation without blame before deciding.", "Pehle thoda waqt aur jagah dein, phir bina ilzaam lagaye ek seedhi baat-cheet karke hi faisla lein."))
        if intent in ("caution", "trouble", "advice"):
            body.append((T("What is straining things: ", "Kya khinchav la raha hai: ") + " ".join(obs[:3])) if obs else T("Nothing serious is straining this area in your chart.", "Aapke chart mein is kshetra par koi gambhir khinchav nahi dikhta."))
            if mg and mg[0] == "-" and mg[1].plain and mg[1].plain not in obs[:3]:
                body.append(mg[1].plain)
            if sheet.strength("Venus") == "weak":
                body.append(T("Venus, the planet of love, is under pressure, so affection may need deliberate expression.", "Prem ka graha Shukra dabaav mein hai, isliye pyaar jaan-boojhkar vyakt karna padega."))
            if intent == "trouble":
                if ss_item:
                    body.append(ss_item[0][1].plain)
                    sn = _sade_sati_note(sheet, ephem)
                    if sn:
                        body.append(sn)
                dd = sheet.dasha()
                if dd:
                    hard = [x for x in (dd["maha"], dd["antar"]) if any(h in R.DUSTHANA for h in sheet.rules(x)) or sheet.house_of(x) in R.DUSTHANA]
                    body.append(_dasha_plain(sheet, houses, karakas) + (T(" Phases like this can make friction feel heavier.", " Aise daur mein ghisaav bhaari lagta hai.") if hard else ""))
                else:
                    body.append(T("Without your exact birth time I read the current phase from how Saturn and Jupiter are moving over your Moon sign, so the dates here come from that, not from your life-phase (dasha) calendar.",
                                  "Exact janm samay ke bina main abhi ka daur Shani aur Guru ki Chandra rashi par chaal se padhta hoon, isliye yahan ki tarikhein usi se hain, dasha calendar se nahi."))
            advice += _advice_for(sheet, advice_planets)
            advice.append(T("Make a habit of one honest conversation a week, listen first, and avoid deciding big things during an argument.", "Hafte mein ek seedhi baat-cheet ki aadat daalein, pehle sunein, aur behes ke dauran bade faisle na lein."))
    if topic == "health":
        if intent == "vitality":
            body.append(T("Your physical vitality draws on the Sun ({s}) and your mental calm draws on the Moon ({m}).",
                          "Aapki sharirik urja Surya ({s}) par aur man ki shanti Chandra ({m}) par tikti hai.",
                          s=sheet.sw("Sun"), m=sheet.sw("Moon")))
            body += [helps and T("What supports your energy: {x}", "Aapki urja ko kya sahara deta hai: {x}", x=helps), lm]
        if intent == "routine":
            body.append(T("Your chart responds best to steady daily habits: fixed meal hours, consistent sleep, and light daily movement keep your energy balanced.",
                          "Aapka chart niyamit dincharya ko sabse achha jawab deta hai: tay samay par bhojan, poori neend aur roz thoda vyayam aapki urja ko santulit rakhte hain."))
            if cares:
                body.append(T("What to pace carefully: {x}", "Kis baat mein santulan rakhein: {x}", x=cares))
            advice.append(T("Keep a consistent wake-up and sleep time even on busy days, and take short breaks before fatigue builds up.", "Vyast dinon mein bhi uthne aur sone ka samay ek rakhein, aur thakan badhne se pehle chhota vishram lein."))
        if intent in ("caution", "trouble", "advice"):
            body.append((T("What drains your energy: ", "Kya aapki urja ko kam karta hai: ") + " ".join(obs[:3])) if obs else T("No heavy drain shows in your general wellbeing pattern.", "Aapke samanya urja chitra mein koi bhaari khinchav nahi dikhta."))
            if ss_item:
                body.append(ss_item[0][1].plain)
            advice += _advice_for(sheet, advice_planets)
            advice.append(T("Prioritise regular sleep, hydration and a calm morning routine; this reading covers general wellbeing tendencies, not medical care.",
                            "Niyamit neend, paani aur shaant subah ki dincharya ko prathamikta dein; yeh samanya urja ke rujhaan hain, medical salah nahi."))
    if topic == "career":
        l10 = sheet.lord(10)
        dom = [x for x in [l10] + sheet.occupants(10) + list(karakas) if x in sheet.pl]
        dom = list(dict.fromkeys(sorted(dom, key=lambda p: {"strong": 0, "ok": 1, "weak": 2}[sheet.strength(p)])))[:3]
        if intent == "switch":
            unstable = sheet.house_of(l10) in R.DUSTHANA
            movable = sheet.sign_of(l10) in R.MOVABLE
            body.append(T("Your chart shows a changeable career pattern, so a move comes naturally to you, but time it for a supportive stretch rather than reacting to a bad week.", "Aapka chart badalta hua career pattern dikhata hai, isliye badlaav aapke liye swabhavik hai, par bure hafte mein react karne ki jagah sahayak daur mein karein.")
                        if (unstable or movable) else
                        T("Your career pattern is steady, so staying and growing where you are is the stronger route unless the work itself no longer fits you.", "Aapka career pattern sthir hai, isliye jahan hain wahin badhna zyada majboot raasta hai, jab tak kaam aap par fit na rahe."))
            sat = sheet.transit_house("Saturn")
            if sat and (sat == 10 or 10 in [(sat + n - 2) % 12 + 1 for n in (3, 7, 10)]):
                body.append(T("Saturn is currently pressing on your career area: a period of heavy workload and testing. Changing in the middle of it works only with a firm offer in hand.", "Shani abhi aapke career ke kshetra par dabaav daal raha hai: kaam ka bojh aur pareeksha ka daur. Beech mein badalna tabhi theek hai jab pakka offer haath mein ho."))
            body += wins_block(T("Stretches to watch for a move or a new offer:", "Badlaav ya naye offer ke liye dekhne wale daur:"))
            advice.append(T("Apply while you are still employed, and let the offer, not the frustration, decide.", "Job mein rehte hue apply karein, aur frustration nahi balki offer faisla kare."))
        if intent == "business":
            b = sheet.strength(sheet.lord(7)) != "weak" and sheet.house_of(sheet.lord(7)) not in R.DUSTHANA and sheet.strength("Mercury") != "weak"
            body.append(T("Your chart can support running your own business, ideally started in a supportive stretch with some savings behind you.", "Aapka chart apna business chalane ka saath de sakta hai, behtar hai ki sahayak daur mein kuch bachat ke saath shuru karein.") if b else
                        T("A steady job gives you the stronger base; a small business can run alongside it until it proves itself.", "Pakki job aapko majboot aadhaar deti hai; chhota business saath mein tab tak chal sakta hai jab tak woh apne aap ko sabit na kare."))
            body.append(T("The main reason: " + (cares or "no major obstacle shows").rstrip(".") + ".", "Mukhya kaaran: " + (cares or "koi bada rukavat dikhti nahi").rstrip(".") + ".") if not b else "")
        if intent in ("field", "overview") and dom:
            fields = "; ".join(PLANET_FIELDS[p][0 if L == "en" else 1] for p in dom)
            body.append(T("Fields that fit your chart: {f}.", "Aapke chart se mel khaati fields: {f}.", f=fields))
            fn = _field_note(sheet, question, dom)
            if fn:
                body.append(fn)
        if intent == "govt":
            body.append(T("For government work, authority and discipline count most. The Sun, the planet of authority, is {s} in your chart, and your career area reads {v}.", "Sarkari kaam mein adhikaar aur anushasan sabse zaroori hain. Adhikaar ka graha Surya aapke chart mein {s} hai, aur aapka career kshetra {v} hai.", s=sheet.sw("Sun"), v=_verdict_word(sheet, label)))
        if intent == "growth":
            body.append(T("Growth depends on your position and your gains: ", "Tarakki aapke pad aur laabh par tikti hai: ") + (helps or T("the supports are limited, so steady skill-building matters most.", "sahayak kam hain, isliye lagataar skill banana sabse zaroori hai.")))
            body += wins_block(T("Likely growth stretches:", "Tarakki ke sambhavit daur:"))
    if topic == "wealth":
        if intent == "debt":
            heavy = sheet.house_of(sheet.lord(12)) in (2, 11) or label == "demanding"
            body.append(T("Spending pressure is visible in your chart, so a repayment plan matters more than waiting for luck.", "Aapke chart mein kharch ka dabaav dikhta hai, isliye kismat ka intezaar karne se repayment plan zyada zaroori hai.") if heavy else
                        T("Nothing in your chart forces heavy debt; manage it with a scheduled repayment and it should stay under control.", "Aapke chart mein bhaari karz ka koi majboor karne wala sanket nahi; tay kisht se sambhalein, kaabu mein rahega."))
        if intent in ("income", "savings", "advice"):
            body += [helps and T("What helps: {x}", "Kya madad karta hai: {x}", x=helps), cares and T("What to watch: {x}", "Kis par nazar: {x}", x=cares), lm]
        if intent == "savings":
            body.append(T("Saving is helped by a fixed amount set aside on payday, before spending begins.", "Bachat tab behtar hoti hai jab salary ke din hi ek tay rakam alag kar di jaaye."))
        if intent == "income":
            body.append(T("Your chart points to skills and contacts, more than luck, as the way to earn more.", "Aapka chart zyada kamaane ke liye kismat se zyada skills aur contacts ki taraf ishaara karta hai."))
    if topic == "education":
        if intent == "exam":
            mw = sheet.strength("Mercury")
            body.append(T("Your learning ability is {a}, and Mercury, the planet of exams and communication, is {b} in your chart" + (", so steady revision and practice papers matter a lot." if mw == "weak" else "."),
                          "Aapki seekhne ki kshamta {a} hai, aur pariksha aur samvad ka graha Budh aapke chart mein {b} hai" + (", isliye lagataar revision aur practice papers bahut zaroori hain." if mw == "weak" else "."), a=sheet.sw(sheet.lord(5)), b=sheet.sw("Mercury")))
            body += wins_block(T("Supportive stretches:", "Sahayak daur:"))
        if intent == "focus":
            body.append(T("Concentration depends on a calm mind (the Moon) and Mercury. Your Moon is {m} and Mercury is {b}.", "Ekagrata shaant man (Chandra) aur Budh par tikti hai. Aapka Chandra {m} hai aur Budh {b}.", m=sheet.sw("Moon"), b=sheet.sw("Mercury")))
            advice.append(T("Study in fixed short blocks at the same hour daily and keep the phone away; routine suits this pattern best.", "Roz ek hi samay par chhote fixed block mein padhein aur phone door rakhein; is pattern ko routine sabse behtar suit karta hai."))
        if intent == "abroad":
            link = [x for x in (sheet.house_of(sheet.lord(9)), sheet.house_of(sheet.lord(12)), sheet.house_of("Rahu")) if x in (9, 12, 3)]
            body.append(T("Your chart shows links with distant places, so studying or settling abroad is a real possibility.", "Aapka chart door ki jagahon se jod dikhata hai, isliye videsh mein padhna ya basna ek asli sambhavna hai.") if link else
                        T("Links with distant places are not strongly shown, so going abroad would take deliberate effort and planning.", "Door ki jagahon se jod zyada majboot nahi dikhta, isliye videsh jaane ke liye soch-samajhkar prayas aur planning chahiye."))
        if intent in ("field", "overview"):
            dom = list(dict.fromkeys([x for x in [sheet.lord(5), "Mercury", "Jupiter"] if x in sheet.pl]))[:3]
            body.append(T("Subjects that fit the way your mind works: {f}.", "Jo vishay aapke sochne ke tareeke se mel khaate hain: {f}.", f="; ".join(PLANET_FIELDS[p][0 if L == "en" else 1] for p in dom)))
            fn = _field_note(sheet, question, dom)
            if fn:
                body.append(fn)
    if topic in ("children", "family", "property", "foreign", "health", "general") and intent in ("advice", "explain", "phase") and not body:
        body += [helps and T("What helps: {x}", "Kya madad karta hai: {x}", x=helps), cares and T("What needs care: {x}", "Kis baat mein dhyaan: {x}", x=cares), lm]
    if intent == "phase":
        dp = _dasha_plain(sheet, houses, karakas)
        if dp:
            body.append(dp)
        else:
            body.append(T("You asked which phase you are in. Your birth time is not exact, so I will not invent life-phase (dasha) dates. The reliable clock here is where Saturn and Jupiter are moving over your Moon sign:",
                          "Aapne poochha ki aap kaunse daur mein hain. Aapka janm samay exact nahi hai, isliye main dasha ki tarikhein andaaze se nahi banaunga. Yahan bharosemand ghadī yeh hai ki Shani aur Guru aapki Chandra rashi par kahan chal rahe hain:"))
            for p in ("Saturn", "Jupiter"):
                h = sheet.transit_house(p)
                span = _transit_until(sheet, p, ephem)
                if not h or not span:
                    continue
                sign, until = span
                area = sheet.subj(h)
                when = T("and it stays in that sign until about {u}", "aur woh is rashi mein lagbhag {u} tak rahega", u=timeline._mon(until, L)) if until else T("and it is still moving through that sign", "aur woh abhi bhi usi rashi mein chal raha hai")
                body.append(T(
                    "{P} is in {s}, your {h} counted from the Moon, {w}. In this chart that colours the area of {a}.",
                    "{P} {s} mein hai, Chandra se {h} par, {w}. Is chart mein yeh {a} ke kshetra ko rang deta hai.",
                    P=sheet.p(p), s=sheet.sg(sign), h=sheet.ho(h), w=when, a=area))
            sn = _sade_sati_note(sheet, ephem)
            if sn:
                body.append(sn)
        body += wins_block(T("Stretches that switch this area on:", "Is kshetra ko sakriya karne wale daur:"))
    if intent == "explain":
        why_lines = (sup[:3] and [T("What supports it: ", "Kya madad karta hai: ") + " ".join(sup[:3])] or []) + (obs[:2] and [T("What holds it back: ", "Kya rokta hai: ") + " ".join(obs[:2])] or [])
        body += why_lines + [T("The full step-by-step working is saved under 'Why this answer?' if you want to see it.", "Poora kramwar hisaab 'Why this answer?' ke neeche rakha hai agar aap dekhna chahein.")]
    if intent == "advice" and topic not in ("marriage", "love", "health"):
        advice += _advice_for(sheet, advice_planets)
    # Never send the same paragraph again about the same subject; keep only new material.
    if not repeat:
        body = [x for x in body if not _already_said(x, prev_text)]
        if not body and not advice and not status_note:
            head = ""
            body = [T("I have already given you the overall picture for {t}, so I will not repeat it. Tell me the specific decision in front of you and I will read your chart against that.",
                      "Maine {t} ka samanya chitra pehle de diya hai, isliye dohraunga nahi. Aapke saamne jo thos faisla hai woh bataiye, main aapke chart ko usi se milakar padhunga.", t=tl)]
    if repeat:
        recap = T("As I showed a moment ago, your chart reads {v} here" + (": " + helps.rstrip(".") if helps else "") + (". On the other side: " + cares.rstrip(".") if cares else "") + ".",
                  "Jaisa maine abhi dikhaya, yahan aapka chart {v} hai" + (": " + helps.rstrip(".") if helps else "") + (". Doosri taraf: " + cares.rstrip(".") if cares else "") + ".", v=_verdict_word(sheet, label))
        if intent in ("when", "delay"):
            sharpen = (T("The stretches above stand. To narrow them further I would look at your finer life-phase (sub-period) calendar, and for that I need your exact birth time (add it in your profile).",
                         "Upar ke daur wahi rahenge. Inhe aur sankuchit karne ke liye main aapka baareek dasha calendar dekhta, jiske liye exact janm samay chahiye (profile mein jodein).")
                       if not sheet.dasha() else T("The stretches above stand; your finer life-phase calendar is what narrows them.", "Upar ke daur wahi rahenge; aapka baareek dasha calendar unhe sankuchit karta hai."))
        else:
            sharpen = T("The picture has not changed, so I will not repeat it. Ask me about another side of it below, or tell me what is happening and I will read your chart against it.",
                        "Chitra badla nahi hai, isliye dohrata nahi. Neeche se koi aur pehlu poochhein, ya bataiye kya ho raha hai, main aapke chart ko usse milakar padhunga.")
        body = [recap, sharpen]
        advice = []
        head = ""
    advice = [x for x in advice if x]
    body = [x for x in body if x]
    pieces = ([status_note] if status_note else []) + ([head] if head else []) + body + ([T("What you can do: ", "Aap kya kar sakte hain: ") + "; ".join(x.rstrip(".")[:1].lower() + x.rstrip(".")[1:] for x in advice) + "."] if advice else [])
    text = "\n\n".join(pieces)
    # ---------------- 4. follow-ups that move the conversation forward
    asked = {detect_intent(m.get("text", ""), topic) for m in history if m.get("role") == "user"}
    asked.add(intent)
    chips: List[str] = []
    q_text = ""
    first_time = not any(m.get("topic") == topic for m in history if m.get("role") == "bot")
    stat_key = "rel" if topic in ("marriage", "love") else "work" if topic == "career" else None
    if first_time and stat_key and not slots.get(stat_key) and topic in STATUS_CHIPS:
        q_text = sheet.t("To fine-tune this, tell me where you are right now.", "Ise aur sateek karne ke liye bataiye ki aap abhi kahan hain.")
        chips += [(en if L == "en" else hg) for _k, en, hg in STATUS_CHIPS[topic]][:3]
    for key, en, hg in FOLLOW.get(topic, []):
        if key not in asked and len(chips) < 5:
            chips.append(en if L == "en" else hg)
    if not chips:
        chips = [sheet.t("Tell me about my career", "Mere career ke baare mein batayein"), sheet.t("Tell me about money", "Paise ke baare mein batayein")]
    return {"text": text, "calc": calc, "timing": timing, "quick_replies": chips[:5], "question": q_text, "intent": intent, "topic": topic,
            "verdict": label, "slots": slots, "supports": plus, "obstacles": minus}
