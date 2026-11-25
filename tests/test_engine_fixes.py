"""Regression tests for the Nov-2026 engine accuracy review. Pure: no ephemeris, no network."""
import itertools

import pytest

from aipandit import ashtakoota, doshas, gochara_live, gates, hindi, yogas
from aipandit import kb_core, v09_engine
from aipandit.jyotish import KARANA_FIXED, KARANA_MOVABLE, SIGNS, karana_name, sign_name


# ---- Karana: 60 per lunar month = Kimstughna, 7 movable x 8, then Shakuni / Chatushpada / Naga -----------------
def test_karana_first_half_of_shukla_pratipada_is_kimstughna():
    assert karana_name(0.0) == "Kimstughna" and karana_name(5.99) == "Kimstughna"


def test_karana_movable_sequence_starts_after_kimstughna():
    assert [karana_name(6.0 * k + 1) for k in range(1, 8)] == list(KARANA_MOVABLE)
    assert karana_name(6.0 * 8 + 1) == "Bava"          # the cycle restarts


def test_karana_last_three_are_fixed_and_vishti_positions_are_classical():
    assert [karana_name(6.0 * k + 1) for k in (57, 58, 59)] == list(KARANA_FIXED)
    # Bhadra (Vishti): Shukla Chaturthi 2nd half, Ashtami 1st half, Ekadashi 2nd half, Purnima 1st half
    vishti = [k for k in range(60) if karana_name(6.0 * k + 1) == "Vishti"]
    assert vishti == [7, 14, 21, 28, 35, 42, 49, 56]
    assert vishti[0] == 2 * 3 + 1 and vishti[1] == 2 * 7          # Chaturthi (tithi 4) 2nd half, Ashtami (tithi 8) 1st half


def test_karana_wraps_negative_and_over_360():
    assert karana_name(-0.5) == karana_name(359.5) == "Naga"
    assert karana_name(360.0 + 7.0) == karana_name(7.0)


# ---- one spelling for every sign, everywhere (Scorpio used to be 'Vrischika' in some modules, 'Vrishchika' in others) ---
@pytest.mark.parametrize("module_signs", [
    ashtakoota.RASHIS, doshas.RASHIS, yogas.RASHIS, gochara_live.RASHIS, v09_engine.RASHIS,
])
def test_all_modules_spell_signs_like_the_kundli_engine(module_signs):
    assert tuple(module_signs) == tuple(SIGNS)


def test_name_tables_are_keyed_by_the_same_signs():
    assert set(hindi.SIGN_HI) == set(SIGNS) and set(hindi.SIGN_DEV) == set(SIGNS)
    assert set(gates.SIGN_FORMS) == set(SIGNS)
    assert {row[0] for row in kb_core.SIGNS} == set(SIGNS)
    assert set(v09_engine.RASHI_META) == set(SIGNS)


def test_sign_name_of_scorpio_longitudes():
    assert sign_name(210.0) == sign_name(239.99) == "Vrishchika"


def test_scorpio_placements_flow_through_the_rule_modules():
    chart = {"lagna": "Mesha", "moon": {"sign": "Vrishchika"},
             "planets": {"Mars": {"sign": "Vrishchika", "house": 8}, "Moon": {"sign": "Vrishchika", "house": 8}}}
    assert doshas.manglik(chart)["status"] == "softened"              # Mars in its own sign, 8th from lagna and Moon
    got = ashtakoota.compute({"rashi": "Vrishchika", "nakshatra": "Anuradha"}, {"rashi": "Tula", "nakshatra": "Swati"})
    assert got["ok"] is True
    reading = gochara_live.reading_for_moon_sign("Vrishchika", {"Saturn": {"sign": "Vrishchika"}, "Moon": {"sign": "Dhanu"}})
    assert {f["planet"]: f["house"] for f in reading["facts"]} == {"Saturn": 1, "Moon": 2}
    assert reading["sade_sati"] is True


# ---- legacy /api/v09/compatibility now uses the exact Ashtakoota: no 42-98 clamp, no placeholder signs -------------
class _Store:
    def __init__(self, sign, nak, pada=2):
        self._v = {("Moon", "sign"): sign, ("Moon", "nakshatra"): nak, ("Moon", "pada"): pada}

    def value(self, subject, predicate, system=None):
        return self._v.get((subject, predicate))


def _lowest_scoring_pair():
    best = None
    for (s1, n1), (s2, n2) in itertools.product(
            [(r, n) for r in ashtakoota.RASHIS[:4] for n in ashtakoota.NAK_NAMES[:9]], repeat=2):
        r = ashtakoota.compute({"rashi": s1, "nakshatra": n1}, {"rashi": s2, "nakshatra": n2})
        if best is None or r["total"] < best[0]:
            best = (r["total"], (s1, n1), (s2, n2))
    return best


def test_v09_compatibility_is_not_clamped_and_matches_exact_ashtakoota(monkeypatch):
    total, (s1, n1), (s2, n2) = _lowest_scoring_pair()
    assert total / 36 * 100 < 42                                       # a genuinely poor match exists
    stores = iter([_Store(s1, n1), _Store(s2, n2)])
    monkeypatch.setattr(v09_engine, "build_astrobrain_store", lambda b: (None, next(stores)))
    monkeypatch.setattr(v09_engine, "_to_birth_input", lambda p: type("B", (), {"name": p["name"]})())
    out = v09_engine.compute_compatibility({"name": "A"}, {"name": "B"})
    assert out["ok"] and out["total_points"] == total
    assert out["percentage"] == round(total / 36 * 100) and out["percentage"] < 42


def test_v09_compatibility_refuses_instead_of_inventing_a_moon(monkeypatch):
    monkeypatch.setattr(v09_engine, "build_astrobrain_store", lambda b: (None, _Store(None, None)))
    monkeypatch.setattr(v09_engine, "_to_birth_input", lambda p: type("B", (), {"name": p["name"]})())
    out = v09_engine.compute_compatibility({"name": "A"}, {"name": "B"})
    assert out["ok"] is False and "Moon" in out["error"]


# ---- calculator: real pada, and no invented Moon sign when it is withheld -------------------------------------------
def _patch_calc(monkeypatch, *, rashi, nak, lagna="Mesha", pada=3):
    monkeypatch.setattr(v09_engine, "summarize_profile", lambda p: {"rashi": rashi, "nakshatra": nak, "lagna": lagna,
                                                                    "mahadasha": "Venus", "antardasha": "Sun", "mulank": 1, "bhagyank": 1})
    monkeypatch.setattr(v09_engine, "_to_birth_input", lambda p: type("B", (), {"place_name": "Bhopal"})())
    monkeypatch.setattr(v09_engine, "build_astrobrain_store", lambda b: (None, _Store(rashi, nak, pada)))
    sky = {g: {"sign": "Meena", "degree": 1.0, "retrograde": False} for g in v09_engine.GRAHAS}
    monkeypatch.setattr(v09_engine, "compute_panchang", lambda *a, **k: {"sky_planets": sky})


def test_nakshatra_calculator_shows_the_charts_own_pada(monkeypatch):
    for pada in (1, 2, 3, 4):
        _patch_calc(monkeypatch, rashi="Vrishchika", nak="Anuradha", pada=pada)
        out = v09_engine.run_calculator("nakshatra", {})
        assert out["ok"] and out["headline"] == f"Anuradha - Pada {pada}"


def test_calculator_refuses_when_moon_is_withheld(monkeypatch):
    _patch_calc(monkeypatch, rashi="Withheld", nak="Withheld")
    for kind in ("moon", "nakshatra", "sade_sati"):
        out = v09_engine.run_calculator(kind, {})
        assert out["ok"] is False and "error" in out


def test_ascendant_calculator_never_reports_the_moon_sign_as_lagna(monkeypatch):
    _patch_calc(monkeypatch, rashi="Karka", nak="Pushya", lagna="Withheld (uncertain birth time)")
    out = v09_engine.run_calculator("ascendant", {})
    assert out["ok"] is False and "birth time" in out["error"]
