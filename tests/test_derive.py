import pytest

from aipandit.derive import (ASPECT_OFFSETS, DEBIL_SIGN, EXALT_SIGN, OWN_SIGNS, SIGN_LORD,
                             aspects, lord_relation, pair)
from chartkit import (DHANU, KANYA, KARKA, KUMBHA, MAKARA, MEENA, MESHA, MITHUNA, SIMHA, TULA,
                      VRISCHIKA, VRISHABHA, make)


def test_classical_dignity_tables():
    names = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika", "Dhanu",
             "Makara", "Kumbha", "Meena")
    assert {g: names[s] for g, s in EXALT_SIGN.items()} == {
        "Sun": "Mesha", "Moon": "Vrishabha", "Mars": "Makara", "Mercury": "Kanya",
        "Jupiter": "Karka", "Venus": "Meena", "Saturn": "Tula"}
    assert {g: names[s] for g, s in DEBIL_SIGN.items()} == {
        "Sun": "Tula", "Moon": "Vrischika", "Mars": "Karka", "Mercury": "Meena",
        "Jupiter": "Makara", "Venus": "Kanya", "Saturn": "Mesha"}
    assert OWN_SIGNS["Mars"] == (MESHA, VRISCHIKA) and OWN_SIGNS["Saturn"] == (MAKARA, KUMBHA)
    assert OWN_SIGNS["Sun"] == (SIMHA,) and OWN_SIGNS["Moon"] == (KARKA,)
    # every sign has exactly one lord and each of the 7 grahas rules 1 or 2 signs
    assert len(SIGN_LORD) == 12 and sorted(len(v) for v in OWN_SIGNS.values()) == [1, 1, 2, 2, 2, 2, 2]


def test_graha_drishti_geometry():
    # Mars in Mesha: 4th Karka, 7th Tula, 8th Vrischika - not Mithuna (3rd) or Simha (5th)
    assert [aspects("Mars", MESHA, s) for s in (KARKA, TULA, VRISCHIKA)] == [True] * 3
    assert not aspects("Mars", MESHA, MITHUNA) and not aspects("Mars", MESHA, SIMHA)
    # Jupiter in Mesha: 5th Simha, 7th Tula, 9th Dhanu
    assert [aspects("Jupiter", MESHA, s) for s in (SIMHA, TULA, DHANU)] == [True] * 3
    # Saturn in Mesha: 3rd Mithuna, 7th Tula, 10th Makara
    assert [aspects("Saturn", MESHA, s) for s in (MITHUNA, TULA, MAKARA)] == [True] * 3
    # Sun: 7th only; no aspect onto its own sign
    assert aspects("Sun", MESHA, TULA) and not aspects("Sun", MESHA, MESHA) and not aspects("Sun", MESHA, KARKA)
    assert "Rahu" not in ASPECT_OFFSETS and "Ketu" not in ASPECT_OFFSETS


def test_lord_relation_cases():
    assert lord_relation("Mars", "Mars", 0, 7) == "same_planet"
    # Mars in Vrishabha (Venus's sign) and Venus in Mesha (Mars's sign): exchange
    assert lord_relation("Mars", "Venus", VRISHABHA, MESHA) == "exchange"
    assert lord_relation("Sun", "Moon", SIMHA, SIMHA) == "conjunct"
    assert lord_relation("Sun", "Moon", MESHA, TULA) == "mutual_aspect"            # 7th from each other
    assert lord_relation("Mars", "Mercury", MESHA, KARKA) == "one_way_aspect"      # Mars 4th, Mercury no
    assert lord_relation("Sun", "Moon", MESHA, MITHUNA) == "none"


def test_enrich_on_a_hand_built_chart():
    # Kanya Lagna; Mercury exalted in Kanya (house 1); Saturn debilitated in Mesha (house 8)
    k, s = make(KANYA, {"Sun": SIMHA, "Moon": KARKA, "Mars": TULA, "Mercury": KANYA, "Jupiter": DHANU,
                        "Venus": KANYA, "Saturn": MESHA, "Rahu": MITHUNA})
    P = "parashari"
    assert s.value("Mercury", "dignity", P) == "exalted" and s.value("Mercury", "in_own_sign", P) is True
    assert s.value("Saturn", "dignity", P) == "debilitated"
    assert s.value("Moon", "dignity", P) == "own"                       # Moon in Karka
    assert s.value("Venus", "dignity", P) == "debilitated"              # Venus in Kanya
    assert s.value("house1", "lord", P) == "Mercury" and s.value("house5", "lord", P) == "Saturn"
    assert s.value("house5", "lord_house", P) == 8                      # Saturn in Mesha = 8th from Kanya
    assert s.value("Moon", "house_from_sun", P) == 12                   # Sun Simha, Moon Karka
    assert s.value("Mars", "house_from_moon", P) == 4                   # Karka -> Tula
    assert s.value(pair("Mercury", "Venus"), "conjunct", P) is True
    assert s.value("Mars>Saturn", "aspects", P) is True                  # Mars in Tula: Mesha is its 7th
    assert s.value("Mars>Jupiter", "aspects", P) is False               # Dhanu is Mars's 3rd from Tula
    assert s.value("Venus>Mars", "aspects", P) is False
    assert s.value("Saturn>Jupiter", "aspects", P) is False
    assert s.value("Saturn>Moon", "aspects", P) is False                # Karka is Saturn's 4th: no such aspect
    assert s.value("Saturn>Rahu", "aspects", P) is True                 # Mithuna is Saturn's 3rd from Mesha
