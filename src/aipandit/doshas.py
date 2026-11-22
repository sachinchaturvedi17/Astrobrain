"""Computed dosha checks (v1.1.1). Pure functions over the chart dict; no astronomy here.

Only what the chart actually supports is claimed:
  * Manglik: Mars in house 1, 2, 4, 7, 8 or 12 counted from the Lagna and/or the Moon (the widely used rule).
    Softened when Mars is in its own or exalted sign. Never presented as a bar to marriage.
  * Kaal Sarp: all seven planets (Sun..Saturn) on one side of the Rahu-Ketu axis. The chart stores signs, not degrees,
    so a planet sharing a sign with Rahu or Ketu makes the result "borderline" instead of a confident yes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}
SOFT_SIGNS = {"Mesha", "Vrishchika", "Makara"}  # Mars in own or exalted sign
SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
LI = {"en": 0, "hg": 1, "hi": 2}


def manglik(chart: Dict[str, Any], from_lagna_ok: bool = True) -> Dict[str, Any]:
    mars = (chart.get("planets") or {}).get("Mars") or {}
    msign = mars.get("sign")
    if msign not in RASHIS:
        return {"status": "unknown", "bases": []}
    bases: List[str] = []
    if from_lagna_ok and mars.get("house") in MANGLIK_HOUSES:
        bases.append("lagna")
    moon = (chart.get("moon") or {}).get("sign")
    if moon in RASHIS and ((RASHIS.index(msign) - RASHIS.index(moon)) % 12 + 1) in MANGLIK_HOUSES:
        bases.append("moon")
    if not bases:
        return {"status": "absent", "bases": []}
    return {"status": "softened" if msign in SOFT_SIGNS else "present", "bases": bases, "house": mars.get("house")}


def kaal_sarp(chart: Dict[str, Any]) -> str:
    pl = chart.get("planets") or {}
    if "Rahu" not in pl or any(p not in pl for p in SEVEN):
        return "unknown"
    r = RASHIS.index(pl["Rahu"]["sign"])
    k = (r + 6) % 12
    offs = [(RASHIS.index(pl[p]["sign"]) - r) % 12 for p in SEVEN]
    shared = any(o in (0, 6) for o in offs)
    side_a = all(0 <= o <= 6 for o in offs)      # Rahu -> Ketu
    side_b = all(o == 0 or o >= 6 for o in offs)  # Ketu -> Rahu
    if not (side_a or side_b):
        return "absent"
    return "borderline" if shared else "formed"


TXT = {
    "manglik": {
        "present": ("In your chart Mars sits in a spot that traditional rules call Manglik. In plain words: Mars is a fiery, direct planet, so it asks for patience and calm communication in close relationships. It does not stop marriage, and many Manglik people have happy marriages.",
                    "Aapke chart mein Mangal aisi jagah hai jise parampara Manglik kehti hai. Seedhe shabdon mein: Mangal tez aur seedha graha hai, isliye rishton mein sabr aur shaant baat-cheet chahiye. Yeh shaadi ko rokta nahi, aur kai Manglik logon ki shaadi khushhaal hoti hai.",
                    "आपकी कुंडली में मंगल ऐसी जगह है जिसे परंपरा मांगलिक कहती है। सरल शब्दों में: मंगल तेज़ और सीधा ग्रह है, इसलिए रिश्तों में धैर्य और शांत बातचीत चाहिए। यह विवाह को रोकता नहीं, और कई मांगलिक लोगों का विवाह सुखी होता है।"),
        "softened": ("Mars is in a Manglik position in your chart, but it sits in its own or exalted sign, and traditional texts treat that as softening the effect. So this is a mild point, not a worry.",
                     "Aapke chart mein Mangal Manglik sthiti mein hai, lekin woh apni ya uchch rashi mein hai, aur parampara ise prabhav ko halka maanti hai. Yeh halki baat hai, chinta ki nahi.",
                     "आपकी कुंडली में मंगल मांगलिक स्थिति में है, पर वह अपनी या उच्च राशि में है, और परंपरा इसे प्रभाव को हल्का मानती है। यह हल्की बात है, चिंता की नहीं।"),
        "absent": ("Good news: by the usual rule you are not Manglik. Mars is not in the sensitive houses from your Lagna or Moon.",
                   "Achhi baat: aam niyam se aap Manglik nahi hain. Mangal aapke Lagna ya Chandra se sensitive bhavon mein nahi hai.",
                   "अच्छी बात: सामान्य नियम से आप मांगलिक नहीं हैं। मंगल आपके लग्न या चंद्र से संवेदनशील भावों में नहीं है।"),
        "unknown": ("I need your Mars position to check this, and I could not read it from the chart.", "Is jaanch ke liye Mangal ki sthiti chahiye, jo chart se nahi mil saki.", "इस जाँच के लिए मंगल की स्थिति चाहिए, जो कुंडली से नहीं मिल सकी।"),
        "tail": ("Two helpful facts: if both partners are Manglik it is traditionally considered balanced, and a Manglik can marry a non-Manglik. Fear sold around this is far bigger than the idea itself.",
                 "Do kaam ki baatein: dono Manglik hon toh parampara se santulan maana jata hai, aur Manglik aur non-Manglik ki shaadi ho sakti hai. Is par bechi jaane wali ghabrahat idea se kahin badi hai.",
                 "दो काम की बातें: दोनों मांगलिक हों तो परंपरा से संतुलित माना जाता है, और मांगलिक व अमांगलिक का विवाह हो सकता है। इस पर बेचा जाने वाला डर विचार से कहीं बड़ा है।"),
    },
    "kaalsarp": {
        "formed": ("In your chart the planets appear to sit on one side of the Rahu-Ketu axis, which is called Kaal Sarp. Think of it as a pattern of intense focus and some delays that ease with steady effort. Many very successful people have it, so please do not read it as a curse.",
                   "Aapke chart mein grah Rahu-Ketu ki ek taraf dikhte hain, jise Kaal Sarp kehte hain. Ise gehre focus aur kuch deri ka pattern samjhein jo lagatar mehnat se halka hota hai. Kai bahut safal logon mein yeh hota hai, isliye ise shraap na samjhein.",
                   "आपकी कुंडली में ग्रह राहु-केतु की एक ओर दिखते हैं, जिसे काल सर्प कहते हैं। इसे गहरे ध्यान और कुछ देरी का पैटर्न समझें जो लगातार मेहनत से हल्का होता है। कई बहुत सफल लोगों में यह होता है, इसलिए इसे श्राप न समझें।"),
        "borderline": ("Your chart is borderline for Kaal Sarp: one planet shares a sign with Rahu or Ketu, so only exact degrees can say yes or no, and most traditions would not call it a full Kaal Sarp. I would not worry about it.",
                       "Aapka chart Kaal Sarp ke kareeb hai: ek graha Rahu ya Ketu ki rashi mein hai, isliye sahi ansh hi haan ya na bata sakte hain, aur zyadatar parampara ise poora Kaal Sarp nahi kehti. Main chinta nahi karunga.",
                       "आपकी कुंडली काल सर्प के क़रीब है: एक ग्रह राहु या केतु की राशि में है, इसलिए सटीक अंश ही हाँ या ना बता सकते हैं, और अधिकतर परंपराएँ इसे पूर्ण काल सर्प नहीं कहतीं। मैं चिंता नहीं करूँगा।"),
        "absent": ("Your planets are on both sides of the Rahu-Ketu axis, so there is no Kaal Sarp pattern in your chart.",
                   "Aapke grah Rahu-Ketu ke dono taraf hain, isliye aapke chart mein Kaal Sarp pattern nahi hai.",
                   "आपके ग्रह राहु-केतु के दोनों ओर हैं, इसलिए आपकी कुंडली में काल सर्प पैटर्न नहीं है।"),
        "unknown": ("I could not read all the planets needed to check this.", "Iske liye zaroori sabhi grah chart se nahi mile.", "इसके लिए ज़रूरी सभी ग्रह कुंडली से नहीं मिले।"),
        "tail": ("This check uses signs only, so treat it as a guide. I will never tell you that you need an expensive puja for it.",
                 "Yeh jaanch sirf rashiyon par hai, isliye ise margdarshak samjhein. Main kabhi nahi kahunga ki iske liye mehengi puja chahiye.",
                 "यह जाँच केवल राशियों पर है, इसलिए इसे मार्गदर्शक समझें। मैं कभी नहीं कहूँगा कि इसके लिए महँगी पूजा चाहिए।"),
    },
}


def dosha_text(kind: str, chart: Dict[str, Any], lang: str, from_lagna_ok: bool = True) -> str:
    li = LI.get(lang, 0)
    status = manglik(chart, from_lagna_ok)["status"] if kind == "manglik" else kaal_sarp(chart)
    t = TXT[kind]
    parts = [t[status][li]]
    if status in ("present", "softened", "formed", "borderline"):
        parts.append(t["tail"][li])
    return " ".join(parts)
