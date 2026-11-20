"""Test helpers: build charts with exact placements (no ephemeris) and run the rule base."""
from dataclasses import replace

from aipandit.derive import enrich
from aipandit.engines.base import RawChart, RawPlanet
from aipandit.engines.vedaksha_engine import VedakshaEngine
from aipandit.inference import infer
from aipandit.intake import BirthInput
from aipandit.jyotish import GRAHAS
from aipandit.kundli import generate_kundli
from aipandit.rulepacks import parashari_rules

RULES = parashari_rules()
_real = VedakshaEngine()


class FixedEngine:
    """Returns exactly the placements it is given. Dasha is delegated to the real engine."""
    lagna_error_arcsec = _real.lagna_error_arcsec
    planet_error_arcsec = _real.planet_error_arcsec
    dasha_year_days = _real.dasha_year_days
    engine_id = "fixed:test"

    def __init__(self, lagna_lon, lons):
        self.lagna_lon, self.lons = lagna_lon, lons

    def natal(self, jd_ut, lat, lon, *, ayanamsa, node_mode):
        planets = {g: RawPlanet(g, self.lons[g], 1.0, False) for g in GRAHAS}
        return RawChart(jd_ut, planets, self.lagna_lon, (self.lagna_lon + 90) % 360, self.engine_id)

    def vimshottari(self, birth_jd, moon_longitude, depth=2):
        return _real.vimshottari(birth_jd, moon_longitude, depth)


BIRTH = BirthInput(name="t", date="1990-05-15", time="14:30", time_certainty="exact",
                   place_name="Bhopal", latitude=23.2599, longitude=77.4126,
                   tz_name="Asia/Kolkata", subject_is_minor=False)


def make(lagna, signs=None, lons=None, birth=BIRTH):
    """lagna: sign index. signs: {graha: sign index} placed mid-sign. lons: {graha: absolute longitude}.
    Unspecified grahas default to Mesha mid-sign; Ketu defaults to Rahu + 180."""
    full = {g: 15.0 for g in GRAHAS}
    for g, s in (signs or {}).items():
        full[g] = s * 30 + 15.0
    full.update(lons or {})
    if "Ketu" not in (signs or {}) and "Ketu" not in (lons or {}):
        full["Ketu"] = (full["Rahu"] + 180.0) % 360
    k = generate_kundli(birth, engine=FixedEngine(lagna * 30 + 15.0, full))
    return k, enrich(k)


def fired(store, rules=RULES):
    return infer(store, rules).fired_ids()


MESHA, VRISHABHA, MITHUNA, KARKA, SIMHA, KANYA, TULA, VRISCHIKA, DHANU, MAKARA, KUMBHA, MEENA = range(12)
