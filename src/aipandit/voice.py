"""AstroMuni v1.1 voice: turns chart findings into a short, personal, plain-language conversation.

The engine (brain.py) still decides WHAT is true from the chart. This module only decides HOW it is said:
  - no house numbers or lords in the main answer (those stay in "Why this answer?"),
  - one idea at a time, then ONE follow-up question the person can tap or type,
  - the next message continues from that question (field, work status, relationship status, timing),
  - English, Hinglish (Roman Hindi) and Hindi; Hinglish/Hindi is detected from how the person writes.

Honesty rules kept from v1.0: only statements derived from the chart or engine-computed dasha dates, tendencies
not certainties, no invented lucky numbers/colours, no predictions of events.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

LI = {"en": 0, "hg": 1, "hi": 2}
RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
EXALT = {"Sun": "Mesha", "Moon": "Vrishabha", "Mars": "Makara", "Mercury": "Kanya", "Jupiter": "Karka", "Venus": "Meena", "Saturn": "Tula"}
DEBIL = {"Sun": "Tula", "Moon": "Vrishchika", "Mars": "Karka", "Mercury": "Meena", "Jupiter": "Makara", "Venus": "Kanya", "Saturn": "Mesha"}
OWN = {"Sun": ("Simha",), "Moon": ("Karka",), "Mars": ("Mesha", "Vrishchika"), "Mercury": ("Mithuna", "Kanya"), "Jupiter": ("Dhanu", "Meena"),
       "Venus": ("Vrishabha", "Tula"), "Saturn": ("Makara", "Kumbha")}
PL = {"hg": {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"},
      "hi": {"Sun": "सूर्य", "Moon": "चंद्रमा", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}}
MONTHS = {"en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
          "hi": ("जन॰", "फ़र॰", "मार्च", "अप्रैल", "मई", "जून", "जुला॰", "अग॰", "सित॰", "अक्टू॰", "नव॰", "दिस॰")}

# ------------------------------------------------------------------------------------------ language
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_HINGLISH = re.compile(
    r"\b(kya|kaisa|kaisi|kaise|kesa|hoga|hogi|hai|hain|hoon|mera|meri|mere|mujhe|mujhko|aap|apna|apni|nahi|nahin|nhi|kab|kyun|kyu|"
    r"padhai|naukri|shaadi|shadi|paisa|paise|sehat|ghar|rishta|bhai|yaar|batao|bataiye|bolo|chahiye|karna|karni|lagta|achha|accha|theek|"
    r"haan|han|abhi|aaj|kal|samay|dasha|kundli|janam|mein|mai|main|ka|ki|ke|se|toh|bhi)\b", re.I)


def detect_lang(question: str, chosen: str = "en") -> str:
    """Reply in the language the person actually writes in; fall back to their chosen language."""
    chosen = chosen if chosen in LI else "en"
    if _DEVANAGARI.search(question):
        return "hi"
    words = re.findall(r"[a-z]+", question.lower())
    hits = len(_HINGLISH.findall(question))
    if chosen == "en":
        starters = {"kya", "kab", "kaisa", "kaise", "mera", "meri", "mujhe", "naukri", "padhai", "shaadi", "paisa", "sehat"}
        if hits >= 2 or (hits >= 1 and len(words) <= 3 and words and words[0] in starters):
            return "hg"
    return chosen


def _p(lang: str, *t: str) -> str:
    return t[LI.get(lang, 0)]


def _pl(planet: str, lang: str) -> str:
    return PL.get(lang, {}).get(planet, planet)


def _date(d: Optional[str], lang: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})", d or "")
    if not m:
        return ""
    names = MONTHS["hi" if lang == "hi" else "en"]
    return f"{names[int(m.group(2)) - 1]} {m.group(1)}"


# ------------------------------------------------------------------------------------------ chart helpers
def status(chart: Dict[str, Any], planet: str) -> str:
    """strong | weak | ok, from sign dignity and house only (no invented scores)."""
    v = (chart.get("planets") or {}).get(planet)
    if not v or v.get("sign") not in RASHIS:
        return "ok"
    sign, house = v["sign"], v.get("house")
    if EXALT.get(planet) == sign or sign in OWN.get(planet, ()):
        return "strong"
    if DEBIL.get(planet) == sign:
        return "weak"
    if planet not in ("Rahu", "Ketu") and house in (6, 8, 12):
        return "weak"
    return "ok"


DOMAIN = {
    "Sun": ("confidence and authority", "confidence aur authority", "आत्मविश्वास और अधिकार"),
    "Moon": ("mind and emotions", "mann aur emotions", "मन और भावनाएँ"),
    "Mars": ("drive and courage", "josh aur himmat", "ऊर्जा और साहस"),
    "Mercury": ("learning and communication", "seekhne aur baat karne ki kala", "सीखने और संवाद"),
    "Jupiter": ("wisdom, growth and good fortune", "samajh, tarakki aur bhagya", "ज्ञान, उन्नति और भाग्य"),
    "Venus": ("love, comfort and creativity", "pyaar, sukh aur creativity", "प्रेम, सुख और रचनात्मकता"),
    "Saturn": ("discipline and hard work", "anushasan aur mehnat", "अनुशासन और परिश्रम"),
    "Rahu": ("ambition and unusual paths", "mahatvakanksha aur alag raste", "महत्वाकांक्षा और अलग रास्ते"),
    "Ketu": ("detachment and intuition", "vairagya aur intuition", "वैराग्य और अंतर्ज्ञान"),
}
DASHA_THEME = {
    "Sun": ("confidence, recognition and taking responsibility", "confidence, pehchaan aur zimmedari lene", "आत्मविश्वास, पहचान और ज़िम्मेदारी"),
    "Moon": ("emotions, home and the people close to you", "emotions, ghar aur apno", "भावनाएँ, घर और अपने लोग"),
    "Mars": ("energy, action and a bit of restlessness", "energy, action aur thodi bechaini", "ऊर्जा, कर्म और थोड़ी बेचैनी"),
    "Mercury": ("learning, business and communication", "seekhne, business aur baatcheet", "सीखना, व्यापार और संवाद"),
    "Jupiter": ("growth, guidance and new opportunities", "tarakki, guidance aur naye mauke", "उन्नति, मार्गदर्शन और नए अवसर"),
    "Venus": ("relationships, comfort and creativity", "rishton, sukh aur creativity", "रिश्ते, सुख और रचनात्मकता"),
    "Saturn": ("hard work, discipline and slow but lasting progress", "mehnat, anushasan aur dheemi par tikau tarakki", "परिश्रम, अनुशासन और धीमी पर टिकाऊ प्रगति"),
    "Rahu": ("ambition, change and big desires", "mahatvakanksha, badlaav aur badi ichhayein", "महत्वाकांक्षा, बदलाव और बड़ी इच्छाएँ"),
    "Ketu": ("letting go, reflection and a spiritual pull", "chhodna, sochna aur adhyatmik jhukaav", "छोड़ना, चिंतन और आध्यात्मिक झुकाव"),
}


def dasha_line(chart: Dict[str, Any], lang: str) -> str:
    d = chart.get("dasha") or {}
    if not (d.get("maha") and d.get("antar")):
        return ""
    until = _date(d.get("antar_end"), lang)
    th = DASHA_THEME.get(d["antar"], DASHA_THEME["Jupiter"])[LI[lang]]
    a, m = _pl(d["maha"], lang), _pl(d["antar"], lang)
    return _p(lang,
              f"Right now you are in your {m} phase (within {a})" + (f", running till {until}" if until else "") + f". This phase is mostly about {th}.",
              f"Abhi aap {m} ke daur mein hain ({a} ke andar)" + (f", jo {until} tak chalega" if until else "") + f". Is daur ka mudda hai {th}.",
              f"अभी आप {m} के दौर में हैं ({a} के भीतर)" + (f", जो {until} तक चलेगा" if until else "") + f"। इस दौर का विषय है {th}।")


def karaka_line(topic: str, karakas: Tuple[str, ...], chart: Dict[str, Any], lang: str) -> str:
    strong = [p for p in karakas if status(chart, p) == "strong"]
    weak = [p for p in karakas if status(chart, p) == "weak"]
    out = []
    if strong:
        p = strong[0]
        d = DOMAIN[p][LI[lang]]
        out.append(_p(lang, f"A real strength: your {p}, the planet of {d}, is well placed.",
                      f"Aapki ek badi taakat: {_pl(p, lang)}, jo {d} ka graha hai, achhi sthiti mein hai.",
                      f"आपकी एक बड़ी ताक़त: {_pl(p, lang)}, जो {d} का ग्रह है, अच्छी स्थिति में है।"))
    if weak:
        p = weak[0]
        d = DOMAIN[p][LI[lang]]
        out.append(_p(lang, f"One thing to work on: {p}, the planet of {d}, is under some pressure, so that part needs deliberate effort.",
                      f"Ek cheez par kaam karna hoga: {_pl(p, lang)}, jo {d} ka graha hai, thoda dabaav mein hai, isliye us hisse mein jaan-boojhkar mehnat chahiye.",
                      f"एक चीज़ पर काम करना होगा: {_pl(p, lang)}, जो {d} का ग्रह है, थोड़े दबाव में है, इसलिए उस हिस्से में सोच-समझकर मेहनत चाहिए।"))
    return " ".join(out)


# ------------------------------------------------------------------------------------------ openers
OPEN: Dict[str, Dict[str, Tuple[str, str, str]]] = {
    "education": {
        "sup": ("Good news first: your chart is quite supportive for studies. You tend to learn well once something clicks, and focused effort should pay off.",
                "Pehle achhi baat: padhai ke liye aapka chart kaafi saath deta hai. Jab cheez samajh aa jaati hai tab aap achha seekhte hain, aur focus se ki gayi mehnat rang laati hai.",
                "पहले अच्छी बात: पढ़ाई के लिए आपकी कुंडली काफ़ी साथ देती है। जब बात समझ आ जाती है तब आप अच्छा सीखते हैं, और ध्यान से की गई मेहनत रंग लाती है।"),
        "mix": ("Studies show a mixed picture for you: some subjects come easily, others need extra effort and a steady routine.",
                "Padhai ke liye mila-jula chitra hai: kuch subjects aasaani se aate hain, kuch mein extra mehnat aur fixed routine chahiye.",
                "पढ़ाई के लिए मिला-जुला चित्र है: कुछ विषय आसानी से आते हैं, कुछ में अतिरिक्त मेहनत और तय दिनचर्या चाहिए।"),
        "dem": ("Studies may ask a bit more patience from you than from others. That does not mean you cannot do well; a fixed routine and the right guidance matter a lot for you.",
                "Padhai mein aapko auron se thoda zyada sabr rakhna pad sakta hai. Iska matlab yeh nahi ki aap achha nahi kar sakte; fixed routine aur sahi guidance aapke liye bahut maayne rakhte hain.",
                "पढ़ाई में आपको औरों से थोड़ा ज़्यादा धैर्य रखना पड़ सकता है। इसका मतलब यह नहीं कि आप अच्छा नहीं कर सकते; तय दिनचर्या और सही मार्गदर्शन आपके लिए बहुत मायने रखते हैं।")},
    "career": {
        "sup": ("Your chart is supportive for your career. You tend to grow steadily when you take responsibility and stay consistent.",
                "Aapka chart career ke liye saath deta hai. Jab aap zimmedari lete hain aur lage rehte hain, tab aap dheere-dheere achhi tarakki karte hain.",
                "आपकी कुंडली करियर के लिए साथ देती है। जब आप ज़िम्मेदारी लेते हैं और लगे रहते हैं, तब आप धीरे-धीरे अच्छी तरक्की करते हैं।"),
        "mix": ("Your career picture is mixed: there is real potential, but it comes with some ups and downs and asks you to choose your direction carefully.",
                "Career ki tasveer mili-juli hai: potential asli hai, par thode utaar-chadhaav ke saath, aur disha soch-samajhkar chunni hogi.",
                "करियर की तस्वीर मिली-जुली है: क्षमता असली है, पर कुछ उतार-चढ़ाव के साथ, और दिशा सोच-समझकर चुननी होगी।"),
        "dem": ("Your career may need more patience and effort than average, and results can come a little late. Late does not mean never; it means a steady, well-chosen path works better than quick jumps.",
                "Career mein aapko average se zyada sabr aur mehnat lag sakti hai, aur nateeje thoda der se aa sakte hain. Der ka matlab kabhi nahi nahi; tez chhalang ke bajaye soch-samajh kar chuna hua steady raasta behtar rehta hai.",
                "करियर में आपको औसत से ज़्यादा धैर्य और मेहनत लग सकती है, और नतीजे थोड़ी देर से आ सकते हैं। देर का मतलब कभी नहीं नहीं; तेज़ छलांग के बजाय सोच-समझकर चुना स्थिर रास्ता बेहतर रहता है।")},
    "wealth": {
        "sup": ("Money looks supportive in your chart. You tend to build wealth steadily, especially through your own effort and good contacts.",
                "Paise ke maamle mein aapka chart saath deta hai. Aap apni mehnat aur achhe contacts se dheere-dheere achha paisa bana sakte hain.",
                "पैसे के मामले में आपकी कुंडली साथ देती है। आप अपनी मेहनत और अच्छे संपर्कों से धीरे-धीरे अच्छा धन बना सकते हैं।"),
        "mix": ("Money is a mixed picture for you: income can come, but saving needs a plan, otherwise it slips away.",
                "Paise ka chitra mila-jula hai: income aa sakti hai, par saving ka plan chahiye, warna paisa nikal jaata hai.",
                "पैसे का चित्र मिला-जुला है: आय आ सकती है, पर बचत की योजना चाहिए, वरना पैसा निकल जाता है।"),
        "dem": ("Money may need extra care in your chart: slow and steady saving works better for you than risky shortcuts.",
                "Aapke chart mein paise par extra dhyaan chahiye: risky shortcut ke bajaye dheemi aur steady saving aapke liye behtar hai.",
                "आपकी कुंडली में पैसे पर अतिरिक्त ध्यान चाहिए: जोखिम भरे शॉर्टकट के बजाय धीमी और स्थिर बचत आपके लिए बेहतर है।")},
    "marriage": {
        "sup": ("Relationships look supportive in your chart. You tend to be loyal, and a partner can be a real source of strength for you.",
                "Rishton ke liye aapka chart saath deta hai. Aap wafadaar hote hain, aur ek saathi aapki asli taakat ban sakta hai.",
                "रिश्तों के लिए आपकी कुंडली साथ देती है। आप वफ़ादार होते हैं, और जीवनसाथी आपकी असली ताक़त बन सकता है।"),
        "mix": ("Relationships show a mixed picture: there is a lot of warmth, but you may need to work on patience and communication to keep things smooth.",
                "Rishton ka chitra mila-jula hai: pyaar bahut hai, par baat-cheet aur sabr par kaam karna padega taaki sab smooth rahe.",
                "रिश्तों का चित्र मिला-जुला है: प्यार बहुत है, पर बातचीत और धैर्य पर काम करना पड़ेगा ताकि सब सहज रहे।"),
        "dem": ("Relationships may ask for extra patience and honest communication from you. Take your time choosing and do not rush; that usually works out better for you.",
                "Rishton mein aapko extra sabr aur seedhi baat-cheet karni pad sakti hai. Chunne mein waqt lijiye, jaldbaazi mat kijiye; aapke liye aksar yahi behtar rehta hai.",
                "रिश्तों में आपको अतिरिक्त धैर्य और सीधी बातचीत करनी पड़ सकती है। चुनने में समय लें, जल्दबाज़ी न करें; आपके लिए अक्सर यही बेहतर रहता है।")},
    "children": {
        "sup": ("The family-and-children side of your chart looks supportive.", "Parivaar aur bachchon ke liye aapka chart saath deta hai.", "परिवार और बच्चों के लिए आपकी कुंडली साथ देती है।"),
        "mix": ("The children side of your chart is mixed: good support, but timing and patience matter.", "Bachchon ke liye chart mila-jula hai: saath hai, par samay aur sabr maayne rakhte hain.", "बच्चों के लिए कुंडली मिली-जुली है: साथ है, पर समय और धैर्य मायने रखते हैं।"),
        "dem": ("The children side of your chart asks for patience and timing. Please do not read it as a verdict; it is a tendency, not a promise or a warning.",
                "Bachchon ke liye chart sabr aur sahi samay maangta hai. Ise faisla mat samjhiye; yeh ek rujhaan hai, wada ya chetavni nahi.",
                "बच्चों के लिए कुंडली धैर्य और सही समय माँगती है। इसे फ़ैसला न समझें; यह एक रुझान है, वादा या चेतावनी नहीं।")},
    "health": {
        "sup": ("Your general energy and wellbeing look well supported in the chart.", "Aapki general energy aur sehat ke liye chart achha saath deta hai.", "आपकी सामान्य ऊर्जा और सेहत के लिए कुंडली अच्छा साथ देती है।"),
        "mix": ("Your energy is mixed: good stretches and tired stretches. Routine sleep and food will help you more than most.",
                "Aapki energy mili-juli rehti hai: kabhi achhi, kabhi thaki hui. Neend aur khaane ka routine aapko auron se zyada fayda dega.",
                "आपकी ऊर्जा मिली-जुली रहती है: कभी अच्छी, कभी थकी हुई। नींद और खाने की दिनचर्या आपको औरों से ज़्यादा फ़ायदा देगी।"),
        "dem": ("Your chart suggests you should guard your energy and not overdo things. This is general wellbeing, not a medical statement.",
                "Aapka chart kehta hai ki apni energy ka dhyaan rakhein aur zyada khichein nahi. Yeh general wellbeing hai, medical baat nahi.",
                "आपकी कुंडली कहती है कि अपनी ऊर्जा का ध्यान रखें और ज़्यादा खींचें नहीं। यह सामान्य सेहत की बात है, चिकित्सकीय नहीं।")},
    "family": {
        "sup": ("Home and family look like a source of support for you.", "Ghar aur parivaar aapke liye sahara dikhte hain.", "घर और परिवार आपके लिए सहारा दिखते हैं।"),
        "mix": ("Home and family are mixed: lots of love, with some moments that need patience.", "Ghar aur parivaar mila-jula hai: pyaar bahut, kuch pal sabr maangte hain.", "घर और परिवार मिला-जुला है: प्यार बहुत, कुछ पल धैर्य माँगते हैं।"),
        "dem": ("Home and family may ask more patience from you. Calm, clear conversations will help more than arguments.", "Ghar aur parivaar mein aapko zyada sabr chahiye ho sakta hai. Bahes se zyada shaant, saaf baat-cheet kaam aayegi.", "घर और परिवार में आपको ज़्यादा धैर्य चाहिए हो सकता है। बहस से ज़्यादा शांत, साफ़ बातचीत काम आएगी।")},
    "general": {
        "sup": ("Overall your chart gives you good support: a positive base to build on.", "Kul milakar aapka chart achha saath deta hai: aage badhne ke liye ek positive aadhaar.", "कुल मिलाकर आपकी कुंडली अच्छा साथ देती है: आगे बढ़ने के लिए एक सकारात्मक आधार।"),
        "mix": ("Overall your chart is a mix of strengths and lessons, which is normal and gives you real depth.", "Kul milakar aapke chart mein taakat aur seekh dono hain, jo normal hai aur aapko gehrai deta hai.", "कुल मिलाकर आपकी कुंडली में ताक़त और सीख दोनों हैं, जो सामान्य है और आपको गहराई देता है।"),
        "dem": ("Overall your chart asks for patience, and it rewards steady effort over time.", "Kul milakar aapka chart sabr maangta hai, aur lagatar mehnat ka phal samay ke saath deta hai.", "कुल मिलाकर आपकी कुंडली धैर्य माँगती है, और लगातार मेहनत का फल समय के साथ देती है।")},
}

# ------------------------------------------------------------------------------------------ follow-up questions
# Each option: key, regex that recognises a typed or tapped reply, label per language (the label must match the regex).
ASK: Dict[str, Dict[str, Any]] = {
    "career_status": {
        "q": ("To guide you better: are you working right now, studying, or looking for a job?", "Aur achhe se batane ke liye: abhi aap job mein hain, padh rahe hain, ya job dhoondh rahe hain?", "और बेहतर बताने के लिए: अभी आप नौकरी में हैं, पढ़ रहे हैं, या नौकरी ढूँढ रहे हैं?"),
        "opts": [("working", r"work|job mein|naukri mein|employed|कर रहा|नौकरी में|working", ("I'm working", "Job mein hoon", "नौकरी में हूँ")),
                 ("student", r"student|study|studying|padh|college|पढ़|छात्र", ("I'm studying", "Student hoon", "मैं पढ़ रहा/रही हूँ")),
                 ("jobseeker", r"look|search|seeking|dhoond|talash|ढूँढ|खोज|तलाश|unemploy|jobless|no job", ("Looking for a job", "Job ki talash mein", "नौकरी की तलाश में")),
                 ("business", r"business|own|vyapar|startup|व्यवसाय|अपना", ("I run a business", "Apna business hai", "अपना व्यवसाय है"))]},
    "field": {
        "q": ("Which line are you in or aiming for? Tech, medical, business, creative, government job...?", "Kis line mein ho ya jaana chahte ho? Tech, medical, business, creative, sarkari naukri...?", "आप किस क्षेत्र में हैं या जाना चाहते हैं? टेक, मेडिकल, बिज़नेस, क्रिएटिव, सरकारी नौकरी...?"),
        "opts": []},
    "rel_status": {
        "q": ("Where are you right now: single, in a relationship, or married?", "Abhi aap kahan hain: single, relationship mein, ya shaadi-shuda?", "अभी आप कहाँ हैं: अकेले, रिश्ते में, या विवाहित?"),
        "opts": [("trouble", r"problem|issue|trouble|fight|dikkat|tension|breakup|toot|दिक्कत|परेशान", ("Having issues", "Rishte mein dikkat hai", "रिश्ते में दिक्कत है")),
                 ("single", r"single|alone|akela|akeli|unmarried|अकेल|अविवाहित", ("Single", "Single hoon", "अकेला/अकेली")),
                 ("relationship", r"relationship|dating|in love|girlfriend|boyfriend|rishte mein|रिश्ते में|प्रेम में", ("In a relationship", "Relationship mein hoon", "रिश्ते में हूँ")),
                 ("married", r"married|shaadi.?shuda|husband|wife|spouse|shaadi ho|शादी हो|विवाहित", ("Married", "Shaadi ho chuki hai", "शादी हो चुकी है"))]},
    "money_goal": {
        "q": ("What is on your mind most: saving, earning more, or clearing debt?", "Sabse zyada kya soch rahe ho: saving, zyada kamaana, ya karz utaarna?", "सबसे ज़्यादा क्या सोच रहे हैं: बचत, ज़्यादा कमाना, या कर्ज़ उतारना?"),
        "opts": [("savings", r"sav|bachat|jod|बचत", ("Saving more", "Saving badhani hai", "बचत बढ़ानी है")),
                 ("income", r"earn|income|salary|kamaa|kamaan|आय|कमा", ("Earning more", "Zyada kamaana hai", "ज़्यादा कमाना है")),
                 ("debt", r"debt|loan|karz|karj|udhaar|कर्ज|उधार", ("Clearing debt", "Karz ki tension hai", "कर्ज़ की चिंता है"))]},
    "timing": {
        "q": ("Want me to tell you which phase you are in right now and how long it lasts?", "Kya main bataun ki abhi aap kaunse daur mein hain aur woh kab tak chalega?", "क्या मैं बताऊँ कि अभी आप किस दौर में हैं और वह कब तक चलेगा?"),
        "opts": [("yes", r"^(yes|yeah|yep|sure|ok|okay|please|haan|han|ha|haa|bilkul|zaroor|bataiye|batao|हाँ|हां|जी|ज़रूर|बताइए|बताओ)(?!\w)", ("Yes, tell me", "Haan, batao", "हाँ, बताइए")),
                 ("no", r"^((abhi |अभी )?(no|nope|nah|not now|nahi|nahin|nhi|na|नहीं|नही))(?!\w)", ("Not now", "Abhi nahi", "अभी नहीं"))]},
}
FIELDS: Dict[str, Tuple[str, Tuple[str, ...], Tuple[str, str, str]]] = {
    "tech": (r"tech|software|\bit\b|coding|engineer|computer|\bdata\b|\bai\b|develop|programm|इंजीनियर|टेक", ("Mercury", "Rahu", "Saturn"), ("Tech / engineering", "Tech / engineering", "टेक / इंजीनियरिंग")),
    "medical": (r"medic|doctor|mbbs|nurs|pharma|dental|मेडिकल|डॉक्टर", ("Sun", "Mars", "Jupiter"), ("Medical", "Medical", "मेडिकल")),
    "business": (r"business|startup|entrepren|shop|trade|vyapar|बिज़नेस|व्यापार|व्यवसाय", ("Mercury", "Venus", "Jupiter"), ("Business", "Business", "बिज़नेस")),
    "finance": (r"commerce|account|finance|bank|\bca\b|cfa|econom|कॉमर्स|बैंक", ("Mercury", "Jupiter", "Venus"), ("Commerce / finance", "Commerce / finance", "कॉमर्स / फ़ाइनेंस")),
    "teaching": (r"teach|professor|lecturer|research|academ|phd|shikshak|शिक्षक|अध्यापक|शिक्षण|शोध", ("Jupiter", "Mercury", "Moon"), ("Teaching / research", "Teaching / research", "शिक्षण / शोध")),
    "law": (r"\blaw\b|legal|lawyer|advoc|judge|vakil|वकील|क़ानून|कानून", ("Jupiter", "Saturn", "Mercury"), ("Law", "Law", "कानून")),
    "writing": (r"writ|journal|content|author|blog|lekhak|media|लेखक|लेखन|पत्रकार|मीडिया", ("Mercury", "Moon", "Jupiter"), ("Writing / media", "Writing / media", "लेखन / मीडिया")),
    "creative": (r"\bart|design|music|film|creative|fashion|acting|dance|photograph|कला|संगीत|क्रिएटिव", ("Venus", "Moon", "Mercury"), ("Creative / arts", "Creative / arts", "क्रिएटिव / कला")),
    "marketing": (r"market|sales|advertis|brand|communicat|मार्केटिंग|बिक्री", ("Mercury", "Venus", "Mars"), ("Marketing / sales", "Marketing / sales", "मार्केटिंग / सेल्स")),
    "govt": (r"govt|government|upsc|\bias\b|police|army|defen|civil serv|sarkari|\bssc\b|सरकारी|सेना|पुलिस", ("Sun", "Mars", "Saturn"), ("Government job", "Sarkari naukri", "सरकारी नौकरी")),
}
QUICK_FIELDS = ("tech", "medical", "business", "creative", "govt", "marketing")
ASK["field"]["opts"] = [(k, v[0], v[2]) for k, v in FIELDS.items()]
TOPIC_ASK = {"education": "field", "career": "career_status", "marriage": "rel_status", "wealth": "money_goal"}

REPLY: Dict[str, Dict[str, Tuple[str, str, str]]] = {
    "career_status": {
        "working": ("Good, then we are talking about growth, not a fresh start. Work on being visible for what you already do well.",
                    "Achha, toh baat naye shuruaat ki nahi, tarakki ki hai. Jo aap pehle se achha karte ho, usi mein apni pehchaan banane par dhyaan dein.",
                    "अच्छा, तो बात नई शुरुआत की नहीं, तरक्की की है। जो आप पहले से अच्छा करते हैं, उसी में अपनी पहचान बनाने पर ध्यान दें।"),
        "student": ("Then your biggest job right now is building skills; the career will follow what you build.",
                    "Toh abhi aapka sabse bada kaam skills banana hai; career wahi follow karega jo aap banaoge.",
                    "तो अभी आपका सबसे बड़ा काम कौशल बनाना है; करियर वही अपनाएगा जो आप बनाएँगे।"),
        "jobseeker": ("Job hunting can be tiring, so first: this is a phase and not a verdict on you. Steady applications beat big bursts.",
                      "Job dhoondhna thaka deta hai, isliye pehle yeh: yeh ek daur hai, aapke baare mein faisla nahi. Roz thodi application bade josh se behtar hai.",
                      "नौकरी ढूँढना थका देता है, इसलिए पहले यह: यह एक दौर है, आपके बारे में फ़ैसला नहीं। रोज़ थोड़े आवेदन बड़े जोश से बेहतर हैं।"),
        "business": ("A business needs patience and good people around you; your chart is clearest about timing, so let's look at that.",
                     "Business ko sabr aur achhe log chahiye; aapka chart samay ke baare mein sabse saaf hai, toh wahi dekhte hain.",
                     "व्यवसाय को धैर्य और अच्छे लोग चाहिए; आपकी कुंडली समय के बारे में सबसे साफ़ है, तो वही देखते हैं।")},
    "rel_status": {
        "single": ("Then the real question is usually when and with whom. Rather than a date, I can say what kind of partner suits you and what to be careful about.",
                   "Toh asli sawaal aksar yeh hota hai ki kab aur kiske saath. Tareekh ke bajaye main bata sakta hoon ki kaisa saathi aapko suit karega aur kis cheez se bachna hai.",
                   "तो असली सवाल अक्सर यह होता है कि कब और किसके साथ। तारीख़ की जगह मैं बता सकता हूँ कि कैसा साथी आपको सूट करेगा और किस बात से बचना है।"),
        "relationship": ("Nice. In a relationship, what matters most is how you two handle disagreements, and that is where your chart has something to say.",
                         "Achha. Relationship mein sabse zaroori hai ki aap dono matbhed kaise sambhalte ho, aur yahin aapka chart kuch kehta hai.",
                         "अच्छा। रिश्ते में सबसे ज़रूरी है कि आप दोनों मतभेद कैसे संभालते हैं, और यहीं आपकी कुंडली कुछ कहती है।"),
        "married": ("Marriage is a long journey, and the best use of the chart is understanding which phases need more care.",
                    "Shaadi ek lamba safar hai, aur chart ka sabse achha use yeh samajhna hai ki kaun se daur mein zyada dhyaan chahiye.",
                    "विवाह एक लंबा सफ़र है, और कुंडली का सबसे अच्छा उपयोग यह समझना है कि किस दौर में ज़्यादा ध्यान चाहिए।"),
        "trouble": ("I'm sorry things feel difficult. Chart tendencies cannot decide your relationship; honest conversation can. Let me show what phase you are in, since phases make things feel heavier or lighter.",
                    "Mujhe afsos hai ki sab mushkil lag raha hai. Chart ke rujhaan aapka rishta tay nahi karte; seedhi baat-cheet karti hai. Main dikhata hoon ki aap kaunse daur mein hain, kyunki daur cheezon ko bhaari ya halka bana dete hain.",
                    "मुझे अफ़सोस है कि सब मुश्किल लग रहा है। कुंडली के रुझान आपका रिश्ता तय नहीं करते; ईमानदार बातचीत करती है। मैं दिखाता हूँ कि आप किस दौर में हैं, क्योंकि दौर चीज़ों को भारी या हल्का बना देते हैं।")},
    "money_goal": {
        "savings": ("Saving is where your chart rewards routine: set an automatic amount on salary day so it never depends on mood.",
                    "Saving mein aapka chart routine ko inaam deta hai: salary wale din ek tay rakam apne aap alag ho jaaye, mood par na chhodein.",
                    "बचत में आपकी कुंडली दिनचर्या को इनाम देती है: वेतन के दिन एक तय रकम अपने आप अलग हो जाए, मूड पर न छोड़ें।"),
        "income": ("To earn more, the chart points to skills and contacts over luck. Pick one skill to deepen this year.",
                   "Zyada kamaane ke liye chart kismat se zyada skills aur contacts ki taraf ishaara karta hai. Is saal ek skill gehri karein.",
                   "ज़्यादा कमाने के लिए कुंडली किस्मत से ज़्यादा कौशल और संपर्कों की ओर इशारा करती है। इस साल एक कौशल गहरा करें।"),
        "debt": ("Debt is stressful, so one calm step: list everything, clear the highest-interest one first. I will not predict windfalls; planning is more reliable.",
                 "Karz tension deta hai, isliye ek shaant kadam: sab likhein, sabse zyada byaaj wala pehle chukayein. Main achaanak paise ki prediction nahi karunga; planning zyada bharosemand hai.",
                 "कर्ज़ तनाव देता है, इसलिए एक शांत कदम: सब लिखें, सबसे ज़्यादा ब्याज वाला पहले चुकाएँ। मैं अचानक धन की भविष्यवाणी नहीं करूँगा; योजना ज़्यादा भरोसेमंद है।")},
}
FIELD_FIT = {
    "good": ("{f} looks like a natural fit: {pl} is well placed in your chart, and that planet is traditionally linked with this kind of work.",
             "{f} aapke liye natural fit lagta hai: {pl} aapke chart mein achhi sthiti mein hai, aur yeh graha parampara se is tarah ke kaam se jud hai.",
             "{f} आपके लिए स्वाभाविक मेल लगता है: {pl} आपकी कुंडली में अच्छी स्थिति में है, और यह ग्रह परंपरा से इस तरह के काम से जुड़ा है।"),
    "mix": ("{f} is workable for you. Some parts will come naturally and some need deliberate practice, so build those skills on purpose.",
            "{f} aapke liye possible hai. Kuch hissa aasaani se aayega, kuch mein jaan-boojhkar practice chahiye, isliye woh skills sochkar banayein.",
            "{f} आपके लिए संभव है। कुछ हिस्सा सहज आएगा, कुछ में सोच-समझकर अभ्यास चाहिए, इसलिए वे कौशल इरादे से बनाएँ।"),
    "stretch": ("{f} can still be done, but it will ask more effort from you than other lines. If you love it, go for it with a strong routine; if you are unsure, keep a second option open.",
                "{f} kiya ja sakta hai, par doosri lines se zyada mehnat maangega. Agar pasand hai toh pakke routine ke saath jaiye; agar pakka nahi hai toh doosra option khula rakhein.",
                "{f} किया जा सकता है, पर दूसरी लाइनों से ज़्यादा मेहनत माँगेगा। अगर पसंद है तो पक्की दिनचर्या के साथ जाइए; अगर पक्का नहीं तो दूसरा विकल्प खुला रखें।"),
}
FIELD_DASHA = ("Also, your current phase involves {pl}, so it is a good time to start moving in this direction.",
               "Saath hi, aapke abhi ke daur mein {pl} shamil hai, isliye is disha mein badhna shuru karne ka achha samay hai.",
               "साथ ही, आपके अभी के दौर में {pl} शामिल है, इसलिए इस दिशा में बढ़ना शुरू करने का अच्छा समय है।")
GREET = ("Namaste! I am AstroMuni. I read your chart and explain it in plain words. Ask me about your career, love, studies, money, or what phase of life you are in.",
         "Namaste! Main AstroMuni hoon. Main aapka chart padhkar saaf shabdon mein samjhata hoon. Career, pyaar, padhai, paisa, ya abhi aap kaunse daur mein ho, kuch bhi poochhiye.",
         "नमस्ते! मैं AstroMuni हूँ। मैं आपकी कुंडली पढ़कर सरल शब्दों में समझाता हूँ। करियर, प्रेम, पढ़ाई, पैसा, या अभी आप किस दौर में हैं, कुछ भी पूछिए।")
THANKS = ("You are welcome! Ask me anything else whenever you like.", "Aapka swagat hai! Jab chahein kuch aur poochhiye.", "आपका स्वागत है! जब चाहें कुछ और पूछिए।")
TOPIC_CHIPS = {"en": ["My career", "Love & marriage", "Studies", "Money", "My current phase"],
               "hg": ["Mera career", "Pyaar aur shaadi", "Padhai", "Paisa", "Meri abhi ki dasha"],
               "hi": ["मेरा करियर", "प्रेम और विवाह", "पढ़ाई", "पैसा", "मेरी अभी की दशा"]}
NO_FOLLOW = ("Fine, we can leave it there. Ask me about another area whenever you like.", "Theek hai, yahin rokte hain. Jab chahein kisi aur kshetra ke baare mein poochhiye.", "ठीक है, यहीं रोकते हैं। जब चाहें किसी और क्षेत्र के बारे में पूछिए।")
TIMING_TAIL = ("Phases change, and each sub-period has its own tone, so it helps to check again when this one ends.",
               "Daur badalte hain aur har sub-period ka apna mizaaj hota hai, isliye jab yeh khatam ho tab dobara dekhna achha rehta hai.",
               "दौर बदलते हैं और हर उप-दौर का अपना मिज़ाज होता है, इसलिए जब यह ख़त्म हो तब दोबारा देखना अच्छा रहता है।")


# ------------------------------------------------------------------------------------------ public API
def greeting(question: str, lang: str) -> Optional[Dict[str, Any]]:
    q = question.strip().lower()
    if re.match(r"^(hi+|hello+|hey+|namaste|namaskar|नमस्ते|हैलो|हाय|good (morning|evening|afternoon))\W*$", q):
        return {"text": _p(lang, *GREET), "expects": None, "question": "", "quick_replies": TOPIC_CHIPS[lang]}
    if re.match(r"^(thanks?|thank you|shukriya|dhanyavaad|dhanyawad|thx|धन्यवाद|शुक्रिया)\W*$", q):
        return {"text": _p(lang, *THANKS), "expects": None, "question": "", "quick_replies": TOPIC_CHIPS[lang]}
    return None


def ask_block(expects: Optional[str], lang: str) -> Tuple[str, List[str]]:
    if not expects or expects not in ASK:
        return "", []
    a = ASK[expects]
    if expects == "field":
        labels = [FIELDS[k][2][LI[lang]] for k in QUICK_FIELDS]
    else:
        labels = [o[2][LI[lang]] for o in a["opts"]]
        if expects == "rel_status":  # keep the sensitive option last in the chips
            labels = labels[1:] + labels[:1]
    return a["q"][LI[lang]], labels


def parse_reply(expects: str, text: str) -> Optional[str]:
    """Recognise a typed or tapped answer to the last follow-up question. Returns an option key or None."""
    if expects not in ASK:
        return None
    t = text.strip().lower()
    if len(t.split()) > 8:
        return None
    if expects == "field":
        for k, (pat, _pls, _lab) in FIELDS.items():
            if re.search(pat, t, re.I):
                return k
        return None
    for opt in ASK[expects]["opts"]:
        if re.search(opt[1], t, re.I):
            return opt[0]
    return None


def last_context(history: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    for m in reversed(history or []):
        if isinstance(m, dict) and m.get("role") in ("bot", "assistant", "ai"):
            return {"topic": m.get("topic"), "expects": m.get("expects")}
    return {}


def compose(topic: str, total: int, karakas: Tuple[str, ...], chart: Dict[str, Any], lang: str) -> Dict[str, Any]:
    tone = "sup" if total >= 3 else "mix" if total >= 0 else "dem"
    parts = [_p(lang, *OPEN[topic][tone]), karaka_line(topic, karakas, chart, lang)]
    expects = TOPIC_ASK.get(topic, "timing")
    q, quick = ask_block(expects, lang)
    return {"text": " ".join(x for x in parts if x), "expects": expects, "question": q, "quick_replies": quick}


def dasha_answer(chart: Dict[str, Any], lang: str) -> Dict[str, Any]:
    line = dasha_line(chart, lang)
    return {"text": line, "expects": None, "question": _p(lang, "Which area should I connect it with?", "Ise kis kshetra se jodkar bataun?", "इसे किस क्षेत्र से जोड़कर बताऊँ?"),
            "quick_replies": TOPIC_CHIPS[lang][:4]}


def continue_chat(expects: str, key: str, topic: str, chart: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """The person answered our follow-up question; carry on from it."""
    li = LI[lang]
    if expects == "field":
        label, planets = FIELDS[key][2][li], FIELDS[key][1]
        st = [status(chart, p) for p in planets]
        strong = [p for p, s in zip(planets, st) if s == "strong"]
        weak = st.count("weak")
        fit = "good" if strong and weak == 0 else "stretch" if weak > len(strong) else "mix"
        text = FIELD_FIT[fit][li].format(f=label, pl=_pl(strong[0], lang) if strong else "")
        d = chart.get("dasha") or {}
        hit = [p for p in (d.get("maha"), d.get("antar")) if p in planets]
        if hit:
            text += " " + FIELD_DASHA[li].format(pl=_pl(hit[0], lang))
        nxt = "timing"
    elif expects == "timing":
        if key == "no":
            return {"text": NO_FOLLOW[li], "expects": None, "question": "", "quick_replies": TOPIC_CHIPS[lang]}
        text = (dasha_line(chart, lang) + " " + TIMING_TAIL[li]).strip()
        return {"text": text, "expects": None, "question": "", "quick_replies": TOPIC_CHIPS[lang]}
    else:
        text = REPLY[expects][key][li]
        nxt = "field" if expects == "career_status" and key != "business" else "timing"
    q, quick = ask_block(nxt, lang)
    return {"text": text, "expects": nxt, "question": q, "quick_replies": quick}
