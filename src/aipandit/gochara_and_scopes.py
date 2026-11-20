"""Live transits (Gochara) and starter rules for Education, Children & Family.

Keeps Gochara transit facts under system='gochara' so they never overwrite natal
Parashari facts in FactStore, and provides tendency-based rules for scopes that
were previously uncovered (education, children, family).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .fact_ir import Fact, FactStore
from .jyotish import sign_index
from .predicate import And, Eq, In
from .rules import Rule, Source

GOCHARA_SYS = "gochara"
SCOPE_SYS = "parashari"

SHASTRA_SRC = Source(
    text="Brihat Parashara Hora Shastra & Classical Jyotish Tradition",
    chapter="bhava_and_gochara",
    edition="Astrobrain starter rulepack (requires astrologer audit)",
    licence="unspecified",
)


def _approx_sidereal_longitude(planet: str, on_date: date) -> float:
    """Deterministic approximate sidereal longitude for slow transits (Guru, Shani, Rahu)."""
    days_j2000 = on_date.toordinal() - 2451545
    if planet == "Jupiter":
        lon = (42.0 + days_j2000 * (360.0 / (11.8626 * 365.25636))) % 360.0
    elif planet == "Saturn":
        lon = (40.0 + days_j2000 * (360.0 / (29.4571 * 365.25636))) % 360.0
    elif planet == "Rahu":
        lon = (125.0 - days_j2000 * (360.0 / (18.6129 * 365.25636))) % 360.0
    else:
        raise ValueError(f"Unsupported transit planet: {planet}")
    return round(lon, 4)


def enrich_gochara(store: FactStore, on_date: Optional[date] = None) -> FactStore:
    """Return a new frozen store = `store` + Gochara transit facts for `on_date`."""
    target_date = on_date or date.today()
    out = FactStore(birth_hash=store.birth_hash)
    for f in store:
        out.add(f)

    moon_sign = store.value("Moon", "sign_index", "parashari")
    out.add(Fact("transit", "date", target_date.isoformat(), GOCHARA_SYS, 1.0, "gochara:v1|target_date"))

    for planet in ("Jupiter", "Saturn", "Rahu"):
        lon = _approx_sidereal_longitude(planet, target_date)
        s_idx = sign_index(lon)
        out.add(Fact(planet, "transit_sign_index", s_idx, GOCHARA_SYS, 0.75, "gochara:v1|approx_transit"))
        if moon_sign is not None:
            house_from_moon = (s_idx - moon_sign) % 12 + 1
            out.add(
                Fact(
                    planet,
                    "house_from_natal_moon",
                    house_from_moon,
                    GOCHARA_SYS,
                    0.75,
                    "gochara:v1|from_natal_moon",
                )
            )
    return out.freeze()


def gochara_rules() -> list[Rule]:
    """Starter Gochara transit rules under system='gochara'."""
    return [
        Rule(
            rule_id="gochara.jupiter_favorable_moon",
            system=GOCHARA_SYS,
            condition=In(GOCHARA_SYS, "Jupiter", "house_from_natal_moon", (2, 5, 7, 9, 11)),
            scope=("general", "career", "wealth"),
            interpretation="In Gochara (transit), Jupiter is in a traditionally supportive house counted from the natal Moon, often associated with growth, learning or steady opportunities; this is a general transit tendency, not a guarantee.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="later_tradition",
            adverse=False,
            rarity="common",
            notes="Approximate transit position; refine with full ephemeris before production launch.",
        ),
        Rule(
            rule_id="gochara.saturn_sade_sati_window",
            system=GOCHARA_SYS,
            condition=In(GOCHARA_SYS, "Saturn", "house_from_natal_moon", (12, 1, 2)),
            scope=("general", "mind", "career"),
            interpretation="In Gochara (transit), Saturn is transiting the 12th, 1st or 2nd sign from the natal Moon (the Sade Sati zone), traditionally read as a period calling for patience, discipline and steady boundaries rather than fear.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="later_tradition",
            adverse=True,
            rarity="moderate",
            notes="Framed gently without fear-mongering; requires astrologer audit.",
        ),
    ]


def life_area_rules() -> list[Rule]:
    """Starter rules covering Education, Children, and Family under system='parashari'."""
    return [
        Rule(
            rule_id="parashari.education.jupiter_or_mercury_kendra_trikona",
            system=SCOPE_SYS,
            condition=In(SCOPE_SYS, "Jupiter", "house", (1, 4, 5, 9, 10)),
            scope=("education",),
            interpretation="For education themes, Jupiter placed in a kendra or trikona house from Lagna is traditionally associated with studiousness, mentorship and broader conceptual learning.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="synthesized",
            adverse=False,
            rarity="common",
            notes="Starter rule for previously uncovered 'education' scope.",
        ),
        Rule(
            rule_id="parashari.education.house5_lord_strong",
            system=SCOPE_SYS,
            condition=In(SCOPE_SYS, "house5", "lord_house", (1, 4, 5, 7, 9, 10, 11)),
            scope=("education",),
            interpretation="The lord of the 5th house (traditionally linked with learning and intellect) is placed in a supportive house, associated with steady study focus when effort is consistent.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="synthesized",
            adverse=False,
            rarity="common",
            notes="Starter rule for 'education' scope.",
        ),
        Rule(
            rule_id="parashari.children.house5_lord_supportive",
            system=SCOPE_SYS,
            condition=In(SCOPE_SYS, "house5", "lord_house", (1, 2, 4, 5, 9, 11)),
            scope=("children",),
            interpretation="In traditional Parashari reading, the 5th house lord placed in a kendra, trikona or gain house is associated with positive themes around children and creative mentorship.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="synthesized",
            adverse=False,
            rarity="common",
            notes="Starter rule for 'children' scope; never shown to minor charts.",
        ),
        Rule(
            rule_id="parashari.family.house2_lord_supportive",
            system=SCOPE_SYS,
            condition=Eq(SCOPE_SYS, "house2", "lord_house", 2),
            scope=("family",),
            interpretation="In traditional Parashari reading, the 2nd house lord in its own 2nd house is associated with family continuity, shared values and home-rooted stability.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="synthesized",
            adverse=False,
            rarity="rare",
            notes="Starter rule for 'family' scope.",
        ),
        Rule(
            rule_id="parashari.family.house4_kendra_supportive",
            system=SCOPE_SYS,
            condition=In(SCOPE_SYS, "house4", "lord_house", (1, 4, 5, 7, 9, 10)),
            scope=("family",),
            interpretation="In traditional Parashari reading, the 4th house lord placed in a kendra or trikona is associated with domestic harmony and a grounded home environment.",
            source=SHASTRA_SRC,
            review_status="draft",
            provenance="synthesized",
            adverse=False,
            rarity="common",
            notes="Starter rule for 'family' scope.",
        ),
    ]
