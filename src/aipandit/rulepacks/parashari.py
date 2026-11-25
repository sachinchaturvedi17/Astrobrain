"""Seed Parashari rules (v0.1).

Honesty rules for this file:
  * Interpretations are written in our own words as *traditional readings*, never as
    predictions. Adverse readings carry adverse=True so the Safety gate frames them.
  * review_status "definition_checked" is used ONLY where the defining conditions were
    compared with the named chapter of a named edition (see ED below). Everything else is
    "draft", and rules whose primary source is not pinned say so (chapter="unpinned").
  * Each rule declares an expected frequency band (rarity) from an a-priori estimate;
    tests/test_base_rates.py measures it over random charts.
  * Variant choices (e.g. which planets count) are written in `notes` for the auditing astrologer.
"""
from __future__ import annotations

from itertools import combinations

from ..derive import (DUSTHANA, KENDRA, SEVEN, aspect_subject, lord_pair, pair)
from ..predicate import Eq, In, all_of, any_of
from ..rules import UNPINNED, Rule, Source

P = "parashari"
BPHS = "Brihat Parashara Hora Shastra"
ED = ("English ebook of Parashara Hora Sastra, archive.org item 'ParasharaHoraSastra' (translator not "
      "stated). Chapter numbering is that ebook's and differs from other editions (e.g. Sagar). "
      "Verse numbers come from an automated reading - confirm at audit.")
UNP = Source("Traditional usage (primary source not pinned)", UNPINNED)


def bphs(chapter: str, verse: str | None = None) -> Source:
    return Source(BPHS, chapter, verse, edition=ED)


def E(subject, predicate, value):
    return Eq(P, subject, predicate, value)


def I(subject, predicate, values):
    return In(P, subject, predicate, tuple(values))


def ordn(n: int) -> str:
    return f"{n}" + ("th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def hset(exclude):
    return tuple(h for h in range(1, 13) if h not in exclude)


FIVE = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")     # planets that count for Moon/Sun-based yogas
RULES: list[Rule] = []


def R(rule_id, cond, scope, text, source, *, status="draft", prov="later_tradition",
      adverse=False, rarity=None, notes=""):
    RULES.append(Rule(rule_id=f"parashari.{rule_id}", system=P, condition=cond, scope=tuple(scope),
                      interpretation=text, source=source, review_status=status, provenance=prov,
                      adverse=adverse, rarity=rarity, notes=notes))


# ------------------------------------------------------------------ Pancha Mahapurusha
MAHA = (
    ("ruchaka", "Mars", "Mars is strong and angular. Traditionally this is read as courage, a commanding "
     "presence, drive, and distinction in competitive or action-oriented fields."),
    ("bhadra", "Mercury", "Mercury is strong and angular. Traditionally this is read as a sharp, articulate "
     "mind with skill in learning, communication, trade and analysis."),
    ("hamsa", "Jupiter", "Jupiter is strong and angular. Traditionally this is read as wisdom, sound judgement, "
     "an ethical bent, and a respected, advisory or teaching role in life."),
    ("malavya", "Venus", "Venus is strong and angular. Traditionally this is read as refinement, charm, "
     "appreciation of the arts and comforts, and good fortune in close relationships."),
    ("shasha", "Saturn", "Saturn is strong and angular. Traditionally this is read as discipline, endurance, "
     "and authority earned through sustained effort and organisation."),
)
for name, g, text in MAHA:
    R(f"yoga.{name}", all_of(I(g, "house", KENDRA), I(g, "dignity", ("exalted", "own"))),
      ("career", "character"), f"{name.capitalize()} yoga (one of the five 'great person' yogas). {text}",
      bphs("75", "1-2"), status="definition_checked", prov="classical_text", rarity="moderate",
      notes="Text states the condition from the Lagna only (not from the Moon). 'Own or exalted' is "
            "sign-level; Mercury in Kanya counts as exalted. Degree-level strength is not assessed.")

# ------------------------------------------------------------------ Chandra (Moon-based) yogas
sunapha = any_of(*[E(g, "house_from_moon", 2) for g in FIVE])
anapha = any_of(*[E(g, "house_from_moon", 12) for g in FIVE])
CH37 = bphs("37", "7-10")
NOTE_CH = ("Counts Mars, Mercury, Jupiter, Venus, Saturn. Excludes the Sun (per text) and Rahu/Ketu "
           "(standard practice; text wording 'a planet other than the Sun' is ambiguous on the nodes).")
R("yoga.sunapha", sunapha, ("wealth", "mind"),
  "Sunapha yoga: a planet (other than the Sun) stands in the 2nd from the Moon. Traditionally read as "
  "self-earned resources and a capable mind; the effect depends on whether the planet is benefic or malefic.",
  CH37, status="definition_checked", prov="classical_text", rarity="common", notes=NOTE_CH)
R("yoga.anapha", anapha, ("health", "character"),
  "Anapha yoga: a planet (other than the Sun) stands in the 12th from the Moon. Traditionally read as a "
  "composed bearing and good standing; the effect depends on the planet's benefic or malefic nature.",
  CH37, status="definition_checked", prov="classical_text", rarity="common", notes=NOTE_CH)
R("yoga.durudhara", all_of(sunapha, anapha), ("wealth", "character"),
  "Durudhara yoga: planets flank the Moon on both sides (2nd and 12th from it). Traditionally read as "
  "comfort, generosity and a supported life.",
  CH37, status="definition_checked", prov="classical_text", rarity="moderate", notes=NOTE_CH)

kema_core = [I(g, "house_from_moon", hset((1, 2, 12))) for g in FIVE]
R("yoga.kemadruma", all_of(*kema_core, *[I(g, "house", hset(KENDRA)) for g in FIVE + ("Moon",)]),
  ("mind", "wealth"),
  "Kemadruma yoga: the Moon is isolated, with no planet beside or around it and none in an angular house "
  "from the Lagna. Traditionally read as phases of isolation or self-reliance; classical texts also list "
  "several conditions that cancel it.",
  bphs("37", "11-13"), status="definition_checked", prov="classical_text", adverse=True, rarity="uncommon",
  notes=NOTE_CH + " Text-faithful variant: also requires no planet in a kendra from the Lagna (the Moon "
        "itself is included in that check - Moon in a kendra cancels). See kemadruma_common for the looser "
        "modern definition.")
R("yoga.kemadruma_common", all_of(*kema_core), ("mind", "wealth"),
  "Kemadruma yoga (common modern definition): no planet with the Moon or in the 2nd or 12th from it. "
  "Traditionally read as phases of isolation or self-reliance; cancellation conditions apply.",
  UNP, prov="later_tradition", adverse=True, rarity="common",
  notes="Looser variant used by most modern software: omits the kendra-from-Lagna clause. Kept separate "
        "so the two definitions are never confused; variance between sources is itself information. "
        "Measured ~32% of charts (a-priori independence estimate was 24%: planets cluster, notably "
        "Mercury and Venus near the Sun). Confirmed against an independent Swiss-based implementation "
        "(tests/test_rules_oracle.py). So 'Kemadruma' in about a third of charts is the arithmetic of "
        "this definition, not a rare affliction - the Composer must not present it as one.")

# ------------------------------------------------------------------ Surya (Sun-based) yogas
vesi = any_of(*[E(g, "house_from_sun", 2) for g in FIVE])
vosi = any_of(*[E(g, "house_from_sun", 12) for g in FIVE])
CH38 = bphs("38", "1")
NOTE_SU = "Counts Mars, Mercury, Jupiter, Venus, Saturn; excludes the Moon (per text) and Rahu/Ketu."
R("yoga.vesi", vesi, ("character", "wealth"),
  "Vesi yoga: a planet (other than the Moon) stands in the 2nd from the Sun. Traditionally read as a "
  "steady, well-spoken nature; benefic planets give the favourable form and malefics the reverse.",
  CH38, status="definition_checked", prov="classical_text", rarity="common", notes=NOTE_SU)
R("yoga.vosi", vosi, ("character", "wealth"),
  "Vosi yoga: a planet (other than the Moon) stands in the 12th from the Sun. Traditionally read as "
  "diligence and a capable, active nature; benefic planets give the favourable form and malefics the reverse.",
  CH38, status="definition_checked", prov="classical_text", rarity="common", notes=NOTE_SU)
R("yoga.ubhayachari", all_of(vesi, vosi), ("character", "career"),
  "Ubhayachari yoga: planets stand on both sides of the Sun. Traditionally read as a balanced, "
  "well-regarded character.",
  CH38, status="definition_checked", prov="classical_text", rarity="common", notes=NOTE_SU)

# ------------------------------------------------------------------ Raja yoga (kendra lord x kona lord)
STRICT = ("conjunct", "exchange", "mutual_aspect")
PAIRS = [(k, t) for k in (4, 7, 10) for t in (5, 9)]
for k, t in PAIRS:
    R(f"raja.l{k}_l{t}", I(lord_pair(k, t), "relation", STRICT), ("career", "status"),
      f"Raja yoga: the lords of the {ordn(k)} (an angular house) and the {ordn(t)} (a trine) are linked by "
      "conjunction, exchange or mutual aspect. Traditionally read as support for rise in status and "
      "achievement, strongest when the planets are themselves well placed.",
      bphs("34", "11-13"), prov="classical_text", rarity="moderate",
      notes="Text (as read) also admits a one-way full aspect between the lords; that reading makes the "
            "yoga appear in most charts, so the stricter mutual-aspect reading is used. Lagna lord is "
            "omitted from the kendra set (it already rules a trine). Needs the auditor's ruling.")
R("raja.yogakaraka", any_of(*[E(lord_pair(k, t), "relation", "same_planet") for k, t in PAIRS]),
  ("career", "status"),
  "Yogakaraka: one planet rules both an angular house and a trine for this Lagna. Traditionally read as "
  "a particularly supportive planet whose periods tend to favour achievement.",
  bphs("34", "11-13"), status="definition_checked", prov="classical_text", rarity="common",
  notes="Text says the same planet owning a kendra and a kona qualifies. Lagna lord excluded from the "
        "kendra set. Holds for six Lagnas (Vrishabha, Karka, Simha, Tula, Makara, Kumbha).")

# ------------------------------------------------------------------ Wealth (adverse + dhana)
R("wealth.daridra_mars_saturn_2h",
  all_of(E("Mars", "house", 2), E(pair("Mars", "Saturn"), "conjunct", True),
         E(aspect_subject("Mercury", "Mars"), "aspects", False)),
  ("wealth",),
  "Mars and Saturn together in the 2nd house: traditionally a caution for accumulation of wealth and "
  "family resources, softened when Mercury aspects them.",
  bphs("42", "16-18"), status="definition_checked", prov="classical_text", adverse=True, rarity="rare",
  notes="Mercury's aspect on the pair reverses the effect per the text; implemented as Mercury NOT "
        "aspecting Mars's sign (the pair share a sign).")
R("wealth.daridra_sun_2h_saturn_aspect",
  all_of(E("Sun", "house", 2), E(aspect_subject("Saturn", "Sun"), "aspects", True)), ("wealth",),
  "Sun in the 2nd house aspected by Saturn: traditionally a caution for steadiness of finances and "
  "family support in the early part of life.",
  bphs("42", "16-18"), status="definition_checked", prov="classical_text", adverse=True, rarity="uncommon",
  notes="Verse range reported by automated reading; confirm. The 'early part of life' gloss is ours and "
        "should be checked against the verse.")

DHANA = ((2, 11), (5, 9), (1, 11), (2, 5), (9, 11))
for a, b in DHANA:
    R(f"wealth.dhana_l{a}_l{b}", I(lord_pair(a, b), "relation", STRICT), ("wealth",),
      f"Dhana yoga: the lords of the {ordn(a)} and {ordn(b)} houses are linked by conjunction, exchange or mutual "
      "aspect. Traditionally read as support for earning and accumulation, in the periods of the "
      "planets involved.",
      bphs("41", "16") if (a, b) == (5, 9) else UNP, prov="later_tradition", rarity="moderate",
      notes="Which house-lord pairs make a dhana yoga varies by source; the 5th-9th pair is the one the "
            "text (as read) names. The text speaks of results during the planets' dasha, not a "
            "conjunction requirement. Status stays draft.")

# ------------------------------------------------------------------ Nabhasa (Asraya group)
for name, signs, text in (
    ("rajju", (0, 3, 6, 9), "all seven planets in movable signs: traditionally read as an active, "
                             "ambitious, travel-prone temperament"),
    ("musala", (1, 4, 7, 10), "all seven planets in fixed signs: traditionally read as steadiness, "
                              "firm resolve and self-respect"),
    ("nala", (2, 5, 8, 11), "all seven planets in dual signs: traditionally read as adaptability and "
                            "versatility"),
):
    R(f"nabhasa.{name}", all_of(*[I(g, "sign_index", signs) for g in SEVEN]), ("character",),
      f"{name.capitalize()} yoga (Nabhasa, Asraya group): {text}.",
      bphs("35", "7"), status="definition_checked", prov="classical_text", rarity="rare",
      notes="'All planets' is read as the seven visible grahas (Sun to Saturn), the standard reading.")

# ------------------------------------------------------------------ Dignity (synthesized from significations)
KARAKA = {"Sun": "vitality, authority and self-confidence", "Moon": "the mind, emotions and nurturing",
          "Mars": "energy, courage and initiative", "Mercury": "intellect, speech and commerce",
          "Jupiter": "wisdom, guidance and fortune", "Venus": "relationships, comforts and the arts",
          "Saturn": "discipline, perseverance and responsibility"}
DIG_SRC = Source(BPHS, "3", "49-50", edition=ED)
for g in SEVEN:
    k = KARAKA[g]
    R(f"dignity.{g.lower()}_exalted", E(g, "dignity", "exalted"), ("character",),
      f"{g} is in its sign of exaltation, conventionally its strongest sign. Matters it stands for "
      f"({k}) tend to express with ease and strength.",
      DIG_SRC, prov="synthesized", rarity="moderate",
      notes="Dignity table is classical (chapter reference checked at chapter level). The reading is "
            "synthesized from the planet's standard significations, not from a verse. Degree-level "
            "refinement needs an exact birth time and is not applied.")
    R(f"dignity.{g.lower()}_debilitated", E(g, "dignity", "debilitated"), ("character",),
      f"{g} is in its sign of debilitation, conventionally its weakest sign. Matters it stands for "
      f"({k}) may need more effort or show uneven results; classical texts list conditions that offset this.",
      DIG_SRC, prov="synthesized", adverse=True, rarity="moderate",
      notes="See exalted note. Cancellation (neecha-bhanga) is a separate rule.")
    R(f"dignity.{g.lower()}_own", E(g, "dignity", "own"), ("character",),
      f"{g} is in a sign it rules, which classical convention treats as a comfortable, stable placement. "
      f"Matters it stands for ({k}) tend to express steadily.",
      DIG_SRC, prov="synthesized", rarity="moderate",
      notes="'own' excludes the exaltation sign (Mercury in Kanya is classed exalted).")

# ------------------------------------------------------------------ Lagna lord placement (grouped)
LL = bphs("24")
for name, houses, text, adv in (
    ("kendra", KENDRA, "in an angular house: traditionally a self-reliant, well-supported life direction", False),
    ("trikona", (5, 9), "in a trine (5th or 9th): traditionally a fortunate, purposeful orientation", False),
    ("dusthana", DUSTHANA, "in the 6th, 8th or 12th: traditionally a life direction shaped by effort, "
                           "service, change or withdrawal", True),
    ("upachaya_2_3_11", (2, 3, 11), "in the 2nd, 3rd or 11th: traditionally gains that build gradually "
                                    "through effort, resources and networks", False),
):
    R(f"lagna_lord.{name}", I("house1", "lord_house", houses), ("character", "general"),
      f"The Lagna lord is placed {text}.", LL, prov="synthesized", adverse=adv, rarity="common" if name == "kendra" else "moderate",
      notes="Grouped by house class rather than twelve separate placements; wording synthesized from "
            "standard house significations. Chapter reference checked at chapter level only.")

# ------------------------------------------------------------------ Vipareeta Raja yoga
for n, name in ((6, "harsha"), (8, "sarala"), (12, "vimala")):
    R(f"yoga.vipareeta_{name}", I(f"house{n}", "lord_house", DUSTHANA), ("general", "status"),
      f"Vipareeta Raja yoga ({name.capitalize()}): the lord of the {n}th sits in another difficult house "
      "(6th, 8th or 12th). Traditionally read as difficulties that eventually turn to advantage.",
      UNP, rarity="moderate",
      notes="Primary chapter not located in the portions read; the three names and the 6/8/12 rule are "
            "standard in later texts. Many authors also require the lord to be unconnected to other "
            "planets - not implemented.")

# ------------------------------------------------------------------ Moon-Jupiter and conjunction yogas
R("yoga.gajakesari", I("Jupiter", "house_from_moon", KENDRA), ("mind", "status"),
  "Gajakesari yoga: Jupiter stands in an angular house from the Moon. Traditionally read as intelligence, "
  "good repute and a supportive standing in society.",
  Source("Phaladeepika", "6", "1", edition="cited via dekhopanchang.com (secondary); primary text not read"),
  prov="classical_text", rarity="common",
  notes="Modern authors often add conditions (Jupiter not debilitated or combust, Moon strong). Not applied.")
CONJ = (
    ("budhaditya", "Sun", "Mercury", False, "common", ("mind", "career"),
     "Budhaditya yoga: Sun and Mercury share a sign. Traditionally read as sharpness of intellect and "
     "skill in communication and analysis."),
    ("chandra_mangala", "Moon", "Mars", False, "moderate", ("wealth", "mind"),
     "Chandra-Mangala yoga: Moon and Mars share a sign. Traditionally read as enterprise and an "
     "earning drive."),
    ("guru_chandala", "Jupiter", "Rahu", True, "moderate", ("mind", "character"),
     "Guru-Chandala yoga: Jupiter and Rahu share a sign. Traditionally read as an unconventional or "
     "questioning approach to belief, teachers and tradition."),
    ("angaraka", "Mars", "Rahu", True, "moderate", ("character", "health"),
     "Angaraka yoga: Mars and Rahu share a sign. Traditionally read as intensity and impulsiveness "
     "that benefit from conscious channelling."),
    ("shrapit", "Saturn", "Rahu", True, "moderate", ("character", "general"),
     "Shrapit yoga: Saturn and Rahu share a sign. Traditionally read as heavy responsibilities or "
     "recurring delays that ask for patience."),
    ("vish", "Moon", "Saturn", True, "moderate", ("mind",),
     "Vish yoga: Moon and Saturn share a sign. Traditionally read as a serious, reserved emotional "
     "temperament that can feel burdened at times."),
)
for name, a, b, adv, rar, scope, text in CONJ:
    R(f"yoga.{name}", E(pair(a, b), "conjunct", True), scope, text, UNP, adverse=adv, rarity=rar,
      notes="Popular later-tradition yoga; primary source not pinned. Sign-level conjunction (no orb).")

# ------------------------------------------------------------------ Manglik (Kuja dosha)
MANGLIK = (1, 4, 7, 8, 12)
for ref, subj in (("lagna", "house"), ("moon", "house_from_moon"), ("venus", "house_from_venus")):
    R(f"dosha.manglik_from_{ref}", I("Mars", subj, MANGLIK), ("marriage",),
      f"Mars occupies the 1st, 4th, 7th, 8th or 12th counted from the {ref.capitalize() if ref != 'lagna' else 'Lagna'} "
      "(Manglik / Kuja dosha). Traditionally flagged in marriage matching as a sign of strong, assertive "
      "energy in partnership; many traditions list cancellations and weigh it against the partner's chart.",
      UNP, adverse=True, rarity="common",
      notes="Regional variants add the 2nd house, and some exclude the 12th or treat it as milder. "
            "Cancellation rules are not implemented. High frequency (~40% of charts per reference) is "
            "expected; the Composer must not treat this as a rare or alarming finding.")

# ------------------------------------------------------------------ Kaal Sarp / Kaal Amrit
R("dosha.kaal_sarp", E("chart", "nodal_hemming", "rahu_to_ketu"), ("general",),
  "All seven planets lie on one side of the Rahu-Ketu axis, in the Rahu-to-Ketu half (Kaal Sarp, as "
  "most sources define it). Traditionally read as a life pattern of concentrated karmic themes; this "
  "concept is a later tradition and is not found in the classical texts read here.",
  UNP, adverse=True, rarity="uncommon",
  notes="Sources disagree on which half is Kaal Sarp and which Kaal Amrit. Requires exact birth time "
        "(planet longitudes). Not a classical yoga; the Composer should say so.")
R("dosha.kaal_amrit", E("chart", "nodal_hemming", "ketu_to_rahu"), ("general",),
  "All seven planets lie on one side of the Rahu-Ketu axis, in the Ketu-to-Rahu half (called Kaal Amrit "
  "or the reverse pattern in some sources). A later-tradition concept, not found in the classical texts "
  "read here.",
  UNP, rarity="uncommon",
  notes="See kaal_sarp: the naming of the two halves differs between sources.")

# ------------------------------------------------------------------ Neecha Bhanga and Parivartana
R("yoga.neecha_bhanga_dispositor_kendra",
  any_of(*[all_of(E(g, "dignity", "debilitated"), I(g, "dispositor_house", KENDRA)) for g in SEVEN]),
  ("general",),
  "A debilitated planet whose sign lord is in an angular house from the Lagna: one of the classical "
  "conditions for cancellation of debilitation (neecha-bhanga), traditionally read as a weakness that "
  "can turn into strength.",
  UNP, rarity="moderate",
  notes="Only one of several commonly listed cancellation criteria (others: exaltation-lord in kendra, "
        "kendra from the Moon, exchange, etc.). Primary source not pinned.")

M_HOUSES = (1, 2, 4, 5, 7, 9, 10, 11)


def _exchange(pairs):
    return any_of(*[E(lord_pair(a, b), "relation", "exchange") for a, b in pairs])


R("parivartana.maha", _exchange(list(combinations(M_HOUSES, 2))), ("general", "status"),
  "Maha Parivartana: the lords of two favourable houses (1, 2, 4, 5, 7, 9, 10, 11) exchange signs. "
  "Traditionally read as a strong mutual support between the matters of those houses.",
  UNP, rarity="common",
  notes="House sets per later-tradition convention; not pinned. Measured ~29% of charts (estimate was "
        "15-25%); confirmed against an independent planet-centric implementation. Exchange between "
        "two planets is common, and most house pairs count as 'favourable'.")
R("parivartana.dainya", _exchange([(d, x) for d in DUSTHANA for x in M_HOUSES + (3,)]), ("general",),
  "Dainya Parivartana: the lord of the 6th, 8th or 12th exchanges signs with the lord of another house. "
  "Traditionally read as the matters of those houses becoming entangled with difficulty or effort.",
  UNP, adverse=True, rarity="common",
  notes="Pairs of two dusthana lords are excluded (treated as a separate pattern). Not pinned. Measured "
        "~30% of charts; confirmed against an independent implementation. Common, so not a rare warning.")
R("parivartana.khala", _exchange([(3, x) for x in M_HOUSES]), ("general",),
  "Khala Parivartana: the lord of the 3rd exchanges signs with the lord of a favourable house. "
  "Traditionally read as a mixed, effort-driven but ambitious pattern.",
  UNP, rarity="moderate",
  notes="Conventions vary; not pinned.")


def parashari_rules() -> list[Rule]:
    from .parashari_bhavas import RULES as _BHAVA_RULES      # lazy: that module imports helpers from here
    return list(RULES) + list(_BHAVA_RULES)
