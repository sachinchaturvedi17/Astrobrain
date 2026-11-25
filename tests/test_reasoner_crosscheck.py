"""Cross-check the advisor's reasoning sheet against the shared rule engine.

`reasoner.Sheet` is what the live astrologer reads off a chart; `derive.py` is the single source of derived
facts used by the 131-rule engine. They must agree on every primitive (signs, houses, lords, dignities,
aspects and lord relations) or the same chart would get two different readings depending on the path.

Charts are built deterministically with fixed placements (no ephemeris needed)."""
import random
import unittest

import chartkit
from aipandit import reasoner
from aipandit.ashtakoota import RASHIS
from aipandit.derive import lord_pair
from aipandit.jyotish import GRAHAS

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
RELATION = {"same": "same_planet", "conjunct": "conjunct", "exchange": "exchange",
            "mutual": "mutual_aspect", "a_on_b": "one_way_aspect", "b_on_a": "one_way_aspect", "none": "none"}


def placements(seed):
    """A fixed spread of grahas over the twelve signs, with Rahu/Ketu always opposite."""
    rnd = random.Random(seed)
    signs = {g: rnd.randrange(12) for g in SEVEN}
    signs["Rahu"] = rnd.randrange(12)
    signs["Ketu"] = (signs["Rahu"] + 6) % 12
    return {g: int(s) for g, s in signs.items()}


def corpus():
    for lagna in range(12):
        for seed in (lagna * 2 + 1, lagna * 2 + 2):
            yield lagna, placements(seed)


def sheet_and_store(lagna, signs):
    _kundli, store = chartkit.make(lagna, signs)
    chart = {
        "lagna": RASHIS[store.value("lagna", "sign_index")],
        "moon": {"sign": RASHIS[store.value("Moon", "sign_index")]},
        "planets": {g: {"sign": RASHIS[store.value(g, "sign_index")], "house": store.value(g, "house")} for g in GRAHAS},
        "time_certainty": "exact",
        "profile": {"gender": "male"},
    }
    return reasoner.Sheet(chart), store


class PrimitiveAgreementTests(unittest.TestCase):
    def test_signs_and_houses_match_derived_facts(self):
        for lagna, signs in corpus():
            sheet, store = sheet_and_store(lagna, signs)
            for g in GRAHAS:
                self.assertEqual(sheet.sign_of(g), store.value(g, "sign"), (lagna, g))
                self.assertEqual(sheet.house_of(g), store.value(g, "house"), (lagna, g))

    def test_house_lordship_matches_derived_facts(self):
        for lagna, signs in corpus():
            sheet, store = sheet_and_store(lagna, signs)
            for h in range(1, 13):
                self.assertEqual(sheet.lord(h), store.value(f"house{h}", "lord"), (lagna, h))
                lord = sheet.lord(h)
                self.assertEqual(sheet.house_of(lord), store.value(f"house{h}", "lord_house"), (lagna, h, lord))
                self.assertEqual(sheet.sign(h), RASHIS[(lagna + h - 1) % 12], (lagna, h))

    def test_dignity_of_the_seven_matches_derived_facts(self):
        for lagna, signs in corpus():
            sheet, store = sheet_and_store(lagna, signs)
            for g in SEVEN:
                self.assertEqual(sheet.dignity(g), store.value(g, "dignity"), (lagna, g))

    def test_aspects_match_derived_facts_including_the_nodes(self):
        for lagna, signs in corpus():
            sheet, store = sheet_and_store(lagna, signs)
            for a in GRAHAS:
                derived = {b for b in GRAHAS if b != a and store.value(f"{a}>{b}", "aspects") is True}
                mine = {b for b in GRAHAS if b != a and sheet.house_of(b) in sheet.aspect_houses(a)}
                self.assertEqual(mine, derived, (lagna, a))

    def test_lord_relations_match_derived_facts(self):
        for lagna, signs in corpus():
            sheet, store = sheet_and_store(lagna, signs)
            for h1 in range(1, 13):
                for h2 in range(h1 + 1, 13):
                    la, lb = sheet.lord(h1), sheet.lord(h2)
                    expected = store.value(lord_pair(h1, h2), "relation")
                    self.assertEqual(RELATION[sheet.relation(la, lb)], expected, (lagna, h1, h2, la, lb))

    def test_sheet_consumes_store_facts_directly_when_attached(self):
        for lagna, signs in corpus():
            sheet, store = sheet_and_store(lagna, signs)
            chart_with_store = dict(sheet.chart, store=store)
            backed = reasoner.Sheet(chart_with_store)
            self.assertIs(backed.store, store)
            for g in GRAHAS:
                self.assertEqual(backed.sign_of(g), sheet.sign_of(g), (lagna, g))
                self.assertEqual(backed.house_of(g), sheet.house_of(g), (lagna, g))
            for g in SEVEN:
                self.assertEqual(backed.dignity(g), sheet.dignity(g), (lagna, g))
                self.assertEqual(backed.neecha_bhanga(g), sheet.neecha_bhanga(g), (lagna, g))
            for h in range(1, 13):
                self.assertEqual(backed.lord(h), sheet.lord(h), (lagna, h))


if __name__ == "__main__":
    unittest.main()
