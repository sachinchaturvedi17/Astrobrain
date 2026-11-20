"""Astronomy engine contract. The orchestrator never touches ephemeris math;
it only sees these dataclasses."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EngineLimit(Exception):
    """The engine cannot give a trustworthy answer (e.g. polar latitudes)."""


@dataclass(frozen=True)
class RawPlanet:
    name: str
    longitude: float      # sidereal, degrees [0,360)
    speed: float          # deg/day
    retrograde: bool


@dataclass(frozen=True)
class RawChart:
    jd_ut: float
    planets: dict          # name -> RawPlanet; includes Rahu and Ketu
    lagna_longitude: float
    mc_longitude: float
    engine_id: str


@dataclass(frozen=True)
class DashaPeriod:
    lord: str
    start_jd: float
    end_jd: float
    sub: tuple = ()


@dataclass(frozen=True)
class DashaResult:
    initial_balance_fraction: float    # fraction of the first maha remaining at birth
    mahas: tuple


class AstronomyEngine(Protocol):
    engine_id: str
    dasha_year_days: float
    lagna_error_arcsec: float     # measured worst-case vs reference (see tests/test_oracle.py)
    planet_error_arcsec: float

    def natal(self, jd_ut: float, lat: float, lon: float, *,
              ayanamsa: str, node_mode: str) -> RawChart: ...

    def vimshottari(self, birth_jd: float, moon_longitude: float, depth: int = 2) -> DashaResult: ...
