"""Numerology facts (Indian / Chaldean-based). A separate system: rules and facts here never mix with Parashari.

Computed from the civil birth DATE (not the birth time), so these facts exist even when the birth time is unknown.
  Mulank   (birth number)   = day of the month reduced to one digit
  Bhagyank (destiny number) = every digit of day+month+year added, reduced to one digit
  Name number (optional)    = Chaldean letter values of the Latin-script name, reduced to one digit
  Personal year             = day + month + the current year, reduced to one digit (a yearly "theme", not a forecast)
Number-to-planet links use the common Indian scheme: 1 Sun, 2 Moon, 3 Jupiter, 4 Rahu, 5 Mercury, 6 Venus,
7 Ketu, 8 Saturn, 9 Mars. Other schemes exist (Pythagorean names, master numbers 11/22/33); this module states its
choice and does not mix them.

Honest status: numerology has no classical Vedic text behind it and no validated predictive record. These are
traditional/popular readings, and every rule built on them is provenance "later_tradition", review "draft".
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .fact_ir import Fact, FactStore

SYS = "numerology"
VERSION = "numerology:v1"
NUMBER_PLANET = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury", 6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}
# Chaldean letter values (1-8; 9 is not assigned to any letter)
CHALDEAN = {c: v for v, letters in {1: "AIJQY", 2: "BKR", 3: "CGLS", 4: "DMT", 5: "EHNX", 6: "UVW", 7: "OZ", 8: "FP"}.items()
            for c in letters}


def reduce_digit(n: int) -> int:
    """Digital root: 1..9 for any positive integer."""
    if n <= 0:
        raise ValueError("reduce_digit needs a positive integer")
    return 1 + (n - 1) % 9


def mulank(day: int) -> int:
    return reduce_digit(day)


def bhagyank(year: int, month: int, day: int) -> int:
    return reduce_digit(sum(int(c) for c in f"{year}{month}{day}"))


def personal_year(month: int, day: int, year: int) -> int:
    return reduce_digit(sum(int(c) for c in f"{day}{month}{year}"))


def name_number(name: str) -> Optional[int]:
    letters = [c for c in (name or "").upper() if "A" <= c <= "Z"]
    if len(letters) < 2:
        return None
    return reduce_digit(sum(CHALDEAN[c] for c in letters))


def enrich(store: FactStore, birth_date: str, name: Optional[str] = None, as_of: Optional[datetime] = None) -> FactStore:
    """Return a new frozen store = `store` + numerology facts."""
    y, m, d = (int(x) for x in birth_date.split("-"))
    out = FactStore(birth_hash=store.birth_hash)
    for f in store:
        out.add(f)

    def put(subject, predicate, value, why):
        out.add(Fact(subject, predicate, value, SYS, 1.0, f"{VERSION}|{why}"))

    for key, val, why in (("mulank", mulank(d), "day of birth reduced"),
                          ("bhagyank", bhagyank(y, m, d), "all digits of the birth date reduced")):
        put(key, "value", val, why)
        put(key, "planet", NUMBER_PLANET[val], "Indian number-planet scheme")
    n = name_number(name or "")
    if n is not None:
        put("name_number", "value", n, "Chaldean letter values")
        put("name_number", "planet", NUMBER_PLANET[n], "Indian number-planet scheme")
    if as_of is not None:
        py = personal_year(m, d, as_of.year)
        put("personal_year", "value", py, "birth day+month plus the current year, reduced")
        put("personal_year", "as_of_year", as_of.year, "session date")
    return out.freeze()
