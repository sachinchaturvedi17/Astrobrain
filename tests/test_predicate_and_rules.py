import pytest

from aipandit.fact_ir import AmbiguousFact, Fact, FactConflict, FactStore, StoreFrozen
from aipandit.predicate import (And, Eq, Exists, Gte, In, Not, Or, PredicateError,
                                Truth, all_of, any_of, from_dict)
from aipandit.rules import Rule, RuleError, Source, rule_from_dict

SRC = Source(text="BPHS", chapter="34")


def store():
    s = FactStore()
    s.add(Fact("Saturn", "house", 7, "parashari", 1.0, "t"))
    s.add(Fact("Saturn", "house", 3, "lal_kitab", 1.0, "t"))
    s.add(Fact("Moon", "pada", 2, "parashari", 0.8, "t"))
    s.add(Fact("chart", "ayanamsa", "lahiri", "session", 1.0, "t"))
    return s


def test_facts_are_immutable_and_systems_never_blend():
    s = store()
    with pytest.raises(FactConflict):
        s.add(Fact("Saturn", "house", 8, "parashari", 1.0, "t"))
    assert s.value("Saturn", "house", "parashari") == 7
    assert s.value("Saturn", "house", "lal_kitab") == 3
    with pytest.raises(AmbiguousFact):
        s.get("Saturn", "house")
    s.freeze()
    with pytest.raises(StoreFrozen):
        s.add(Fact("Mars", "house", 1, "parashari", 1.0, "t"))


def test_atoms_and_confidence():
    s = store()
    m = Eq("parashari", "Saturn", "house", 7).evaluate(s)
    assert m.matched and m.fact_ids == ("parashari:Saturn:house",)
    assert Eq("parashari", "Saturn", "house", 8).evaluate(s).truth is Truth.FALSE
    assert Gte("parashari", "Moon", "pada", 2).evaluate(s).confidence == 0.8
    assert In("parashari", "Saturn", "house", (1, 4, 7, 10)).evaluate(s).matched


def test_missing_fact_is_unknown_not_false():
    s = store()
    p = Eq("parashari", "Mars", "house", 4)
    assert p.evaluate(s).truth is Truth.UNKNOWN
    # Not() of an unknown stays unknown: no closed-world assumption
    assert Not(p).evaluate(s).truth is Truth.UNKNOWN
    # Kleene logic
    false_p = Eq("parashari", "Saturn", "house", 9)
    assert all_of(p, false_p).evaluate(s).truth is Truth.FALSE
    assert all_of(p, Eq("parashari", "Saturn", "house", 7)).evaluate(s).truth is Truth.UNKNOWN
    assert any_of(p, Eq("parashari", "Saturn", "house", 7)).evaluate(s).truth is Truth.TRUE
    assert any_of(p, false_p).evaluate(s).truth is Truth.UNKNOWN
    assert Exists("parashari", "Mars", "house").evaluate(s).truth is Truth.FALSE


def test_and_takes_min_confidence_and_unions_facts():
    s = store()
    m = all_of(Eq("parashari", "Saturn", "house", 7), Gte("parashari", "Moon", "pada", 1)).evaluate(s)
    assert m.matched and m.confidence == 0.8 and len(m.fact_ids) == 2


def test_numeric_comparison_on_text_fact_is_an_authoring_error():
    with pytest.raises(PredicateError):
        Gte("session", "chart", "ayanamsa", 3).evaluate(store())


def test_predicate_roundtrip():
    p = all_of(Eq("parashari", "Saturn", "house", 7),
               any_of(In("parashari", "Moon", "pada", (1, 2)), Not(Exists("parashari", "Mars", "house"))))
    assert from_dict(p.to_dict()) == p


def _rule(**kw):
    base = dict(rule_id="bphs.test.1", system="parashari",
                condition=Eq("parashari", "Saturn", "house", 7),
                scope=("marriage",), interpretation="Text in our own words.", source=SRC)
    base.update(kw)
    return Rule(**base)


def test_rule_cannot_blend_systems():
    with pytest.raises(RuleError, match="never blended"):
        _rule(condition=all_of(Eq("parashari", "Saturn", "house", 7),
                               Eq("lal_kitab", "Saturn", "house", 3)))
    # session facts are allowed
    _rule(condition=all_of(Eq("parashari", "Saturn", "house", 7),
                           Eq("session", "chart", "ayanamsa", "lahiri")))


def test_concordance_rule_has_no_prose():
    cond = all_of(Eq("parashari", "Saturn", "house", 7), Eq("lal_kitab", "Saturn", "house", 7))
    Rule("conc.1", "concordance", cond, ("marriage",), "", SRC)
    with pytest.raises(RuleError):
        Rule("conc.2", "concordance", cond, ("marriage",), "smooth blended narrative", SRC)


def test_lal_kitab_needs_translation_confidence_and_remedy_needs_licence():
    lk = dict(system="lal_kitab", condition=Eq("lal_kitab", "Saturn", "house", 7))
    with pytest.raises(RuleError, match="translation_confidence"):
        _rule(**lk)
    r = _rule(**lk, translation_confidence=0.7)
    assert r.translation_confidence == 0.7
    with pytest.raises(RuleError, match="licence"):
        _rule(**lk, translation_confidence=0.7, remedy={"item": "x"})
    _rule(**lk, translation_confidence=0.7, remedy={"item": "x"},
          source=Source("LK", "1", licence="licensed:acme-2026"))


def test_rule_json_roundtrip():
    r = _rule(salience_hint=0.4)
    assert rule_from_dict(r.to_dict()) == r
