"""Computed yoga check (v1.1.2). Pure functions over the chart dict; no astronomy here.

Only sign-level rules the chart can support are used, and each is worded as a tendency, never a promise:
  * Gajakesari: Jupiter in a kendra (1, 4, 7, 10) counted from the Moon.
  * Budhaditya: Sun and Mercury in the same sign.
  * Chandra-Mangal: Moon and Mars in the same sign.
  * Pancha Mahapurusha: Mars, Mercury, Jupiter, Venus or Saturn in its own/exalted sign AND in a kendra from the Lagna
    (needs a reliable Lagna, so it is skipped when only the Moon chart is available).
  * Guru Chandal: Jupiter and Rahu in the same sign (a caution, worded gently).
  * Raja yoga (v1.1.3): the lord of a kendra house and the lord of a trikona house are linked by sharing a sign, facing each
    other (opposite signs) or exchanging signs; one planet ruling both is a yogakaraka; 9th and 10th lords linked is
    Dharma-Karmadhipati. Needs a reliable Lagna. Planets only (Rahu/Ketu are not house lords here).
  * Neecha Bhanga: a debilitated planet whose weakness is cancelled because the lord of its debilitation sign or of its
    exaltation sign stands in a kendra from the Lagna or the Moon.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .ashtakoota import LORD as SIGN_LORD

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
LI = {"en": 0, "hg": 1, "hi": 2}
PN = {"Sun": ("Sun", "Surya", "सूर्य"), "Moon": ("Moon", "Chandra", "चंद्र"), "Mars": ("Mars", "Mangal", "मंगल"), "Mercury": ("Mercury", "Budh", "बुध"),
      "Jupiter": ("Jupiter", "Guru", "गुरु"), "Venus": ("Venus", "Shukra", "शुक्र"), "Saturn": ("Saturn", "Shani", "शनि")}
DEBIL = {"Sun": "Tula", "Moon": "Vrishchika", "Mars": "Karka", "Mercury": "Meena", "Jupiter": "Makara", "Venus": "Kanya", "Saturn": "Mesha"}
EXALT = {"Sun": "Mesha", "Moon": "Vrishabha", "Mars": "Makara", "Mercury": "Kanya", "Jupiter": "Karka", "Venus": "Meena", "Saturn": "Tula"}
KENDRA_OFFS = (0, 3, 6, 9)
MAHAPURUSHA = {  # planet: (yoga name, signs that count)
    "Mars": ("Ruchaka", ("Mesha", "Vrishchika", "Makara")),
    "Mercury": ("Bhadra", ("Mithuna", "Kanya")),
    "Jupiter": ("Hamsa", ("Dhanu", "Meena", "Karka")),
    "Venus": ("Malavya", ("Vrishabha", "Tula", "Meena")),
    "Saturn": ("Shasha", ("Makara", "Kumbha", "Tula")),
}
KENDRA_HOUSES = {1, 4, 7, 10}

TXT = {
    "gajakesari": ("Gajakesari yoga: Jupiter sits in a supportive spot from your Moon. Traditionally this points to good judgement, a respected name and help arriving when it is needed.",
                   "Gajakesari yoga: Guru aapke Chandra se madadgaar jagah par hai. Parampara ise achhi samajh, izzat aur zarurat par madad milne ka sanket maanti hai.",
                   "गजकेसरी योग: गुरु आपके चंद्र से सहयोगी स्थान पर है। परंपरा इसे अच्छी समझ, सम्मान और ज़रूरत पर मदद मिलने का संकेत मानती है।"),
    "budhaditya": ("Budhaditya yoga: your Sun and Mercury share a sign. It tends to give a sharp mind and a good way with words and numbers.",
                   "Budhaditya yoga: aapke Surya aur Budh ek hi rashi mein hain. Yeh tez dimaag aur shabdon aur ankon par pakad dene ki taraf jhukta hai.",
                   "बुधादित्य योग: आपके सूर्य और बुध एक ही राशि में हैं। यह तेज़ दिमाग़ और शब्दों व अंकों पर पकड़ की ओर झुकाव देता है।"),
    "chandramangal": ("Chandra-Mangal yoga: your Moon and Mars share a sign. It is linked with drive and a knack for earning, though moods can run hot, so rest matters.",
                      "Chandra-Mangal yoga: aapke Chandra aur Mangal ek hi rashi mein hain. Yeh josh aur kamane ki samajh se jodta hai, par mizaaj garam ho sakta hai, isliye aaram zaroori hai.",
                      "चंद्र-मंगल योग: आपके चंद्र और मंगल एक ही राशि में हैं। यह जोश और कमाने की समझ से जुड़ा है, पर मिज़ाज गरम हो सकता है, इसलिए आराम ज़रूरी है।"),
    "rajayoga": ("Raja yoga: {p1} and {p2} are linked in your chart ({how}). One rules a pillar house and the other a fortune house. Tradition reads this as a good base for status, responsibility and rising in life, most visibly in the periods of these planets.",
                 "Raja yoga: aapke chart mein {p1} aur {p2} jude hain ({how}). Ek mukhya bhav ka swami hai aur doosra bhagya bhav ka. Parampara ise maan-pratishtha, zimmedari aur aage badhne ka achha aadhaar maanti hai, in grahon ki dasha mein sabse zyada.",
                 "राज योग: आपकी कुंडली में {p1} और {p2} जुड़े हैं ({how})। एक मुख्य भाव का स्वामी है और दूसरा भाग्य भाव का। परंपरा इसे मान-प्रतिष्ठा, ज़िम्मेदारी और आगे बढ़ने का अच्छा आधार मानती है, इन ग्रहों की दशा में सबसे अधिक।"),
    "yogakaraka": ("Yogakaraka: {p1} rules both a pillar house and a fortune house for your Lagna, which tradition counts as one of the most helpful planets for you. Its own periods are often the ones where things move.",
                   "Yogakaraka: aapke lagna ke liye {p1} mukhya aur bhagya dono bhavon ka swami hai, jise parampara aapke liye sabse madadgaar grahon mein ginti hai. Iski apni dasha mein aksar kaam aage badhte hain.",
                   "योगकारक: आपके लग्न के लिए {p1} मुख्य और भाग्य दोनों भावों का स्वामी है, जिसे परंपरा आपके लिए सबसे सहायक ग्रहों में गिनती है। इसकी अपनी दशा में अक्सर काम आगे बढ़ते हैं।"),
    "dharmakarma": ("Dharma-Karmadhipati yoga: the planets of purpose ({p1}) and career ({p2}) are linked. It is read as work and values pulling in the same direction.",
                    "Dharma-Karmadhipati yoga: uddeshya ({p1}) aur career ({p2}) ke grah jude hain. Ise kaam aur values ka ek hi disha mein chalna samjha jata hai.",
                    "धर्म-कर्माधिपति योग: उद्देश्य ({p1}) और करियर ({p2}) के ग्रह जुड़े हैं। इसे काम और मूल्यों के एक ही दिशा में चलने के रूप में पढ़ा जाता है।"),
    "neechabhanga": ("Neecha Bhanga: your {p1} sits in a weak sign, but the usual cancellation rule applies, which turns the weakness into strength built through effort. Often a late bloomer pattern.",
                     "Neecha Bhanga: aapka {p1} kamzor rashi mein hai, par aam cancellation niyam laagu hota hai, jo kamzori ko mehnat se bani taqat bana deta hai. Aksar der se khilne wala pattern.",
                     "नीच भंग: आपका {p1} कमज़ोर राशि में है, पर सामान्य निरस्तीकरण नियम लागू होता है, जो कमज़ोरी को मेहनत से बनी ताक़त बना देता है। अक्सर देर से खिलने वाला पैटर्न।"),
    "mahapurusha": ("{name} yoga, one of the five Mahapurusha yogas: {planet} is strong in its own or exalted sign and stands in a pillar house of your chart. Tradition links it with standing out in that planet's area of life.",
                    "{name} yoga, paanch Mahapurusha yogon mein se ek: {planet} apni ya uchch rashi mein majboot hai aur aapke chart ke mukhya bhav mein hai. Parampara ise us graha ke kshetra mein alag pehchaan se jodti hai.",
                    "{name} योग, पाँच महापुरुष योगों में से एक: {planet} अपनी या उच्च राशि में मज़बूत है और आपकी कुंडली के मुख्य भाव में है। परंपरा इसे उस ग्रह के क्षेत्र में अलग पहचान से जोड़ती है।"),
    "gurucandal": ("Guru-Chandal pattern: Jupiter shares a sign with Rahu. It is read as a nudge to question borrowed beliefs and pick your teachers carefully, not as a curse.",
                   "Guru-Chandal pattern: Guru aur Rahu ek hi rashi mein hain. Ise udhaar ki maanyataon par sawaal karne aur guru soch-samajh kar chunne ka ishara samjhein, shraap nahi.",
                   "गुरु-चांडाल पैटर्न: गुरु और राहु एक ही राशि में हैं। इसे उधार की मान्यताओं पर सवाल करने और गुरु सोच-समझकर चुनने का इशारा समझें, श्राप नहीं।"),
}
NONE = ("I looked for the well-known yogas (Gajakesari, Budhaditya, Chandra-Mangal, Raja yoga, the five Mahapurusha yogas) and none show up in your chart by the usual sign-based rules. That says very little: yogas are one small part of a chart, and most good qualities in a life come from the whole picture.",
        "Maine jaane-maane yogon (Gajakesari, Budhaditya, Chandra-Mangal, paanch Mahapurusha) ko dekha, aur aam sign-based niyamon se aapke chart mein koi nahi dikha. Isse bahut kam farak padta hai: yog chart ka ek chhota hissa hain, aur zindagi ki achhaiyan poore chart se aati hain.",
        "मैंने जाने-माने योगों (गजकेसरी, बुधादित्य, चंद्र-मंगल, पाँच महापुरुष) को देखा, और सामान्य राशि-आधारित नियमों से आपकी कुंडली में कोई नहीं दिखा। इससे बहुत कम फ़र्क़ पड़ता है: योग कुंडली का एक छोटा हिस्सा हैं, और जीवन की अच्छाइयाँ पूरी कुंडली से आती हैं।")
HEAD = ("Here is what I can see in your chart:", "Aapke chart mein jo dikhta hai:", "आपकी कुंडली में जो दिखता है:")
TAIL = ("These are traditional tendencies, not promises. Effort and choices count for more than any yoga.",
        "Yeh paramparik jhukaav hain, vaade nahi. Kisi bhi yog se zyada mehnat aur faisle matter karte hain.",
        "ये पारंपरिक झुकाव हैं, वादे नहीं। किसी भी योग से ज़्यादा मेहनत और फ़ैसले मायने रखते हैं।")


def _idx(chart: Dict[str, Any], p: str):
    s = ((chart.get("planets") or {}).get(p) or {}).get("sign")
    return RASHIS.index(s) if s in RASHIS else None


def find_yogas(chart: Dict[str, Any], lagna_ok: bool = True) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    moon = _idx(chart, "Moon") if (chart.get("planets") or {}).get("Moon") else None
    if moon is None and (chart.get("moon") or {}).get("sign") in RASHIS:
        moon = RASHIS.index(chart["moon"]["sign"])
    jup, sun, mer, mars, rahu = (_idx(chart, p) for p in ("Jupiter", "Sun", "Mercury", "Mars", "Rahu"))
    if moon is not None and jup is not None and (jup - moon) % 12 in KENDRA_OFFS:
        out.append({"key": "gajakesari"})
    if sun is not None and sun == mer:
        out.append({"key": "budhaditya"})
    if moon is not None and moon == mars:
        out.append({"key": "chandramangal"})
    if lagna_ok:
        for planet, (name, signs) in MAHAPURUSHA.items():
            pl = (chart.get("planets") or {}).get(planet) or {}
            if pl.get("sign") in signs and pl.get("house") in KENDRA_HOUSES:
                out.append({"key": "mahapurusha", "name": name, "planet": planet})
    if jup is not None and jup == rahu:
        out.append({"key": "gurucandal"})
    if lagna_ok:
        out += raja_yogas(chart)
    out += neecha_bhanga(chart, lagna_ok)
    return out


def _sign_of(chart: Dict[str, Any], p: str) -> Optional[str]:
    s = ((chart.get("planets") or {}).get(p) or {}).get("sign")
    return s if s in RASHIS else None


def _linked(chart: Dict[str, Any], a: str, b: str) -> Optional[str]:
    """How two planets are linked at sign level: together, facing each other, or exchanging signs."""
    sa, sb = _sign_of(chart, a), _sign_of(chart, b)
    if not sa or not sb:
        return None
    if sa == sb:
        return "together"
    if (RASHIS.index(sa) - RASHIS.index(sb)) % 12 == 6:
        return "facing"
    if SIGN_LORD[RASHIS.index(sa)] == b and SIGN_LORD[RASHIS.index(sb)] == a:
        return "exchange"
    return None


HOW = {"together": ("in the same sign", "ek hi rashi mein", "एक ही राशि में"), "facing": ("facing each other", "ek doosre ke saamne", "एक-दूसरे के सामने"),
       "exchange": ("exchanging signs", "rashi badalkar", "राशि बदलकर")}


def raja_yogas(chart: Dict[str, Any]) -> List[Dict[str, str]]:
    """Kendra-trikona links, yogakaraka and Dharma-Karmadhipati. Requires a reliable Lagna (caller checks)."""
    lg = chart.get("lagna")
    if lg not in RASHIS:
        return []
    li = RASHIS.index(lg)
    lord = {h: SIGN_LORD[(li + h - 1) % 12] for h in range(1, 13)}
    real = set(PN)
    out: List[Dict[str, str]] = []
    kend = {lord[h] for h in (1, 4, 7, 10)} & real
    trik = {lord[h] for h in (1, 5, 9)} & real
    both = sorted(p for p in real if any(lord[h] == p for h in (4, 7, 10)) and any(lord[h] == p for h in (5, 9)))
    for p in both:
        out.append({"key": "yogakaraka", "p1": p})
    seen = set()
    for k in sorted(kend):
        for t in sorted(trik):
            if k == t or (k, t) in seen or (t, k) in seen:
                continue
            seen.add((k, t))
            how = _linked(chart, k, t)
            if how and sum(1 for y in out if y["key"] == "rajayoga") < 2:
                out.append({"key": "rajayoga", "p1": k, "p2": t, "how": how})
    l9, l10 = lord[9], lord[10]
    if l9 != l10 and l9 in real and l10 in real:
        how = _linked(chart, l9, l10)
        if how:
            out.append({"key": "dharmakarma", "p1": l9, "p2": l10, "how": how})
    return out


def neecha_bhanga(chart: Dict[str, Any], lagna_ok: bool = True) -> List[Dict[str, str]]:
    pl = chart.get("planets") or {}
    moon = (chart.get("moon") or {}).get("sign") or (pl.get("Moon") or {}).get("sign")
    refs = [x for x in (chart.get("lagna") if lagna_ok else None, moon) if x in RASHIS]
    out: List[Dict[str, str]] = []
    for p, deb in DEBIL.items():
        if _sign_of(chart, p) != deb:
            continue
        helpers = {SIGN_LORD[RASHIS.index(deb)], SIGN_LORD[RASHIS.index(EXALT[p])]} - {p}
        for h in sorted(helpers):
            hs = _sign_of(chart, h)
            use = [r for r in refs if not (h == "Moon" and r == moon)]   # the Moon is trivially in a kendra from itself
            if hs and any((RASHIS.index(hs) - RASHIS.index(r)) % 12 in KENDRA_OFFS for r in use):
                out.append({"key": "neechabhanga", "p1": p})
                break
    return out


def yoga_text(chart: Dict[str, Any], lang: str, lagna_ok: bool = True) -> str:
    li = LI.get(lang, 0)
    found = find_yogas(chart, lagna_ok)
    if not found:
        return NONE[li]
    lines = []
    for y in found[:6]:
        kw = {k: v for k, v in y.items() if k != "key"}
        if "how" in kw:
            kw["how"] = HOW[kw["how"]][li]
        for k in ("p1", "p2", "planet"):
            if k in kw and kw[k] in PN:
                kw[k] = PN[kw[k]][li]
        lines.append(TXT[y["key"]][li].format(**kw))
    return HEAD[li] + " " + " ".join(lines) + " " + TAIL[li]
