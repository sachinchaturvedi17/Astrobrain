from datetime import datetime, timezone

from aipandit.derive import enrich
from aipandit.inference import infer
from aipandit.intake import BirthInput
from aipandit.kundli import generate_kundli
from aipandit.rules import Rule, Source
from aipandit.predicate import Eq
from chartkit import BIRTH, RULES, make, KANYA, MESHA

pid = lambda s: f"parashari.{s}"


def test_golden_bhopal_firing_set():
    """Expected set derived by hand from the chart (Kanya Lagna; Venus exalted in 7th; Saturn own in 5th;
    Moon+Saturn+Rahu in Makara; Mars in Kumbha; Jupiter Mithuna; Mercury Mesha) before running the code."""
    store = enrich(generate_kundli(BIRTH))
    res = infer(store, RULES)
    assert res.fired_ids() == {pid(x) for x in (
        "yoga.malavya", "yoga.sunapha", "yoga.vesi", "yoga.vosi", "yoga.ubhayachari",
        "dignity.venus_exalted", "dignity.saturn_own", "lagna_lord.dusthana", "yoga.vipareeta_sarala",
        "yoga.shrapit", "yoga.vish", "dosha.manglik_from_venus",
        # BPHS house-effect batch 1, checked by hand for this chart: lord of the 2nd (Venus) is in the 7th and exalted;
        # lord of the 11th (Moon) is in the 5th; lord of the 5th (Saturn) is in the 5th
        "bhava2.lord_supportive", "bhava2.lord_dignified", "bhava2.lord2_kendra_lord11_trikona",
        "bhava5.lord_supportive",
        # education batch: lord of the 11th (Moon) is in the 5th. The lord of the 12th (Sun, in Vrishabha) is in the
        # 9th, so edu.lord12_in_1_5_7 correctly stays silent
        "edu.lord11_in_1_5_11")}
    assert res.undetermined == []
    assert len(res.firings) + res.not_fired == len(RULES)


def test_firings_carry_real_provenance():
    store = enrich(generate_kundli(BIRTH))
    res = infer(store, RULES)
    mal = next(f for f in res.firings if f.rule_id == pid("yoga.malavya"))
    assert set(mal.fact_ids) == {"parashari:Venus:house", "parashari:Venus:dignity"}
    assert mal.review_status == "definition_checked" and mal.provenance == "classical_text"
    assert mal.source.chapter == "75" and mal.source.edition
    # every cited fact exists in the store and nothing fires without citing something
    for f in res.firings:
        assert f.fact_ids, f.rule_id
        assert all(i in store for i in f.fact_ids), f.rule_id


def test_withheld_facts_make_rules_undetermined_not_false():
    # Delhi 1985, birth time unknown: Lagna, houses and the Moon's sign are withheld
    b = BirthInput(name="t", date="1985-11-02", time=None, time_certainty="unknown", place_name="Delhi",
                   latitude=28.6139, longitude=77.2090, tz_name="Asia/Kolkata", subject_is_minor=False)
    k = generate_kundli(b)
    res = infer(enrich(k), RULES)
    und = {u.rule_id: u for u in res.undetermined}
    # needs the Lagna -> undetermined, and the report names the missing fact
    assert pid("yoga.vipareeta_harsha") in und
    assert "parashari:house6:lord_house" in und[pid("yoga.vipareeta_harsha")].missing
    # needs the Moon's sign -> undetermined
    assert pid("yoga.sunapha") in und
    # kaal sarp needs exact longitudes -> undetermined, never silently 'absent'
    assert pid("dosha.kaal_sarp") in und
    # nothing that depends on a withheld fact is among the firings
    for f in res.firings:
        assert all(i in enrich(k) for i in f.fact_ids)
    assert not any(f.rule_id.startswith(pid("yoga.vipareeta")) for f in res.firings)
    # a rule that only needs day-stable facts can still be decided: Sun and Mars are stable that day
    assert res.firings or res.not_fired


def test_unknown_stays_unknown_through_not_and_or():
    b = BirthInput(name="t", date="1985-11-02", time=None, time_certainty="unknown", place_name="Delhi",
                   latitude=28.6139, longitude=77.2090, tz_name="Asia/Kolkata", subject_is_minor=False)
    s = enrich(generate_kundli(b))
    assert s.get("Moon", "house", "parashari") is None
    assert s.get("house1", "lord", "parashari") is None


def test_status_threshold_and_scope_filters():
    store = enrich(generate_kundli(BIRTH))
    all_res = infer(store, RULES)
    checked = infer(store, RULES, min_status="definition_checked")
    assert checked.out_of_scope == sum(r.review_status == "draft" for r in RULES)
    assert checked.fired_ids() <= all_res.fired_ids()
    assert all(f.review_status != "draft" for f in checked.firings)

    male_only = Rule("parashari.test.m", "parashari", Eq("parashari", "Venus", "house", 7), ("marriage",),
                     "x", Source("T", "1"), gender_scope="male")
    assert infer(store, [male_only]).out_of_scope == 1                       # gender unknown -> skipped
    assert infer(store, [male_only], gender="male").fired_ids() == {"parashari.test.m"}
    assert infer(store, [male_only], gender="female").out_of_scope == 1


def test_by_scope_grouping_and_ordering_is_deterministic():
    store = enrich(generate_kundli(BIRTH))
    a, b = infer(store, RULES), infer(store, RULES)
    assert [f.rule_id for f in a.firings] == [f.rule_id for f in b.firings]
    assert "marriage" in a.by_scope() and "character" in a.by_scope()


def test_dasha_as_of_facts():
    k = generate_kundli(BIRTH)
    s = enrich(k, as_of=datetime(2026, 11, 20, tzinfo=timezone.utc))
    assert s.value("dasha", "maha_lord", "parashari") == "Rahu"
    assert s.value("dasha", "antar_lord", "parashari") == "Moon"
    assert s.value("chart", "as_of", "session") == "2026-11-20"
    assert enrich(k).get("dasha", "maha_lord", "parashari") is None
