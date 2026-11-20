"""Hand-built charts proving each rare rule is reachable and fires exactly when intended."""
import pytest

from chartkit import (DHANU, KANYA, KARKA, KUMBHA, MAKARA, MEENA, MESHA, MITHUNA, RULES, SIMHA, TULA,
                      VRISCHIKA, VRISHABHA, fired, make)

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
pid = lambda s: f"parashari.{s}"


def all_in(signs):
    return {g: signs[i % len(signs)] for i, g in enumerate(SEVEN)}


def build_rajju():       return make(MESHA, {**all_in((MESHA, KARKA, TULA, MAKARA)), "Rahu": MITHUNA})[1]
def build_musala():      return make(MESHA, {**all_in((VRISHABHA, SIMHA, VRISCHIKA, KUMBHA)), "Rahu": MITHUNA})[1]
def build_nala():        return make(MESHA, {**all_in((MITHUNA, KANYA, DHANU, MEENA)), "Rahu": MESHA})[1]
def build_daridra_ms():  return make(MESHA, {"Mars": VRISHABHA, "Saturn": VRISHABHA, "Mercury": KARKA})[1]
def build_daridra_sun(): return make(MESHA, {"Sun": VRISHABHA, "Saturn": VRISCHIKA})[1]
def build_kaal_sarp():
    return make(MESHA, lons={"Rahu": 100, "Ketu": 280, "Sun": 120, "Moon": 150, "Mars": 170,
                             "Mercury": 200, "Jupiter": 220, "Venus": 240, "Saturn": 260})[1]
def build_kaal_amrit():
    return make(MESHA, lons={"Rahu": 100, "Ketu": 280, "Sun": 300, "Moon": 320, "Mars": 340,
                             "Mercury": 10, "Jupiter": 30, "Venus": 50, "Saturn": 70})[1]
def build_kemadruma():
    # Moon Simha(house 5); flank signs Karka/Simha/Kanya and kendras Mesha/Karka/Tula/Makara all empty
    return make(MESHA, {"Moon": SIMHA, "Mars": VRISHABHA, "Mercury": MITHUNA, "Jupiter": VRISCHIKA,
                        "Venus": DHANU, "Saturn": KUMBHA, "Sun": MESHA, "Rahu": MESHA})[1]


WITNESS = {
    "nabhasa.rajju": build_rajju, "nabhasa.musala": build_musala, "nabhasa.nala": build_nala,
    "wealth.daridra_mars_saturn_2h": build_daridra_ms, "wealth.daridra_sun_2h_saturn_aspect": build_daridra_sun,
    "dosha.kaal_sarp": build_kaal_sarp, "dosha.kaal_amrit": build_kaal_amrit,
    "yoga.kemadruma": build_kemadruma, "yoga.kemadruma_common": build_kemadruma,
}


@pytest.mark.parametrize("rule", sorted(WITNESS))
def test_witness_fires(rule):
    assert pid(rule) in fired(WITNESS[rule]())


def test_nabhasa_exclusivity():
    assert {r for r in fired(build_rajju()) if "nabhasa" in r} == {pid("nabhasa.rajju")}
    assert {r for r in fired(build_musala()) if "nabhasa" in r} == {pid("nabhasa.musala")}
    assert {r for r in fired(build_nala()) if "nabhasa" in r} == {pid("nabhasa.nala")}


def test_kaal_sarp_directions_are_distinct():
    assert pid("dosha.kaal_amrit") not in fired(build_kaal_sarp())
    assert pid("dosha.kaal_sarp") not in fired(build_kaal_amrit())


def test_mercury_aspect_reverses_daridra_mars_saturn():
    # Mercury in Vrischika aspects Vrishabha (7th): the text's reversal applies
    _, s = make(MESHA, {"Mars": VRISHABHA, "Saturn": VRISHABHA, "Mercury": VRISCHIKA})
    assert pid("wealth.daridra_mars_saturn_2h") not in fired(s)


def test_kemadruma_text_vs_common_variants_differ():
    # Jupiter in Tula: not flanking the Moon (so the common variant fires) but angular from the Lagna
    _, s = make(MESHA, {"Moon": SIMHA, "Mars": VRISHABHA, "Mercury": MITHUNA, "Jupiter": TULA,
                        "Venus": DHANU, "Saturn": KUMBHA, "Sun": MESHA, "Rahu": MESHA})
    f = fired(s)
    assert pid("yoga.kemadruma_common") in f and pid("yoga.kemadruma") not in f
    # A planet in the 2nd from the Moon kills both
    _, s2 = make(MESHA, {"Moon": SIMHA, "Mars": KANYA, "Mercury": MITHUNA, "Jupiter": VRISCHIKA,
                         "Venus": DHANU, "Saturn": KUMBHA, "Sun": MESHA, "Rahu": MESHA})
    f2 = fired(s2)
    assert pid("yoga.kemadruma_common") not in f2 and pid("yoga.sunapha") in f2


def test_mahapurusha_needs_both_kendra_and_dignity():
    # Mars exalted (Makara) in the 4th from Mesha Lagna -> Ruchaka
    assert pid("yoga.ruchaka") in fired(make(MESHA, {"Mars": MAKARA})[1])
    # exalted but in the 3rd (Mithuna? no: Makara is the 10th from Mesha) -> use Kumbha Lagna: Makara = 12th
    assert pid("yoga.ruchaka") not in fired(make(KUMBHA, {"Mars": MAKARA})[1])
    # kendra but neutral sign: Mars in Mithuna, Lagna Mithuna (house 1)
    assert pid("yoga.ruchaka") not in fired(make(MITHUNA, {"Mars": MITHUNA})[1])
    # Mercury in Kanya counts as exalted: Bhadra from Kanya Lagna
    assert pid("yoga.bhadra") in fired(make(KANYA, {"Mercury": KANYA})[1])


def test_yogakaraka_for_the_six_lagnas_only():
    hits = {l for l in range(12) if pid("raja.yogakaraka") in fired(make(l)[1])}
    # Vrishabha, Karka, Simha, Tula, Makara, Kumbha
    assert hits == {VRISHABHA, KARKA, SIMHA, TULA, MAKARA, KUMBHA}
