"""Pure Jyotish arithmetic: signs, nakshatras, padas, whole-sign houses.

Everything here is deterministic arithmetic on sidereal longitudes. No astronomy.
"""
from __future__ import annotations

from dataclasses import dataclass

SIGNS = (
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
)

NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
)

# Vimshottari order; nakshatra i is ruled by VIMSHOTTARI_ORDER[i % 9].
VIMSHOTTARI_ORDER = (
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
)
VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

NAK_SPAN = 360.0 / 27.0
PADA_SPAN = NAK_SPAN / 4.0

GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


@dataclass(frozen=True)
class NakshatraPosition:
    index: int
    name: str
    pada: int
    lord: str
    fraction_elapsed: float


def norm360(x: float) -> float:
    return x % 360.0


def sign_index(longitude: float) -> int:
    return min(int(norm360(longitude) // 30.0), 11)


def sign_name(longitude: float) -> str:
    return SIGNS[sign_index(longitude)]


def nakshatra_of(longitude: float) -> NakshatraPosition:
    lon = norm360(longitude)
    idx = min(int(lon // NAK_SPAN), 26)
    within = lon - idx * NAK_SPAN
    pada = min(int(within // PADA_SPAN) + 1, 4)
    return NakshatraPosition(
        index=idx,
        name=NAKSHATRAS[idx],
        pada=pada,
        lord=VIMSHOTTARI_ORDER[idx % 9],
        fraction_elapsed=within / NAK_SPAN,
    )


def whole_sign_house(planet_longitude: float, lagna_longitude: float) -> int:
    """House 1-12 counted from the lagna sign (whole-sign system)."""
    return (sign_index(planet_longitude) - sign_index(lagna_longitude)) % 12 + 1
