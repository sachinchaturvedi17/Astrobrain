"""Derived facts: classical relationships computed from the Phase 1 observations.

Still observations, not interpretations. A derived fact exists only if *every*
input it needs exists; a withheld input therefore leaves the derived fact absent
and any rule that needs it evaluates to UNKNOWN (never silently FALSE).

Conventions chosen here (each is a point on which traditions differ, so each is
stated explicitly and covered by tests):
  * Sign-level geometry only. Conjunction = same rashi; aspects = rashi-based
    graha drishti. Degree-based refinements (orbs, combustion) are NOT derived
    because the thresholds differ between sources and are not yet pinned.
  * Graha drishti: every planet aspects the 7th sign from itself; Mars also the
    4th and 8th; Jupiter the 5th and 9th; Saturn the 3rd and 10th (counted
    inclusively). Rahu and Ketu cast no aspect here (traditions disagree).
  * Dignity is sign-level: exalted / debilitated / own / neutral. Exaltation takes
    precedence, so Mercury in Kanya is "exalted" (and in_own_sign is also true).
    Moolatrikona and degree-wise exaltation need an exact longitude and are not derived.
    Rahu/Ketu dignity is not derived (traditions disagree on their signs).
  * House lordship is by sign rulership with Rahu/Ketu given no lordship.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .fact_ir import Fact, FactStore
from .jyotish import GRAHAS

SYS = "parashari"
VERSION = "derive:v1"

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
#                 Mesha    Vrishabha Mithuna   Karka   Simha  Kanya     Tula    Vrishchika Dhanu     Makara   Kumbha   Meena
SIGN_LORD = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars",
             "Jupiter", "Saturn", "Saturn", "Jupiter")
EXALT_SIGN = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBIL_SIGN = {g: (s + 6) % 12 for g, s in EXALT_SIGN.items()}
OWN_SIGNS = {g: tuple(i for i, lord in enumerate(SIGN_LORD) if lord == g) for g in SEVEN}
ASPECT_OFFSETS = {  # inclusive count from the planet's own sign
    "Sun": (7,), "Moon": (7,), "Mercury": (7,), "Venus": (7,),
    "Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10),
}
KENDRA = (1, 4, 7, 10)
TRIKONA = (1, 5, 9)
DUSTHANA = (6, 8, 12)
REFERENCES = ("Moon", "Sun", "Venus")     # house-counting references besides the Lagna


def pair(a: str, b: str) -> str:
    """Canonical subject for an unordered graha pair, e.g. 'Sun+Mercury'."""
    ia, ib = GRAHAS.index(a), GRAHAS.index(b)
    return f"{a}+{b}" if ia < ib else f"{b}+{a}"


def aspect_subject(a: str, b: str) -> str:
    """Subject for 'a aspects b' (directional), e.g. 'Jupiter>Moon'."""
    return f"{a}>{b}"


def lord_pair(h1: int, h2: int) -> str:
    lo, hi = sorted((h1, h2))
    return f"lord{lo}+lord{hi}"


def aspects(a: str, sign_a: int, sign_b: int) -> bool:
    off = (sign_b - sign_a) % 12 + 1
    return off in ASPECT_OFFSETS.get(a, ())


def lord_relation(la: str, lb: str, sa: int, sb: int) -> str:
    """Relation between two planets given their signs (la in sa, lb in sb)."""
    if la == lb:
        return "same_planet"
    if SIGN_LORD[sb] == la and SIGN_LORD[sa] == lb:
        return "exchange"
    if sa == sb:
        return "conjunct"
    a_to_b, b_to_a = aspects(la, sa, sb), aspects(lb, sb, sa)
    if a_to_b and b_to_a:
        return "mutual_aspect"
    if a_to_b or b_to_a:
        return "one_way_aspect"
    return "none"


def enrich(kundli, as_of: Optional[datetime] = None) -> FactStore:
    """Return a new frozen store = Phase 1 facts + derived facts."""
    base: FactStore = kundli.facts
    out = FactStore(birth_hash=base.birth_hash)
    for f in base:
        out.add(f)

    def put(subject, predicate, value, why):
        out.add(Fact(subject, predicate, value, SYS, 1.0, f"{VERSION}|{why}"))

    sign = {g: base.value(g, "sign_index", SYS) for g in GRAHAS}
    house = {g: base.value(g, "house", SYS) for g in GRAHAS}
    lagna = base.value("lagna", "sign_index", SYS)

    # --- dignity (7 grahas) -------------------------------------------------
    for g in SEVEN:
        s = sign[g]
        if s is None:
            continue
        put(g, "in_own_sign", s in OWN_SIGNS[g], "sign")
        dig = ("exalted" if s == EXALT_SIGN[g] else
               "debilitated" if s == DEBIL_SIGN[g] else
               "own" if s in OWN_SIGNS[g] else "neutral")
        put(g, "dignity", dig, "sign-level table")

    # --- dispositor (all 9; nodes are disposed by the sign lord) ------------
    for g in GRAHAS:
        if sign[g] is None:
            continue
        disp = SIGN_LORD[sign[g]]
        put(g, "dispositor", disp, "sign lord of the occupied sign")
        if house[disp] is not None:
            put(g, "dispositor_house", house[disp], "house of the dispositor")

    # --- house lordship (needs the Lagna sign) -------------------------------
    lord = {}
    if lagna is not None:
        for n in range(1, 13):
            lord[n] = SIGN_LORD[(lagna + n - 1) % 12]
            put(f"house{n}", "lord", lord[n], "sign rulership from the Lagna sign")
            if house[lord[n]] is not None:
                put(f"house{n}", "lord_house", house[lord[n]], "house occupied by the lord")

    # --- counting from the Moon / Sun / Venus --------------------------------
    for ref in REFERENCES:
        if sign[ref] is None:
            continue
        for g in GRAHAS:
            if sign[g] is not None:
                put(g, f"house_from_{ref.lower()}", (sign[g] - sign[ref]) % 12 + 1, f"counted from {ref}")

    # --- conjunction (same rashi) --------------------------------------------
    for i, a in enumerate(GRAHAS):
        for b in GRAHAS[i + 1:]:
            if sign[a] is not None and sign[b] is not None:
                put(pair(a, b), "conjunct", sign[a] == sign[b], "same rashi")

    # --- graha drishti --------------------------------------------------------
    for a in SEVEN:
        for b in GRAHAS:
            if a != b and sign[a] is not None and sign[b] is not None:
                put(aspect_subject(a, b), "aspects", aspects(a, sign[a], sign[b]), "rashi drishti")

    # --- relations between house lords ---------------------------------------
    if lagna is not None:
        for h1 in range(1, 13):
            for h2 in range(h1 + 1, 13):
                la, lb = lord[h1], lord[h2]
                if sign[la] is not None and sign[lb] is not None:
                    put(lord_pair(h1, h2), "relation", lord_relation(la, lb, sign[la], sign[lb]),
                        f"lord of {h1} ({la}) vs lord of {h2} ({lb})")

    # --- Rahu-Ketu hemming (needs exact longitudes) ---------------------------
    lon = {g: base.value(g, "longitude", SYS) for g in SEVEN + ("Rahu",)}
    if all(v is not None for v in lon.values()):
        offs = [(lon[g] - lon["Rahu"]) % 360.0 for g in SEVEN]
        if all(0.0 < o < 180.0 for o in offs):
            mode = "rahu_to_ketu"
        elif all(180.0 < o < 360.0 for o in offs):
            mode = "ketu_to_rahu"
        else:
            mode = "none"
        put("chart", "nodal_hemming", mode, "all seven grahas vs the Rahu-Ketu axis")

    # --- running dasha at a date (optional) -----------------------------------
    if as_of is not None and getattr(kundli, "dasha", None) is not None:
        from .kundli import dasha_at
        try:
            d = dasha_at(kundli, as_of)
        except ValueError:
            d = None
        if d:
            out.add(Fact("chart", "as_of", as_of.date().isoformat(), "session", 1.0, VERSION))
            put("dasha", "maha_lord", d["maha"], "Vimshottari at as_of")
            put("dasha", "maha_end", d["maha_end"], "Vimshottari at as_of")
            if d.get("antar"):
                put("dasha", "antar_lord", d["antar"], "Vimshottari at as_of")
                put("dasha", "antar_end", d["antar_end"], "Vimshottari at as_of")

    return out.freeze()
