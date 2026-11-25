"""BPHS batch 1 (chapters 11-16, house effects): each rule fires exactly when intended.

Charts are built straight into a fact store (no ephemeris), so these run anywhere.
"""
import types

import pytest

from aipandit.derive import enrich
from aipandit.fact_ir import Fact, FactStore
from aipandit.inference import infer
from aipandit.jyotish import GRAHAS
from aipandit.rulepacks import all_rules
from aipandit.rulepacks.hinglish import HINGLISH_ALL
from aipandit.rulepacks.parashari_bhavas import RULES

MESHA, VRISHABHA, MITHUNA, KARKA, SIMHA, KANYA, TULA, VRISCHIKA, DHANU, MAKARA, KUMBHA, MEENA = range(12)
pid = lambda s: f"parashari.{s}"


def chart(lagna, signs, with_lagna=True):
    full = {g: MESHA for g in GRAHAS}
    full.update(signs)
    full.setdefault("Ketu", (full["Rahu"] + 6) % 12)
    st = FactStore(birth_hash="t")
    for g, s in full.items():
        st.add(Fact(g, "sign_index", s, "parashari", 1.0, "test"))
        st.add(Fact(g, "house", (s - lagna) % 12 + 1, "parashari", 1.0, "test"))
    if with_lagna:
        st.add(Fact("lagna", "sign_index", lagna, "parashari", 1.0, "test"))
    return enrich(types.SimpleNamespace(facts=st.freeze()))


def fired(store):
    return infer(store, RULES).fired_ids()


def test_batch_is_well_formed():
    ids = [r.rule_id for r in RULES]
    assert len(ids) == len(set(ids)) == 21
    assert set(ids) <= {r.rule_id for r in all_rules()}
    for r in RULES:
        assert r.review_status == "draft" and r.provenance == "classical_text"
        assert r.source.chapter in {"12", "13", "14", "15", "16", "24"} and r.source.verse
        assert r.rarity and HINGLISH_ALL[r.rule_id]


def test_benefic_in_lagna():
    assert pid("bhava1.benefic_in_lagna") in fired(chart(MESHA, {"Jupiter": MESHA}))
    assert pid("bhava1.benefic_in_lagna") not in fired(chart(MESHA, {"Jupiter": TULA, "Venus": TULA}))


def test_second_lord_placement():
    # Mesha lagna: the 2nd (Vrishabha) is ruled by Venus
    assert pid("bhava2.lord_dusthana") in fired(chart(MESHA, {"Venus": KANYA}))          # 6th house
    assert pid("bhava2.lord_dusthana") not in fired(chart(MESHA, {"Venus": MESHA}))      # 1st house
    assert pid("bhava2.lord_supportive") in fired(chart(MESHA, {"Venus": MESHA}))
    assert pid("bhava2.lord_supportive") not in fired(chart(MESHA, {"Venus": KANYA}))


def test_second_lord_dignity():
    assert pid("bhava2.lord_dignified") in fired(chart(MESHA, {"Venus": MEENA}))         # exalted
    assert pid("bhava2.lord_dignified") not in fired(chart(MESHA, {"Venus": KANYA}))     # debilitated


def test_lagna_lord_debilitated():
    # Mesha lagna: lord Mars, debilitated in Karka
    assert pid("bhava1.lagna_lord_debilitated") in fired(chart(MESHA, {"Mars": KARKA}))
    assert pid("bhava1.lagna_lord_debilitated") not in fired(chart(MESHA, {"Mars": MAKARA}))


def test_second_and_eleventh_lords():
    # Mesha: lord2 Venus, lord11 Saturn. Venus in kendra, Saturn in trikona (9th = Dhanu)
    assert pid("bhava2.lord2_kendra_lord11_trikona") in fired(chart(MESHA, {"Venus": KARKA, "Saturn": DHANU}))
    assert pid("bhava2.lord2_kendra_lord11_trikona") not in fired(chart(MESHA, {"Venus": KARKA, "Saturn": MITHUNA}))
    # both lords in dusthana and a malefic (Mars) in the 2nd house
    both = {"Venus": KANYA, "Saturn": VRISCHIKA, "Mars": VRISHABHA}
    assert pid("bhava2.lords_2_11_dusthana_malefic_in_2") in fired(chart(MESHA, both))
    assert pid("bhava2.lords_2_11_dusthana_malefic_in_2") not in fired(chart(MESHA, {**both, "Mars": TULA}))


def test_jupiter_ruling_second():
    # Vrischika lagna: the 2nd (Dhanu) is ruled by Jupiter
    assert pid("bhava2.jupiter_ruler_of_2_in_2_or_with_mars") in fired(chart(VRISCHIKA, {"Jupiter": DHANU}))
    assert pid("bhava2.jupiter_ruler_of_2_in_2_or_with_mars") in fired(
        chart(VRISCHIKA, {"Jupiter": KARKA, "Mars": KARKA}))
    assert pid("bhava2.jupiter_ruler_of_2_in_2_or_with_mars") not in fired(chart(VRISCHIKA, {"Jupiter": KARKA}))
    assert pid("bhava2.jupiter_ruler_of_2_in_2_or_with_mars") not in fired(chart(MESHA, {"Jupiter": VRISHABHA}))


def test_third_fourth_fifth():
    assert pid("bhava3.jupiter_or_venus_in_3") in fired(chart(MESHA, {"Venus": MITHUNA}))
    # Mesha: lord4 Moon, lord10 Saturn
    assert pid("bhava4.lord_or_lagna_lord_in_4") in fired(chart(MESHA, {"Moon": KARKA}))
    assert pid("bhava4.lord_or_lagna_lord_in_4") in fired(chart(MESHA, {"Mars": KARKA}))      # lagna lord in 4th
    assert pid("bhava4.lord_or_lagna_lord_in_4") not in fired(chart(MESHA, {"Moon": KANYA, "Mars": KANYA}))
    assert pid("bhava4.lord_dignified") in fired(chart(MESHA, {"Moon": KARKA}))               # own sign
    assert pid("bhava4.lord4_with_lord10_in_kendra_trikona") in fired(
        chart(MESHA, {"Moon": KARKA, "Saturn": KARKA}))
    assert pid("bhava4.lord4_with_lord10_in_kendra_trikona") not in fired(
        chart(MESHA, {"Moon": KANYA, "Saturn": KANYA}))                                       # together, but in the 6th
    # Mesha: lord5 Sun. Supportive in the 9th, or joined by Jupiter, not alone in the 3rd
    assert pid("bhava5.lord_supportive") in fired(chart(MESHA, {"Sun": DHANU}))
    assert pid("bhava5.lord_supportive") in fired(chart(MESHA, {"Sun": MITHUNA, "Jupiter": MITHUNA}))
    assert pid("bhava5.lord_supportive") not in fired(chart(MESHA, {"Sun": MITHUNA, "Jupiter": MEENA}))


def test_education_lords():
    # Mesha lagna: lagna lord Mars; 4th Karka (Moon); 5th Simha (Sun); 9th Dhanu (Jupiter); 10th Makara (Saturn);
    # 11th Kumbha (Saturn); 12th Meena (Jupiter)
    f = lambda signs: fired(chart(MESHA, signs))
    assert pid("edu.lagna_lord_in_1_2_9") in f({"Mars": MESHA}) and pid("edu.lagna_lord_in_1_2_9") in f({"Mars": VRISHABHA})
    assert pid("edu.lagna_lord_in_1_2_9") not in f({"Mars": MITHUNA})
    assert pid("edu.lord4_in_4") in f({"Moon": KARKA}) and pid("edu.lord4_in_5") in f({"Moon": SIMHA})
    assert pid("edu.lord4_in_5") not in f({"Moon": KARKA})
    assert pid("edu.lord5_in_1_4_9_11") in f({"Sun": DHANU}) and pid("edu.lord5_in_1_4_9_11") not in f({"Sun": MITHUNA})
    assert pid("edu.lord9_in_2") in f({"Jupiter": VRISHABHA}) and pid("edu.lord9_in_2") not in f({"Jupiter": MESHA})
    assert pid("edu.lord10_in_1_5") in f({"Saturn": SIMHA}) and pid("edu.lord10_in_1_5") not in f({"Saturn": KARKA})
    assert pid("edu.lord11_in_1_5_11") in f({"Saturn": MESHA})
    assert pid("edu.lord12_in_1_5_7") in f({"Jupiter": SIMHA}) and pid("edu.lord12_in_1_5_7") not in f({"Jupiter": MITHUNA})


def test_education_rules_are_scoped_and_framed_as_tendencies():
    edu = [r for r in RULES if r.rule_id.startswith("parashari.edu.")]
    assert len(edu) == 8 and all("education" in r.scope for r in edu)
    assert [r.rule_id for r in edu if r.adverse] == ["parashari.edu.lord12_in_1_5_7"]
    assert all("Traditionally" in r.interpretation for r in edu)


def test_withheld_lagna_means_no_house_lord_rule_fires():
    st = chart(MESHA, {"Venus": KANYA}, with_lagna=False)
    res = infer(st, RULES)
    lord_rules = {pid(r) for r in ("bhava2.lord_dusthana", "bhava2.lord_supportive", "bhava5.lord_supportive")}
    assert not (lord_rules & res.fired_ids())
