"""v0.5: numerology lens, Hinglish, combined answers."""
import json
import random
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from aipandit import numerology as N
from aipandit import phrasebook as P
from aipandit.composer import bridge_statements, ComposeInput
from aipandit.gates import GateContext, MINOR_BLOCK, check, check_text_only, entities, text_violations
from aipandit.hindi import detect_language
from aipandit.orchestrator import Pandit
from aipandit.planner import classify
from aipandit.reading import Reading, Statement
from aipandit.rulepacks import all_rules, numerology_rules, parashari_rules
from aipandit.rulepacks.hinglish import HINGLISH_ALL
from chartkit import BIRTH, FixedEngine
from test_phase3 import FakeLLM, NOW, llm_json, random_chart

NUM_RULES = numerology_rules()


# ------------------------------------------------------------------------------------------ the numbers
def test_numerology_values_hand_checked():
    assert N.mulank(15) == 6 and N.mulank(29) == 2 and N.mulank(9) == 9 and N.mulank(10) == 1
    assert N.bhagyank(1990, 5, 15) == 3          # 1+9+9+0+5+1+5 = 30 -> 3
    assert N.bhagyank(1985, 11, 2) == 9          # 1+9+8+5+1+1+2 = 27 -> 9
    assert N.personal_year(5, 15, 2026) == 3     # 1+5+0+5+2+0+2+6 = 21 -> 3
    assert N.name_number("Sachin Chaturvedi") == 1
    assert N.name_number("A") is None and N.name_number("") is None and N.name_number("राम") is None
    assert N.name_number("  sa-chin ") == N.name_number("SACHIN")        # case/punctuation insensitive
    assert [N.NUMBER_PLANET[i] for i in range(1, 10)] == ["Sun", "Moon", "Jupiter", "Rahu", "Mercury", "Venus", "Ketu", "Saturn", "Mars"]


def test_digital_root_never_leaves_1_to_9():
    for n in range(1, 5000):
        assert 1 <= N.reduce_digit(n) <= 9
    with pytest.raises(ValueError):
        N.reduce_digit(0)


def test_numerology_facts_exist_without_birth_time():
    p = Pandit(now=lambda: NOW)                    # real engine: with an unknown time the Lagna cannot be asserted
    s = p.start(replace(BIRTH, time=None, time_certainty="unknown", name="Sachin Chaturvedi"))
    assert s.store.value("mulank", "value", "numerology") == 6
    assert s.store.value("name_number", "value", "numerology") == 1
    assert s.store.value("personal_year", "value", "numerology") == 3
    assert s.store.get("lagna", "sign", "parashari") is None           # the kundli part is withheld...
    a = p.ask(s, "mera mulank kya hai")
    assert a.trace["lenses"] and "numerology" in a.trace["lenses"]     # ...numerology still answers
    assert a.gate.passed


def test_no_name_means_no_name_number_and_a_clear_note(request):
    p = Pandit(now=lambda: NOW)
    s = p.start(replace(BIRTH, name=""))
    assert s.store.get("name_number", "value", "numerology") is None
    a = p.ask(s, "what is my name number")
    assert "English letters" in a.text and a.gate.passed


# ------------------------------------------------------------------------------------------ rules
def test_numerology_rules_are_separate_and_never_read_the_kundli():
    assert len(NUM_RULES) == 36
    for r in NUM_RULES:
        assert r.system == "numerology" and r.provenance == "later_tradition" and r.review_status == "draft"
        assert {a.system for a in r.condition.atoms()} == {"numerology"}
        assert not r.adverse
    assert len({r.rule_id for r in all_rules()}) == len(all_rules()) == 110


def test_exactly_one_rule_per_family_fires_for_any_date():
    from aipandit.inference import infer
    from aipandit.fact_ir import FactStore
    d = date(1950, 1, 1)
    while d <= date(2025, 12, 31):
        st = N.enrich(FactStore(birth_hash="x").freeze(), d.isoformat(), "Anil Kumar", datetime(2026, 11, 20, tzinfo=timezone.utc))
        fam = {}
        for f in infer(st, NUM_RULES).firings:
            fam[f.rule_id.split(".")[1].rsplit("_", 1)[0]] = fam.get(f.rule_id.split(".")[1].rsplit("_", 1)[0], 0) + 1
        assert fam == {"mulank": 1, "bhagyank": 1, "name": 1, "year": 1}, (d, fam)
        d += timedelta(days=37)


def test_rule_frequency_matches_declared_moderate_band():
    """Mulank/Bhagyank rules are 'moderate' (5-25%): with 9 numbers each is ~1/9 = 11%. Verify over every date 1950-2025."""
    from collections import Counter
    c, tot = Counter(), 0
    d = date(1950, 1, 1)
    while d <= date(2025, 12, 31):
        c[("m", N.mulank(d.day))] += 1
        c[("b", N.bhagyank(d.year, d.month, d.day))] += 1
        tot += 1
        d += timedelta(days=1)
    for k, n in c.items():
        assert 0.05 <= n / tot <= 0.25, (k, n / tot)


# ------------------------------------------------------------------------------------------ Hinglish wording
def test_every_rule_has_hinglish_wording_with_same_chart_entities_and_no_safety_hits():
    for r in all_rules():
        hg = HINGLISH_ALL[r.rule_id]
        assert text_violations(hg) == [], (r.rule_id, text_violations(hg))
        en_e, hg_e = entities(r.interpretation), entities(hg)
        keep = lambda s: {x for x in s if x.split(":")[0] in ("graha", "sign", "yoga", "house", "year", "nakshatra", "degree")}
        assert keep(en_e) == keep(hg_e), (r.rule_id, sorted(en_e ^ hg_e))
        if MINOR_BLOCK.search(hg):                                     # a minor must never see wording the English filter would hide
            assert MINOR_BLOCK.search(r.interpretation), r.rule_id
        assert len(hg) < 700


def test_hinglish_and_english_fixed_sentences_cover_each_other():
    en, hg, hi = P.bundle("en"), P.bundle("hg"), P.bundle("hi")
    for name in ("INTRO_OVERVIEW", "INTRO_COMBINED", "INTRO_NUMEROLOGY", "INTRO_DASHA", "INTRO_DECLINED_ONLY", "INVITE",
                 "CAVEAT_TENDENCY", "CAVEAT_PROVISIONAL", "CAVEAT_NUMEROLOGY", "CAVEAT_NONAME", "CAVEAT_TIME", "CAVEAT_TIMING",
                 "CAVEAT_NOREADINGS", "CAVEAT_NODASHA", "CAVEAT_UNDETERMINED", "CRISIS", "DEATH", "SAFE_MINIMAL", "NEED_BIRTH"):
        for mod in (en, hg, hi):
            assert P.is_system_text(getattr(mod, name)), (mod.__name__, name)
    for mod in (hg, hi):
        for t in mod.all_fixed():
            assert not entities(t), (mod.__name__, t[:60], entities(t))        # framing/caveat text names no chart entity
    assert "14416" in hg.CRISIS and "1800-599-0019" in hg.CRISIS
    assert hg.CAVEAT_TIME and "janm samay" in hg.CAVEAT_TIME


@pytest.mark.parametrize("q,lang", [
    ("meri shaadi kab hogi?", "hg"), ("mera career kaisa rahega", "hg"), ("kya mera mulank achha hai", "hg"),
    ("Tell me about my career", "en"), ("what is my dasha", "en"), ("मेरी कुंडली बताइए", "hi"), ("", "en")])
def test_language_detection(q, lang):
    assert detect_language(q) == lang


def test_hinglish_hard_stops_and_declines():
    assert classify("mujhe jeene ka mann nahi hai").kind == "crisis"
    assert classify("zindagi khatam karni hai").kind == "crisis"
    assert classify("kitna jeeunga main").kind == "death"
    assert classify("kya mujhe bimari hogi").declined == ("medical",)
    assert classify("share bazaar mein nivesh karun").declined == ("financial",)


def test_hinglish_safety_vocabulary():
    for t, code in [("aap ko bahut paisa milega", "future_you"), ("yeh rog badhega", "medical"), ("ratna pehno", "remedy_sales"),
                    ("yeh pakka hai", "guarantee"), ("jadu tona hai", "fear_curse"), ("maut ka yog", "death_lifespan"),
                    ("share bazaar mein nivesh karein", "financial_advice")]:
        assert code in text_violations(t), (t, code, text_violations(t))
    assert text_violations("This is a challenge, not an omega") == []           # -enge / -ega words in plain English are fine
    assert {"house:2", "house:7"} <= entities("Chandra se 2nd bhaav aur saatve bhaav mein Mangal")


# ------------------------------------------------------------------------------------------ combined answers
@pytest.fixture(scope="module")
def pandit():
    return Pandit(now=lambda: NOW)


@pytest.fixture(scope="module")
def session(pandit):
    return pandit.start(replace(BIRTH, name="Sachin Chaturvedi"))


def test_overview_has_both_lenses_labelled_and_bridge_note(pandit, session):
    a = pandit.ask(session, "tell me about my kundli and numerology")
    assert a.gate.passed and a.trace["composer"] == "template"
    assert {"kundli", "numerology", "both"} <= set(a.trace["lenses"])
    assert "**Kundli:**" in a.text and "**Numerology:**" in a.text and "**Both lenses:**" in a.text
    assert "Mulank 6" in a.text and "Venus" in a.text
    assert "no classical Vedic text" in a.text                           # the numerology honesty note is always there
    assert len(a.reading.of_kind("reading")) <= 6                         # total reading cap unchanged
    for st in a.reading.of_kind("reading"):                               # a statement never blends the systems
        assert len({r.split(".")[0] for r in st.rule_ids}) == 1


def test_numerology_only_question_uses_only_numerology_rules(pandit, session):
    a = pandit.ask(session, "what is my mulank and bhagyank")
    assert a.gate.passed
    assert all(r.startswith("numerology.") for r in a.trace["selected"]) and len(a.trace["selected"]) == 4
    assert set(a.trace["lenses"]) <= {"numerology", "both"}


def test_topic_question_mixes_lenses_and_keeps_numerology_small(pandit, session):
    a = pandit.ask(session, "my career")
    assert a.gate.passed
    n_num = sum(r.startswith("numerology.") for r in a.trace["selected"])
    assert 1 <= n_num <= 3 and len(a.trace["selected"]) <= 6


def test_hinglish_question_gets_hinglish_answer_without_any_llm(pandit, session):
    for q in ("mera career kaisa rahega", "kundli aur numerology batao", "mera mulank kya hai"):
        a = pandit.ask(session, q)
        assert a.trace["lang"] == "hg" and a.trace["composer"] == "template" and a.gate.passed, (q, a.trace["violations"])
        assert "Parampara se" in a.text or "mana jata hai" in a.text
        assert "Basis:" not in a.text and "Aadhaar:" in a.text
    assert "bhavishyavani nahi" in pandit.ask(session, "mera career kaisa rahega").text


def test_explicit_language_overrides_detection(pandit, session):
    assert pandit.ask(session, "my career", lang="hg").trace["lang"] == "hg"
    assert pandit.ask(session, "mera career", lang="en").trace["lang"] == "en"


def test_unknown_birth_time_still_gets_numerology_reading_and_says_so(pandit):
    s = pandit.start(replace(BIRTH, time=None, time_certainty="unknown", name="Anil Kumar"))
    a = pandit.ask(s, "tell me about my personality")
    assert a.gate.passed and any(r.startswith("numerology.") for r in a.trace["selected"])
    assert "birth time" in a.text.lower()


def test_minor_sees_no_marriage_or_adverse_in_any_lens_or_language(pandit):
    s = pandit.start(replace(BIRTH, date="2012-05-15", subject_is_minor=True, guardian_consent=True, name="Riya Sharma"))
    for q in ("tell me about my kundli and numerology", "meri shaadi kab hogi?", "mera mulank kya hai", "my personality",
              "tell me about my family", "kundli batao", "meri love life kaisi hai"):
        a = pandit.ask(s, q)
        assert a.gate.passed, (q, a.gate.codes())
        for st in a.reading.statements:                      # system sentences may name the topic they decline; wording must not
            if st.kind in ("reading", "fact"):
                assert not MINOR_BLOCK.search(st.text), (q, st.text)
        for rid in a.trace["selected"]:
            assert "marriage" not in next(r for r in all_rules() if r.rule_id == rid).scope


def test_bridge_notes_only_for_real_overlaps_and_are_gate_valid():
    from aipandit.jyotish import GRAHAS
    rnd = random.Random(5)
    seen = {"dasha": 0, "dignity": 0, "none": 0}
    for _ in range(40):
        lagna, lons = random_chart(rnd)
        p = Pandit(engine=FixedEngine(lagna, lons), now=lambda: NOW)
        s = p.start(replace(BIRTH, date=f"19{rnd.randint(50, 99)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}", name="Test Person"))
        a = p.ask(s, "tell me about my kundli and numerology")
        assert a.gate.passed, a.gate.codes()
        bridges = [x for x in a.reading.statements if x.lens == "both"]
        for b in bridges:
            planet_fact = next(f for f in b.fact_ids if f.startswith("numerology:"))
            planet = s.store.value(planet_fact.split(":")[1], "planet", "numerology")
            assert planet in b.text
            other = next(f for f in b.fact_ids if f.startswith("parashari:"))
            if other.endswith("dignity"):
                assert s.store.value(planet, "dignity", "parashari") in ("exalted", "own", "debilitated")
                seen["dignity"] += 1
            else:
                assert s.store.value("dasha", other.split(":")[-1], "parashari") == planet
                seen["dasha"] += 1
        seen["none"] += not bridges
    assert seen["none"] > 0 and (seen["dasha"] + seen["dignity"]) > 0, seen


def test_gate_rejects_a_statement_that_blends_two_systems():
    p = Pandit(now=lambda: NOW)
    s = p.start(replace(BIRTH, name="Sachin Chaturvedi"))
    a = p.ask(s, "tell me about my kundli and numerology")
    kr = next(r for r in a.trace["selected"] if r.startswith("parashari."))
    nr = next(r for r in a.trace["selected"] if r.startswith("numerology."))
    ctx = GateContext({f.rule_id: f for f in s.inference.firings if f.rule_id in (kr, nr)}, s.store)
    bad = Reading([Statement("Venus themes and Mulank 6 agree.", "reading", rule_ids=(kr, nr))])
    assert "mixed_systems" in check(bad, ctx).codes()


# ------------------------------------------------------------------------------------------ LLM path with the new lenses
def test_llm_path_hinglish_and_lens_tagging():
    base = Pandit(now=lambda: NOW)
    s = base.start(replace(BIRTH, name="Sachin Chaturvedi"))
    a0 = base.ask(s, "mera career kaisa rahega")
    num = next(r for r in a0.trace["selected"] if r.startswith("numerology."))
    kun = next(r for r in a0.trace["selected"] if r.startswith("parashari."))
    good = llm_json([{"text": "Aapke Bhagyank 3 ka jhukaav sikhane aur margdarshan ki taraf mana jata hai, Guru se juda.", "cites": [num]}])
    p = Pandit(llm=FakeLLM(good), now=lambda: NOW)
    p.llm.client.calls = 0
    a = p.ask(s, "mera career kaisa rahega")
    # the LLM answer covers only one cited rule; the other selected rules are simply not narrated, which is allowed.
    assert a.trace["lang"] == "hg" and a.gate.passed
    assert any(x.lens == "numerology" for x in a.reading.statements if x.kind == "reading")
    mixed = llm_json([{"text": "Dono milkar kehte hain.", "cites": [num, kun]}])
    a2 = Pandit(llm=FakeLLM(mixed), now=lambda: NOW).ask(s, "mera career kaisa rahega")
    assert a2.trace["fallback"] is True and a2.trace["composer"] == "template"
    assert any("mixed_systems" in v for v in a2.trace["violations"])


# ------------------------------------------------------------------------------------------ property test
HG_QUESTIONS = ["namaste", "mera kundli aur numerology batao", "mera career kaisa rahega", "meri shaadi kab hogi", "mera mulank kya hai",
                "mera bhagyank aur naam ank", "kya mujhe bimari hogi", "kab marunga", "paisa kaisa rahega", "mera swabhav kaisa hai",
                "which year will I get promotion", "numerology for my career", "my lucky number", "dasha kya chal rahi hai"]


@pytest.mark.parametrize("variant", ["adult", "minor", "unsure_time", "no_name"])
def test_property_combined_answers_always_pass_the_gates(variant):
    rnd = random.Random(20261122)
    kw = {"adult": {}, "minor": {"subject_is_minor": True, "guardian_consent": True},
          "unsure_time": {"time_certainty": "approx_15min"}, "no_name": {"name": ""}}[variant]
    for i in range(40):
        lagna, lons = random_chart(rnd)
        date_s = f"{rnd.randint(1951, 2020)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"
        birth = replace(BIRTH, date=date_s, name=kw.get("name", "Asha Verma"), **{k: v for k, v in kw.items() if k != "name"})
        p = Pandit(engine=FixedEngine(lagna, lons), now=lambda: NOW)
        s = p.start(birth)
        for q in HG_QUESTIONS:
            a = p.ask(s, q)
            assert a.trace["composer"] in ("template", "crisis", "death"), (variant, q, a.trace["violations"])
            assert a.gate.passed
            assert len(a.text.split()) < 900
