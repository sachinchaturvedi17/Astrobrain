"""Vedaksha adapter (runs locally via WebAssembly; no birth data leaves the process).

Vedaksha is BUSL-1.1: free for non-commercial use, commercial use needs a licence.
Only the Lahiri (IndianOfficial) ayanamsa is validated by this project's oracle
tests; others are exposed but flagged by kundli.generate_kundli.
"""
from __future__ import annotations

import importlib.metadata

from .base import (DashaPeriod, DashaResult, EngineLimit, RawChart, RawPlanet)

# Our names -> Vedaksha enum names.
AYANAMSA_MAP = {
    "lahiri": "IndianOfficial",
    "raman": "Raman",
    "kp": "Krishnamurti",
    "true_chitra": "TrueChitra",
    "fagan_bradley": "FaganBradley",
    "yukteshwar": "Yukteshwar",
    "surya_siddhanta": "SuryaSiddhanta",
    "pushya_paksha": "PushyaPaksha",
    "revati_paksha": "RevatiPaksha",
}
VALIDATED_AYANAMSAS = frozenset({"lahiri"})
NODE_KEYS = {"mean": "MeanNode", "true": "TrueNode"}
_CLASSICAL = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


class VedakshaEngine:
    dasha_year_days = 365.25   # verified: Sun/Sun antar = 0.3 yr = 109.575 d
    # Measured vs Swiss Ephemeris over 200 random charts, 1930-2025, lat -55..62 (tests/test_oracle.py):
    #   planets worst 1.82"; Lagna worst 19.3" - Vedaksha computes the Ascendant with MEAN obliquity
    #   where Swiss uses TRUE obliquity (mean + nutation, +-9"). The error is ~0 at the equator and
    #   grows with latitude. Bounds below are what kundli.py uses to refuse to assert a sign/nakshatra
    #   that sits closer to a boundary than the engine can be trusted.
    lagna_error_arcsec = 20.0
    planet_error_arcsec = 2.5

    def __init__(self) -> None:
        from vedaksha import Vedaksha
        self._vk = Vedaksha()
        self.version = importlib.metadata.version("vedaksha")
        self.engine_id = f"vedaksha:{self.version}"

    def natal(self, jd_ut: float, lat: float, lon: float, *,
              ayanamsa: str = "lahiri", node_mode: str = "mean") -> RawChart:
        if ayanamsa not in AYANAMSA_MAP:
            raise ValueError(f"unknown ayanamsa {ayanamsa!r}; choose from {sorted(AYANAMSA_MAP)}")
        if node_mode not in NODE_KEYS:
            raise ValueError("node_mode must be 'mean' or 'true'")
        chart = self._vk.natal_chart(
            jd_ut, lat, lon, house_system="whole_sign", ayanamsha=AYANAMSA_MAP[ayanamsa]
        )
        houses = chart["houses"]
        if houses.get("polar_fallback"):
            raise EngineLimit("ascendant undefined or unreliable at this latitude")

        by_name = {p["name"]: p for p in chart["planets"]}
        planets = {}
        for n in _CLASSICAL:
            p = by_name[n]
            planets[n] = RawPlanet(n, p["longitude"] % 360.0, p["speed"], bool(p["retrograde"]))
        node = by_name[NODE_KEYS[node_mode]]
        rahu_lon = node["longitude"] % 360.0
        planets["Rahu"] = RawPlanet("Rahu", rahu_lon, node["speed"], bool(node["retrograde"]))
        planets["Ketu"] = RawPlanet("Ketu", (rahu_lon + 180.0) % 360.0, node["speed"],
                                    bool(node["retrograde"]))
        return RawChart(
            jd_ut=jd_ut,
            planets=planets,
            lagna_longitude=houses["asc"] % 360.0,
            mc_longitude=houses["mc"] % 360.0,
            engine_id=f"{self.engine_id}:{AYANAMSA_MAP[ayanamsa]}",
        )

    def vimshottari(self, birth_jd: float, moon_longitude: float, depth: int = 2) -> DashaResult:
        res = self._vk.call_tool(
            "compute_dasha", system="Vimshottari",
            birth_jd=birth_jd, moon_longitude=moon_longitude,
        )

        def parse(nodes, d):
            out = []
            for n in nodes:
                sub = parse(n.get("sub_periods", []), d - 1) if d > 1 else ()
                out.append(DashaPeriod(n["lord"], n["start_jd"], n["end_jd"], tuple(sub)))
            return tuple(out)

        return DashaResult(res["initial_balance"], parse(res["maha_dashas"], depth))
