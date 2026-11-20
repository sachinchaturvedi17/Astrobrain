"""Kundli generator: BirthInput -> FactStore (observations only, no interpretation).

Uncertain birth time is handled by a stability test, not by guessing: the chart is
recomputed at the edges of the uncertainty window and a fact is asserted only if
it is identical at every sample. Anything else is recorded as *withheld* with a
reason, so downstream rules see UNKNOWN rather than a wrong value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from .engines.base import AstronomyEngine, DashaResult, RawChart
from .engines.vedaksha_engine import VALIDATED_AYANAMSAS
from .fact_ir import Fact, FactStore
from .intake import (BirthInput, ResolvedBirth, birth_hash, jd_to_utc,
                     julian_day_ut, resolve_birth)
from .jyotish import (GRAHAS, SIGNS, VIMSHOTTARI_YEARS, nakshatra_of, norm360,
                      sign_index, whole_sign_house)


@dataclass(frozen=True)
class KundliConfig:
    ayanamsa: str = "lahiri"
    node_mode: str = "mean"          # "mean" | "true" - they differ by up to ~1.1 deg
    house_system: str = "whole_sign"


@dataclass(frozen=True)
class Withheld:
    subject: str
    predicate: str
    reason: str


@dataclass
class Kundli:
    birth: ResolvedBirth
    config: KundliConfig
    birth_hash: str
    facts: FactStore
    raw: RawChart
    dasha: Optional[DashaResult]
    withheld: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    dasha_year_days: float = 365.25


def generate_kundli(b: BirthInput, config: Optional[KundliConfig] = None,
                    engine: Optional[AstronomyEngine] = None,
                    today: Optional[date] = None) -> Kundli:
    cfg = config or KundliConfig()
    if cfg.house_system != "whole_sign":
        raise ValueError("v0.1 supports whole_sign only (Placidus/KP cusps are not validated)")
    if engine is None:
        from .engines.vedaksha_engine import VedakshaEngine
        engine = VedakshaEngine()

    rb = resolve_birth(b, today)
    kw = dict(ayanamsa=cfg.ayanamsa, node_mode=cfg.node_mode)
    chart = engine.natal(rb.jd_ut, rb.latitude, rb.longitude, **kw)

    w_min = rb.window_minutes
    samples = [chart]
    if w_min:
        half = w_min / 1440.0
        samples.append(engine.natal(rb.jd_ut - half, rb.latitude, rb.longitude, **kw))
        samples.append(engine.natal(rb.jd_ut + half, rb.latitude, rb.longitude, **kw))

    def stable(fn) -> bool:
        base = fn(chart)
        return all(fn(s) == base for s in samples[1:])

    bh = birth_hash(rb, ayanamsa=cfg.ayanamsa, node_mode=cfg.node_mode,
                    house_system=cfg.house_system, engine_id=chart.engine_id)
    store = FactStore(birth_hash=bh)
    withheld: list = []
    deriv = f"{chart.engine_id}|{cfg.house_system}|" + ("exact" if not w_min else f"stable+-{w_min}min")

    def put(subject, predicate, value, system="parashari", derivation=deriv):
        store.add(Fact(subject, predicate, value, system, 1.0, derivation))

    def hold(subject, predicate, reason=None):
        withheld.append(Withheld(subject, predicate,
                                 reason or f"changes within +/-{w_min} min of the stated birth time"))

    # --- session facts (configuration, so rules and the gate can cite them) ---
    put("chart", "ayanamsa", cfg.ayanamsa, "session")
    put("chart", "node_mode", cfg.node_mode, "session")
    put("chart", "house_system", cfg.house_system, "session")
    put("chart", "time_certainty", rb.time_certainty, "session")
    put("chart", "dasha_year_days", engine.dasha_year_days, "session")
    put("chart", "birth_utc", rb.utc.isoformat(timespec="seconds"), "session")

    # Two independent reasons a value may not be assertable, both handled the same way
    # (recompute at the edges, assert only if unchanged):
    #   1. birth-time uncertainty  -> sample the chart at +-window
    #   2. engine precision        -> jitter longitudes by the engine's measured error bound
    lag_j = getattr(engine, "lagna_error_arcsec", 0.0) / 3600.0
    pl_j = getattr(engine, "planet_error_arcsec", 0.0) / 3600.0

    def stable_over(fn, g=None, use_lag=True):
        """fn(lagna_lon, planet_lon) must give one value across all samples and jitters."""
        outs = set()
        for s in samples:
            l0 = s.lagna_longitude
            p0 = s.planets[g].longitude if g else 0.0
            for dl in ((-lag_j, 0.0, lag_j) if use_lag else (0.0,)):
                for dp in ((-pl_j, 0.0, pl_j) if g else (0.0,)):
                    outs.add(fn(norm360(l0 + dl), norm360(p0 + dp)))
        return len(outs) == 1

    why = (f"changes within +/-{w_min} min of the stated birth time, or lies within the engine's "
           f"error bound of a boundary" if w_min else
           "lies within the engine's measured error bound of a sign/nakshatra boundary")

    # --- lagna ---
    lag = chart.lagna_longitude
    if not w_min:
        put("lagna", "longitude", lag)
    else:
        hold("lagna", "longitude", "exact longitude needs an exact birth time")
    for pred, fn, val in (
        ("sign", lambda l, p: SIGNS[sign_index(l)], SIGNS[sign_index(lag)]),
        ("sign_index", lambda l, p: sign_index(l), sign_index(lag)),
        ("nakshatra", lambda l, p: nakshatra_of(l).name, nakshatra_of(lag).name),
        ("pada", lambda l, p: nakshatra_of(l).pada, nakshatra_of(lag).pada),
    ):
        if stable_over(fn):
            put("lagna", pred, val)
        else:
            hold("lagna", pred, why)

    # --- grahas ---
    for g in GRAHAS:
        p = chart.planets[g]
        npos = nakshatra_of(p.longitude)
        if not w_min:
            put(g, "longitude", p.longitude)
        else:
            hold(g, "longitude", "exact longitude needs an exact birth time")
        for pred, fn, val in (
            ("sign", lambda l, x: SIGNS[sign_index(x)], SIGNS[sign_index(p.longitude)]),
            ("sign_index", lambda l, x: sign_index(x), sign_index(p.longitude)),
            ("nakshatra", lambda l, x: nakshatra_of(x).name, npos.name),
            ("pada", lambda l, x: nakshatra_of(x).pada, npos.pada),
        ):
            if stable_over(fn, g, use_lag=False):
                put(g, pred, val)
            else:
                hold(g, pred, why)
        # retrograde: a motion state, only time-sensitive
        if stable(lambda c, g=g: c.planets[g].retrograde):
            put(g, "retrograde", p.retrograde)
        else:
            hold(g, "retrograde")
        # house depends on both the lagna sign and the planet's sign
        if stable_over(lambda l, x: whole_sign_house(x, l), g):
            put(g, "house", whole_sign_house(p.longitude, lag))
        else:
            hold(g, "house", why)

    # --- Vimshottari dasha (Parashari) ---
    moon_lon = chart.planets["Moon"].longitude
    dasha: Optional[DashaResult] = None
    birth_lord = nakshatra_of(moon_lon).lord
    moon_ok = stable_over(lambda l, x: nakshatra_of(x).lord, "Moon", use_lag=False)
    if not w_min and not moon_ok:
        for pred in ("birth_lord", "birth_balance_years", "maha_sequence"):
            hold("vimshottari", pred, "Moon lies within the engine's error bound of a nakshatra boundary")
    elif not w_min:
        dasha = engine.vimshottari(rb.jd_ut, moon_lon, depth=2)
        put("vimshottari", "birth_lord", birth_lord)
        put("vimshottari", "birth_balance_years",
            round(dasha.initial_balance_fraction * VIMSHOTTARI_YEARS[birth_lord], 6))
        put("vimshottari", "maha_sequence", [
            {"lord": m.lord,
             "start": jd_to_utc(m.start_jd).isoformat(timespec="seconds"),
             "end": jd_to_utc(m.end_jd).isoformat(timespec="seconds")}
            for m in dasha.mahas
        ])
    else:
        if stable(lambda c: nakshatra_of(c.planets["Moon"].longitude).lord):
            put("vimshottari", "birth_lord", birth_lord)
        else:
            hold("vimshottari", "birth_lord")
        hold("vimshottari", "birth_balance_years", "dasha balance needs an exact birth time")
        hold("vimshottari", "maha_sequence", "dasha dates need an exact birth time")

    warnings = list(rb.warnings)
    if cfg.ayanamsa not in VALIDATED_AYANAMSAS:
        warnings.append(f"ayanamsa {cfg.ayanamsa!r} is not yet validated against an external reference")
    if w_min:
        warnings.append(f"birth time is {rb.time_certainty}: facts that change inside the window were withheld")

    store.freeze()
    return Kundli(rb, cfg, bh, store, chart, dasha, withheld, warnings, engine.dasha_year_days)


def dasha_at(k: Kundli, when: datetime) -> dict:
    """Running maha/antar dasha at `when`. Needs an exact birth time."""
    if k.dasha is None:
        raise ValueError("dasha dates are withheld for uncertain birth times")
    jd = julian_day_ut(when)
    for m in k.dasha.mahas:
        if m.start_jd <= jd < m.end_jd:
            antar = next((a for a in m.sub if a.start_jd <= jd < a.end_jd), None)
            fmt = lambda x: jd_to_utc(x).date().isoformat()
            return {
                "maha": m.lord, "maha_end": fmt(m.end_jd),
                "antar": antar.lord if antar else None,
                "antar_end": fmt(antar.end_jd) if antar else None,
            }
    raise ValueError("date is outside the computed Vimshottari span (120 years from birth)")
