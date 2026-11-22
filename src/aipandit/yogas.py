"""Computed yoga check (v1.1.2). Pure functions over the chart dict; no astronomy here.

Only sign-level rules the chart can support are used, and each is worded as a tendency, never a promise:
  * Gajakesari: Jupiter in a kendra (1, 4, 7, 10) counted from the Moon.
  * Budhaditya: Sun and Mercury in the same sign.
  * Chandra-Mangal: Moon and Mars in the same sign.
  * Pancha Mahapurusha: Mars, Mercury, Jupiter, Venus or Saturn in its own/exalted sign AND in a kendra from the Lagna
    (needs a reliable Lagna, so it is skipped when only the Moon chart is available).
  * Guru Chandal: Jupiter and Rahu in the same sign (a caution, worded gently).
"""
from __future__ import annotations

from typing import Any, Dict, List

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
LI = {"en": 0, "hg": 1, "hi": 2}
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
    "mahapurusha": ("{name} yoga, one of the five Mahapurusha yogas: {planet} is strong in its own or exalted sign and stands in a pillar house of your chart. Tradition links it with standing out in that planet's area of life.",
                    "{name} yoga, paanch Mahapurusha yogon mein se ek: {planet} apni ya uchch rashi mein majboot hai aur aapke chart ke mukhya bhav mein hai. Parampara ise us graha ke kshetra mein alag pehchaan se jodti hai.",
                    "{name} योग, पाँच महापुरुष योगों में से एक: {planet} अपनी या उच्च राशि में मज़बूत है और आपकी कुंडली के मुख्य भाव में है। परंपरा इसे उस ग्रह के क्षेत्र में अलग पहचान से जोड़ती है।"),
    "gurucandal": ("Guru-Chandal pattern: Jupiter shares a sign with Rahu. It is read as a nudge to question borrowed beliefs and pick your teachers carefully, not as a curse.",
                   "Guru-Chandal pattern: Guru aur Rahu ek hi rashi mein hain. Ise udhaar ki maanyataon par sawaal karne aur guru soch-samajh kar chunne ka ishara samjhein, shraap nahi.",
                   "गुरु-चांडाल पैटर्न: गुरु और राहु एक ही राशि में हैं। इसे उधार की मान्यताओं पर सवाल करने और गुरु सोच-समझकर चुनने का इशारा समझें, श्राप नहीं।"),
}
NONE = ("I looked for the well-known yogas (Gajakesari, Budhaditya, Chandra-Mangal, the five Mahapurusha yogas) and none show up in your chart by the usual sign-based rules. That says very little: yogas are one small part of a chart, and most good qualities in a life come from the whole picture.",
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
    return out


def yoga_text(chart: Dict[str, Any], lang: str, lagna_ok: bool = True) -> str:
    li = LI.get(lang, 0)
    found = find_yogas(chart, lagna_ok)
    if not found:
        return NONE[li]
    lines = [TXT[y["key"]][li].format(**{k: v for k, v in y.items() if k != "key"}) for y in found]
    return HEAD[li] + " " + " ".join(lines) + " " + TAIL[li]
