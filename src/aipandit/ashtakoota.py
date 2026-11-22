"""Ashtakoota Gun Milan (36 points), v1.0. Pure functions, no engine dependency.

Exact (standard Parashari tables): Varna, Tara, Graha Maitri, Gana, Bhakoot, Nadi.
Approximate and labelled as such: Vashya and Yoni (the full lookup matrices differ between texts, so we use the
safe core - same group/animal scores full, known enemy animals score 0, otherwise a neutral middle value).
The score is never rescaled or clamped: percent = total / 36. Classical cancellations (Nadi/Bhakoot exceptions,
Mangal dosha comparison) are reported as notes, not silently applied.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
LORD = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")
NAK_NAMES = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
             "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
             "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
YONI = ["Horse", "Elephant", "Sheep", "Serpent", "Serpent", "Dog", "Cat", "Sheep", "Cat", "Rat", "Rat", "Cow", "Buffalo", "Tiger",
        "Buffalo", "Tiger", "Deer", "Deer", "Dog", "Monkey", "Mongoose", "Monkey", "Lion", "Horse", "Lion", "Cow", "Elephant"]
GANA = ["Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya",
        "Deva", "Rakshasa", "Deva", "Rakshasa", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Rakshasa",
        "Manushya", "Manushya", "Deva"]
NADI = ["Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya",
        "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya"]
VARNA_OF = {"Karka": 4, "Vrishchika": 4, "Meena": 4, "Mesha": 3, "Simha": 3, "Dhanu": 3,
            "Vrishabha": 2, "Kanya": 2, "Makara": 2, "Mithuna": 1, "Tula": 1, "Kumbha": 1}
VARNA_NAME = {4: "Brahmin", 3: "Kshatriya", 2: "Vaishya", 1: "Shudra"}
ENEMY_YONI = {frozenset(p) for p in [("Horse", "Buffalo"), ("Elephant", "Lion"), ("Sheep", "Monkey"), ("Serpent", "Mongoose"),
                                     ("Cow", "Tiger"), ("Dog", "Deer"), ("Cat", "Rat")]}
VASHYA_OF = {"Mesha": "Chatushpada", "Vrishabha": "Chatushpada", "Mithuna": "Manava", "Karka": "Jalachara", "Simha": "Vanachara",
             "Kanya": "Manava", "Tula": "Manava", "Vrishchika": "Keeta", "Dhanu": "Manava", "Makara": "Chatushpada",
             "Kumbha": "Manava", "Meena": "Jalachara"}
# Parashari natural relationships (friend / neutral / enemy)
FRIEND = {"Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"}, "Mars": {"Sun", "Moon", "Jupiter"},
          "Mercury": {"Sun", "Venus"}, "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
          "Saturn": {"Mercury", "Venus"}}
ENEMY = {"Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"}, "Mercury": {"Moon"},
         "Jupiter": {"Mercury", "Venus"}, "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"}}


def _rel(a: str, b: str) -> str:
    if b in FRIEND[a]:
        return "F"
    if b in ENEMY[a]:
        return "E"
    return "N"


def graha_maitri_points(l1: str, l2: str) -> float:
    if l1 == l2:
        return 5.0
    pair = "".join(sorted(_rel(l1, l2) + _rel(l2, l1)))
    return {"FF": 5.0, "FN": 4.0, "NN": 3.0, "EF": 1.0, "EN": 0.5, "EE": 0.0}[pair]


def gana_points(g1: str, g2: str) -> float:
    table = {("Deva", "Deva"): 6, ("Deva", "Manushya"): 6, ("Deva", "Rakshasa"): 1,
             ("Manushya", "Deva"): 5, ("Manushya", "Manushya"): 6, ("Manushya", "Rakshasa"): 0,
             ("Rakshasa", "Deva"): 0, ("Rakshasa", "Manushya"): 0, ("Rakshasa", "Rakshasa"): 6}
    return float(table[(g1, g2)])


def tara_points(n1: int, n2: int) -> float:
    def good(frm: int, to: int) -> bool:
        return (((to - frm) % 27) + 1) % 9 not in (3, 5, 7)     # Vipat, Pratyak, Vadha
    g = good(n1, n2) + good(n2, n1)
    return {2: 3.0, 1: 1.5, 0: 0.0}[g]


def bhakoot(s1: int, s2: int) -> tuple:
    d = ((s2 - s1) % 12) + 1
    pair = {2: "2/12", 12: "2/12", 5: "5/9", 9: "5/9", 6: "6/8", 8: "6/8"}.get(d)
    return (0.0 if pair else 7.0), pair


def _idx(value: Any, names) -> Optional[int]:
    return names.index(value) if value in names else None


def compute(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """a, b: {"name", "rashi": "Simha", "nakshatra": "Magha"}. `a` is scored as the first partner (groom side in the
    directional kootas Varna/Gana); swap the arguments to see the other direction."""
    s1, s2 = _idx(a.get("rashi"), RASHIS), _idx(b.get("rashi"), RASHIS)
    n1, n2 = _idx(a.get("nakshatra"), NAK_NAMES), _idx(b.get("nakshatra"), NAK_NAMES)
    if None in (s1, s2, n1, n2):
        return {"ok": False, "error": "Moon sign and nakshatra are needed for both people (birth time may be missing or withheld)."}
    v1, v2 = VARNA_OF[RASHIS[s1]], VARNA_OF[RASHIS[s2]]
    k_varna = 1.0 if v1 >= v2 else 0.0
    h1, h2 = VASHYA_OF[RASHIS[s1]], VASHYA_OF[RASHIS[s2]]
    k_vashya = 2.0 if h1 == h2 else 1.0
    k_tara = tara_points(n1, n2)
    y1, y2 = YONI[n1], YONI[n2]
    k_yoni = 4.0 if y1 == y2 else 0.0 if frozenset((y1, y2)) in ENEMY_YONI else 2.0
    l1, l2 = LORD[s1], LORD[s2]
    k_maitri = graha_maitri_points(l1, l2)
    g1, g2 = GANA[n1], GANA[n2]
    k_gana = gana_points(g1, g2)
    k_bhakoot, bpair = bhakoot(s1, s2)
    nd1, nd2 = NADI[n1], NADI[n2]
    k_nadi = 0.0 if nd1 == nd2 else 8.0
    kootas: List[Dict[str, Any]] = [
        {"name": "Varna", "obtained": k_varna, "max": 1, "exact": True, "note": f"{VARNA_NAME[v1]} / {VARNA_NAME[v2]}"},
        {"name": "Vashya", "obtained": k_vashya, "max": 2, "exact": False, "note": f"{h1} / {h2} (simplified table)"},
        {"name": "Tara", "obtained": k_tara, "max": 3, "exact": True, "note": f"{NAK_NAMES[n1]} / {NAK_NAMES[n2]}"},
        {"name": "Yoni", "obtained": k_yoni, "max": 4, "exact": False, "note": f"{y1} / {y2} (simplified table)"},
        {"name": "Graha Maitri", "obtained": k_maitri, "max": 5, "exact": True, "note": f"{l1} / {l2}"},
        {"name": "Gana", "obtained": k_gana, "max": 6, "exact": True, "note": f"{g1} / {g2}"},
        {"name": "Bhakoot", "obtained": k_bhakoot, "max": 7, "exact": True, "note": f"signs {bpair} apart" if bpair else "no dosha pattern"},
        {"name": "Nadi", "obtained": k_nadi, "max": 8, "exact": True, "note": f"{nd1} / {nd2}"},
    ]
    total = round(sum(k["obtained"] for k in kootas), 1)
    notes: List[str] = []
    if k_nadi == 0:
        notes.append("Same Nadi (Nadi dosha). Traditional texts list exceptions, for example when the Moon signs or nakshatras differ in specific ways; a pandit should review this.")
    if bpair:
        notes.append(f"Bhakoot pattern {bpair}. It is traditionally softened when the two sign lords are the same planet or friends ({l1}/{l2}).")
    if not all(k["exact"] for k in kootas):
        notes.append("Vashya and Yoni use a simplified table here; the other six kootas follow the standard tables.")
    notes.append("Ashtakoota compares Moon placements only. It does not include Mangal dosha or a comparison of the full charts.")
    band = ("below the usual minimum of about 18" if total < 18 else "acceptable (18 to 24)" if total < 25
            else "good (25 to 32)" if total < 33 else "very good (33 or more)")
    return {"ok": True, "kootas": kootas, "total": total, "max": 36, "percent": round(total / 36 * 100),
            "band": band, "notes": notes, "first_partner": a.get("name") or "Partner 1", "second_partner": b.get("name") or "Partner 2"}
