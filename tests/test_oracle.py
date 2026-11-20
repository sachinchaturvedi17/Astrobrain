"""Oracle suite: Vedaksha (production engine) vs Swiss Ephemeris (dev-only, AGPL).

Swiss Ephemeris must never be imported by anything under src/. Run with
`pytest -m oracle`. Tolerances are tighter than anything astrologically
meaningful: a planet error of 2" is ~0.0006 deg.
"""
import random
from datetime import datetime, timedelta, timezone

import pytest

swe = pytest.importorskip("swisseph")

from aipandit.engines.vedaksha_engine import VedakshaEngine          # noqa: E402
from aipandit.intake import julian_day_ut                              # noqa: E402
from aipandit.jyotish import VIMSHOTTARI_ORDER, VIMSHOTTARI_YEARS, nakshatra_of, sign_index  # noqa: E402

pytestmark = pytest.mark.oracle

BODIES = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
          "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN}
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL


def arcsec(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0) * 3600.0


def samples(n=200, seed=20261120):
    rnd = random.Random(seed)
    start = datetime(1930, 1, 1, tzinfo=timezone.utc)
    span = int((datetime(2025, 12, 31, tzinfo=timezone.utc) - start).total_seconds())
    out = []
    while len(out) < n:
        t = start + timedelta(seconds=rnd.randrange(span))
        lat = rnd.uniform(-55, 62)        # below the polar-fallback latitudes
        lon = rnd.uniform(-180, 180)
        out.append((t, lat, lon))
    return out


@pytest.fixture(scope="module")
def engine():
    return VedakshaEngine()


def test_planets_lagna_mc_and_mean_node_vs_swisseph(engine):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    worst = {"planet": 0.0, "lagna": 0.0, "mc": 0.0, "rahu": 0.0}
    for t, lat, lon in samples():
        jd = julian_day_ut(t)
        c = engine.natal(jd, lat, lon, ayanamsa="lahiri", node_mode="mean")
        for name, code in BODIES.items():
            ref = swe.calc_ut(jd, code, FLAGS)[0][0]
            worst["planet"] = max(worst["planet"], arcsec(c.planets[name].longitude, ref))
        _, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
        worst["lagna"] = max(worst["lagna"], arcsec(c.lagna_longitude, ascmc[0]))
        worst["mc"] = max(worst["mc"], arcsec(c.mc_longitude, ascmc[1]))
        worst["rahu"] = max(worst["rahu"], arcsec(c.planets["Rahu"].longitude, swe.calc_ut(jd, swe.MEAN_NODE, FLAGS)[0][0]))
    print("worst-case arcsec over 200 charts:", worst)
    assert worst["planet"] < engine.planet_error_arcsec     # measured 1.82"
    assert worst["rahu"] < 2.0
    assert worst["mc"] < 5.0                                # measured 2.2"
    # Lagna: NOT within 5". Measured worst 19.3" at 58N; see the next test for the cause.
    assert worst["lagna"] < engine.lagna_error_arcsec


def _asc(ramc_deg, eps_deg, lat):
    import math
    th, ep, ph = map(math.radians, (ramc_deg, eps_deg, lat))
    return math.degrees(math.atan2(math.cos(th), -(math.sin(th) * math.cos(ep) + math.tan(ph) * math.sin(ep)))) % 360


def test_lagna_deviation_is_fully_explained_by_mean_vs_true_obliquity(engine):
    """Vedaksha's Ascendant == Swiss's with MEAN obliquity substituted for TRUE obliquity.
    If this stops holding the engine changed behaviour and the declared bound must be re-measured."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sg = lambda a, b: (a - b + 180.0) % 360.0 - 180.0
    worst_resid = 0.0
    for t, lat, lon in samples():
        jd = julian_day_ut(t)
        c = engine.natal(jd, lat, lon, ayanamsa="lahiri")
        _, sid = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
        _, trop = swe.houses_ex(jd, lat, lon, b"W")
        true_eps, mean_eps = swe.calc_ut(jd, swe.ECL_NUT)[0][:2]
        predicted = sg(_asc(trop[2], mean_eps, lat), _asc(trop[2], true_eps, lat)) * 3600
        actual = sg(c.lagna_longitude, sid[0]) * 3600
        worst_resid = max(worst_resid, abs(actual - predicted))
    assert worst_resid < 0.5, worst_resid          # measured 0.08" worst-case-ish residual (std)


def test_lagna_sign_agrees_except_within_arcseconds_of_a_boundary(engine):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    for t, lat, lon in samples(150, seed=7):
        jd = julian_day_ut(t)
        c = engine.natal(jd, lat, lon, ayanamsa="lahiri")
        _, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
        if sign_index(c.lagna_longitude) != sign_index(ascmc[0]):
            edge = min(ascmc[0] % 30.0, 30.0 - ascmc[0] % 30.0) * 3600.0
            assert edge < 5.0, f"lagna sign differs {edge:.1f} arcsec from a boundary"


def test_vimshottari_matches_independent_implementation(engine):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    yd = engine.dasha_year_days
    for t, lat, lon in samples(60, seed=11):
        jd = julian_day_ut(t)
        moon = swe.calc_ut(jd, swe.MOON, FLAGS)[0][0]
        npos = nakshatra_of(moon)
        res = engine.vimshottari(jd, moon, depth=1)
        start = jd
        i = VIMSHOTTARI_ORDER.index(npos.lord)
        for k, m in enumerate(res.mahas):
            lord = VIMSHOTTARI_ORDER[(i + k) % 9]
            years = VIMSHOTTARI_YEARS[lord] * ((1 - npos.fraction_elapsed) if k == 0 else 1.0)
            end = start + years * yd
            assert m.lord == lord
            assert abs(m.end_jd - end) < 0.01, (m.lord, m.end_jd - end)    # < 15 minutes
            start = end
