"""Golden tests. Expected values were produced by an independent engine
(Swiss Ephemeris, SIDM_LAHIRI) and hand-checked; see docs/RESEARCH_FINDINGS.md."""
from datetime import date, datetime, timezone

import pytest

from aipandit.engines.vedaksha_engine import VedakshaEngine
from aipandit.intake import BirthInput
from aipandit.kundli import KundliConfig, dasha_at, generate_kundli

TODAY = date(2026, 11, 20)


@pytest.fixture(scope="module")
def engine():
    return VedakshaEngine()


def bhopal(**kw):
    base = dict(name="t", date="1990-05-15", time="14:30", time_certainty="exact",
                place_name="Bhopal", latitude=23.2599, longitude=77.4126, tz_name="Asia/Kolkata",
                subject_is_minor=False)
    base.update(kw)
    return BirthInput(**base)


def delhi(**kw):
    base = dict(name="t", date="1985-11-02", time="03:10", time_certainty="exact",
                place_name="Delhi", latitude=28.6139, longitude=77.2090, tz_name="Asia/Kolkata",
                subject_is_minor=False)
    base.update(kw)
    return BirthInput(**base)


def test_bhopal_golden_chart(engine):
    k = generate_kundli(bhopal(), engine=engine, today=TODAY)
    f = k.facts
    P = "parashari"
    assert f.value("lagna", "sign", P) == "Kanya"
    assert f.value("lagna", "longitude", P) == pytest.approx(151.90698, abs=0.001)
    assert f.value("Sun", "longitude", P) == pytest.approx(30.54979, abs=0.001)
    assert f.value("Sun", "nakshatra", P) == "Krittika" and f.value("Sun", "pada", P) == 2
    assert f.value("Moon", "sign", P) == "Makara" and f.value("Moon", "house", P) == 5
    assert f.value("Moon", "nakshatra", P) == "Uttara Ashadha" and f.value("Moon", "pada", P) == 2
    assert f.value("Rahu", "longitude", P) == pytest.approx(287.61996, abs=0.001)     # mean node
    assert f.value("Ketu", "longitude", P) == pytest.approx(107.61996, abs=0.001)
    assert f.value("Mercury", "retrograde", P) is True
    assert f.value("vimshottari", "birth_lord", P) == "Sun"
    assert f.value("vimshottari", "birth_balance_years", P) == pytest.approx(3.648, abs=0.002)
    assert not k.withheld and not k.warnings
    assert len(k.birth_hash) == 64


def test_dasha_lookup(engine):
    k = generate_kundli(bhopal(), engine=engine, today=TODAY)
    # Order from the Sun balance: Sun (ends 1994-01-06) -> Moon 10y (-2004-01) -> Mars 7y (-2011-01-06) -> Rahu 18y (-2029-01)
    assert dasha_at(k, datetime(1992, 1, 1, tzinfo=timezone.utc))["maha"] == "Sun"
    assert dasha_at(k, datetime(1998, 1, 1, tzinfo=timezone.utc))["maha"] == "Moon"
    d = dasha_at(k, datetime(2005, 1, 1, tzinfo=timezone.utc))
    assert d["maha"] == "Mars" and d["maha_end"] == "2011-01-06"
    now = dasha_at(k, datetime(2026, 11, 20, tzinfo=timezone.utc))
    assert now["maha"] == "Rahu" and now["maha_end"].startswith("2029-01")


def test_engine_dasha_year_convention_is_what_we_record(engine):
    k = generate_kundli(bhopal(), engine=engine, today=TODAY)
    sun = k.dasha.mahas[0]
    first_sub = sun.sub[0]                                   # Sun/Sun = 6*6/120 years
    assert first_sub.end_jd - first_sub.start_jd == pytest.approx(0.3 * k.dasha_year_days, abs=1e-6)


def test_approximate_time_withholds_instead_of_guessing(engine):
    # Lagna is only 1.9 deg into Kanya; +-15 min moves it ~+-3.7 deg, so the sign is not assertable.
    k = generate_kundli(bhopal(time_certainty="approx_15min"), engine=engine, today=TODAY)
    f = k.facts
    held = {(w.subject, w.predicate) for w in k.withheld}
    assert ("lagna", "sign") in held
    assert ("Moon", "house") in held and ("Sun", "house") in held
    assert f.get("lagna", "sign", "parashari") is None
    # Moon is 1.9 deg into Makara and moves ~0.13 deg in 15 min: the sign is safe
    assert f.value("Moon", "sign", "parashari") == "Makara"
    assert f.value("Moon", "nakshatra", "parashari") == "Uttara Ashadha"
    assert f.get("Moon", "longitude", "parashari") is None          # exact longitude needs exact time
    assert f.value("vimshottari", "birth_lord", "parashari") == "Sun"
    assert f.get("vimshottari", "birth_balance_years", "parashari") is None
    assert k.dasha is None
    with pytest.raises(ValueError):
        dasha_at(k, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_unknown_time_keeps_only_day_stable_facts(engine):
    k = generate_kundli(delhi(time=None, time_certainty="unknown"), engine=engine, today=TODAY)
    f, held = k.facts, {(w.subject, w.predicate) for w in k.withheld}
    assert f.get("lagna", "sign", "parashari") is None
    assert f.value("Sun", "sign", "parashari") == "Tula"            # Sun moves < 1 deg/day
    assert f.value("Mars", "sign", "parashari") == "Kanya"
    assert ("Moon", "sign") in held                                  # Moon is 0.9 deg into Mithuna
    assert all(f.get(g, "house", "parashari") is None for g in ("Sun", "Moon", "Mars"))


def test_node_mode_changes_rahu_and_the_hash(engine):
    mean = generate_kundli(bhopal(), KundliConfig(node_mode="mean"), engine, TODAY)
    true = generate_kundli(bhopal(), KundliConfig(node_mode="true"), engine, TODAY)
    d = abs(mean.facts.value("Rahu", "longitude", "parashari") - true.facts.value("Rahu", "longitude", "parashari"))
    assert 0.1 < d < 1.2          # mean and true node differ by up to ~1.1 deg
    assert mean.birth_hash != true.birth_hash


def test_unvalidated_ayanamsa_is_flagged(engine):
    k = generate_kundli(bhopal(), KundliConfig(ayanamsa="raman"), engine, TODAY)
    assert any("not yet validated" in w for w in k.warnings)


def test_only_whole_sign_is_supported(engine):
    with pytest.raises(ValueError):
        generate_kundli(bhopal(), KundliConfig(house_system="placidus"), engine, TODAY)


class _Shifted:
    """Wraps the real engine but moves the Lagna / Moon to a chosen longitude (test double)."""
    def __init__(self, inner, lagna=None, moon=None):
        self.inner, self.lagna, self.moon = inner, lagna, moon
        self.engine_id = inner.engine_id
        self.dasha_year_days = inner.dasha_year_days
        self.lagna_error_arcsec = inner.lagna_error_arcsec
        self.planet_error_arcsec = inner.planet_error_arcsec

    def natal(self, *a, **kw):
        from dataclasses import replace
        c = self.inner.natal(*a, **kw)
        if self.lagna is not None:
            c = replace(c, lagna_longitude=self.lagna)
        if self.moon is not None:
            planets = dict(c.planets)
            planets["Moon"] = replace(planets["Moon"], longitude=self.moon)
            c = replace(c, planets=planets)
        return c

    def vimshottari(self, *a, **kw):
        return self.inner.vimshottari(*a, **kw)


def test_lagna_inside_engine_error_bound_of_sign_boundary_is_withheld(engine):
    # 10" past the Kanya/Tula boundary (180 deg): inside the 20" Lagna bound -> must not assert a sign
    k = generate_kundli(bhopal(), engine=_Shifted(engine, lagna=180.0 + 10 / 3600), today=TODAY)
    held = {(w.subject, w.predicate) for w in k.withheld}
    assert ("lagna", "sign") in held and k.facts.get("lagna", "sign", "parashari") is None
    assert ("Moon", "house") in held or k.facts.get("Moon", "house", "parashari") is None
    # 60" past: outside the bound -> asserted
    k2 = generate_kundli(bhopal(), engine=_Shifted(engine, lagna=180.0 + 60 / 3600), today=TODAY)
    assert k2.facts.value("lagna", "sign", "parashari") == "Tula"


def test_moon_on_nakshatra_boundary_withholds_dasha(engine):
    # Moon 1" before the end of Uttara Ashadha (293.3333 deg): Venus/Sun/Moon lord ambiguity -> no dasha
    k = generate_kundli(bhopal(), engine=_Shifted(engine, moon=280 + 13 + 1 / 3 - 1 / 3600), today=TODAY)
    held = {(w.subject, w.predicate) for w in k.withheld}
    assert ("vimshottari", "birth_lord") in held and ("Moon", "nakshatra") in held
    assert k.facts.get("vimshottari", "birth_lord", "parashari") is None
