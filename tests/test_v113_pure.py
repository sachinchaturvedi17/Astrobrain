"""v1.1.3: raja yogas, dasha timing windows, expert case library. Pure stdlib."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path

from aipandit import brain, expert, retrieval, timeline, yogas

CH = {"lagna": "Simha", "moon": {"sign": "Karka", "nakshatra": "Pushya"}, "time_certainty": "exact", "planets": {
    "Sun": {"sign": "Mithuna", "house": 12}, "Moon": {"sign": "Karka", "house": 12}, "Mars": {"sign": "Karka", "house": 12},
    "Mercury": {"sign": "Mithuna", "house": 11}, "Jupiter": {"sign": "Tula", "house": 3}, "Venus": {"sign": "Kanya", "house": 2},
    "Saturn": {"sign": "Makara", "house": 6}, "Rahu": {"sign": "Dhanu", "house": 5}, "Ketu": {"sign": "Mithuna", "house": 11}}}


def with_dasha(chart, maha="Saturn", antar="Mercury", antar_end="2027-03-10"):
    rest = sum(timeline.YEARS[maha] * timeline.YEARS[x] / 120 * timeline.YEAR_DAYS
               for x in (timeline.ORDER[timeline.ORDER.index(maha):] + timeline.ORDER[:timeline.ORDER.index(maha)])[
                   (timeline.ORDER[timeline.ORDER.index(maha):] + timeline.ORDER[:timeline.ORDER.index(maha)]).index(antar) + 1:])
    me = (dt.date.fromisoformat(antar_end) + dt.timedelta(days=rest)).isoformat()
    c = dict(chart)
    c["dasha"] = {"maha": maha, "antar": antar, "antar_end": antar_end, "maha_end": me}
    return c


class RajaYogaTests(unittest.TestCase):
    def keys(self, c, ok=True):
        return [y["key"] for y in yogas.find_yogas(c, ok)]

    def test_yogakaraka_and_raja_yoga_for_simha_lagna(self):
        k = self.keys(CH)
        self.assertIn("yogakaraka", k)      # Mars rules 4th and 9th for Leo
        self.assertIn("rajayoga", k)        # Saturn (7th) faces Mars (9th) across Makara-Karka

    def test_raja_yoga_needs_a_reliable_lagna(self):
        self.assertNotIn("rajayoga", self.keys(CH, ok=False))
        self.assertNotIn("yogakaraka", self.keys(CH, ok=False))

    def test_neecha_bhanga_cancellation(self):
        def mars(c):
            return [y for y in yogas.find_yogas(c) if y["key"] == "neechabhanga" and y["p1"] == "Mars"]
        self.assertTrue(mars(CH))                      # Mars in Karka; Saturn (lord of its exaltation sign) is in a kendra from the Moon
        c = json.loads(json.dumps(CH)); c["planets"]["Moon"]["sign"] = "Dhanu"; c["moon"]["sign"] = "Dhanu"
        self.assertFalse(mars(c))                      # no helper in a kendra from Lagna or Moon now

    def test_text_is_plain_and_three_languages(self):
        for lang, needle in (("en", "Raja yoga"), ("hg", "Raja yoga"), ("hi", "राज योग")):
            self.assertIn(needle, yogas.yoga_text(CH, lang))
        self.assertNotRegex(yogas.yoga_text(CH, "en").lower(), r"guarantee|curse is|doom")

    def test_routing_for_raja_yoga_question(self):
        r = brain.answer("do I have a raja yoga?", CH, "en", None, False, [])
        self.assertEqual(r["topic"], "yoga")
        self.assertIn("Raja yoga", r["answer"])


class TimelineTests(unittest.TestCase):
    TODAY = dt.date(2026, 11, 22)

    def test_periods_follow_vimshottari_order(self):
        ps = timeline.periods(with_dasha(CH), self.TODAY, 5)
        self.assertEqual([p["antar"] for p in ps[:4]], ["Mercury", "Ketu", "Venus", "Sun"])
        for a, b in zip(ps, ps[1:]):
            self.assertEqual(a["end"], b["start"])
        ketu = ps[1]
        self.assertAlmostEqual((ketu["end"] - ketu["start"]).days, 19 * 7 / 120 * 365.25, delta=2)

    def test_next_maha_starts_in_order_after_last_antar(self):
        c2 = with_dasha(CH, "Jupiter", "Rahu", "2027-01-01")   # Rahu is the last antar of a Jupiter maha
        ps = timeline.periods(c2, self.TODAY, 4)
        self.assertEqual(ps[1]["maha"], "Saturn"); self.assertEqual(ps[1]["antar"], "Saturn")

    def test_inconsistent_anchor_gives_no_windows(self):
        c = with_dasha(CH); c["dasha"]["maha_end"] = "2031-06-01"
        self.assertEqual(timeline.periods(c, self.TODAY), [])
        self.assertEqual(timeline.window_text(c, {"Venus"}, "en", self.TODAY), "")
        self.assertEqual(timeline.periods({}, self.TODAY), [])

    def test_windows_pick_topic_planets_and_stay_honest(self):
        w = timeline.windows(with_dasha(CH), {"Venus", "Ketu"}, self.TODAY, 5)
        self.assertEqual([x["antar"] for x in w], ["Ketu", "Venus"])
        txt = timeline.window_text(with_dasha(CH), {"Venus"}, "en", self.TODAY)
        self.assertIn("not dates for events", txt)
        self.assertNotRegex(txt.lower(), r"will (get|marry|happen)")

    def test_when_question_appends_windows(self):
        c = with_dasha(CH)
        r = brain.answer("when will I get married?", c, "en", None, False, [])
        self.assertEqual(r["topic"], "marriage")
        self.assertTrue(r["timing"])
        self.assertTrue("stretches switch this area on" in r["answer"] or "special window" in r["answer"])


class ExpertTests(unittest.TestCase):
    GOOD = {"id": "career_delay_001", "lang": "en", "topic": "career", "problem": "Promotion has been delayed for years despite good work",
            "advice": "First check whether the sub-period running now is testing patience. Keep a written record of your results, ask your manager for specific goals and revisit in three months.",
            "remedies": ["serve elders on Saturdays"], "cautions": "Do not resign in a hurry.", "expert": "anonymous", "consent": True}

    def test_lint_accepts_a_good_case(self):
        e, w = expert.lint(self.GOOD)
        self.assertEqual(e, [])

    def test_lint_rejects_unsafe_or_private_content(self):
        bad = {
            "death": "He will die early if the puja is not done soon, so please act now.",
            "guarantee": "Do this and you will get the job, 100% guaranteed within a month.",
            "fear": "This is a curse on your family and you will be ruined unless handled.",
            "money": "Book a puja with us for Rs. 5100 and the delay ends this month.",
            "medical": "Stop your medicine and wear this ring, it will cure diabetes for good.",
            "phone": "Call him on 9876543210 and he will explain everything in detail to you.",
            "invest": "You should invest in shares this month because Jupiter supports it strongly.",
        }
        for name, advice in bad.items():
            c = dict(self.GOOD, advice=advice)
            e, _ = expert.lint(c)
            self.assertTrue(e, name)

    def test_lint_requires_consent_and_fields(self):
        self.assertTrue(expert.lint(dict(self.GOOD, consent=False))[0])
        c = dict(self.GOOD); del c["advice"]
        self.assertTrue(expert.lint(c)[0])
        self.assertTrue(expert.lint(dict(self.GOOD, topic="lottery"))[0])

    def test_end_to_end_loading_retrieval_and_answer(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.jsonl").write_text(json.dumps(self.GOOD) + "\n" + json.dumps(dict(self.GOOD, id="bad_001", advice="He will die soon, so act now please.")) + "\n", encoding="utf-8")
            (Path(d) / "_template.jsonl").write_text(json.dumps(dict(self.GOOD, id="tmpl_001")) + "\n", encoding="utf-8")
            old = os.environ.get("ASTRONARAD_EXPERT_DIR")
            os.environ["ASTRONARAD_EXPERT_DIR"] = d
            try:
                expert._CACHE.clear(); retrieval.load_index(force=True)
                self.assertEqual(sorted(expert.load_cases()), ["career_delay_001"])
                self.assertTrue(any("skipped" in x for x in expert.last_report()))
                r = brain.answer("My promotion has been delayed for years despite good work, what should I do?", CH, "en", None, False, [])
                self.assertIn("experienced astrologer", r["answer"])
                self.assertIn("Do not resign in a hurry", r["answer"])
                self.assertTrue(any(e["tier"] == "expert" for e in r["evidence"]))
                self.assertNotEqual(r["composer"], "llm")
                r3 = brain.answer("How is my career going to be?", CH, "en", None, False, [])
                self.assertNotIn("experienced astrologer on our panel", r3["answer"])   # vague question must not pull a specific case
                r2 = brain.answer("How is my health going to be?", CH, "en", None, False, [])
                self.assertNotIn("experienced astrologer on our panel", r2["answer"])
            finally:
                if old is None:
                    os.environ.pop("ASTRONARAD_EXPERT_DIR", None)
                else:
                    os.environ["ASTRONARAD_EXPERT_DIR"] = old
                expert._CACHE.clear(); retrieval.load_index(force=True)

    def test_no_cases_means_no_change(self):
        with tempfile.TemporaryDirectory() as d:
            old = os.environ.get("ASTRONARAD_EXPERT_DIR"); os.environ["ASTRONARAD_EXPERT_DIR"] = d
            try:
                expert._CACHE.clear(); retrieval.load_index(force=True)
                r = brain.answer("How is my career going to be?", CH, "en", None, False, [])
                self.assertNotIn("experienced astrologer", r["answer"])
            finally:
                if old is None:
                    os.environ.pop("ASTRONARAD_EXPERT_DIR", None)
                else:
                    os.environ["ASTRONARAD_EXPERT_DIR"] = old
                expert._CACHE.clear(); retrieval.load_index(force=True)


if __name__ == "__main__":
    unittest.main()


class RunningDashaTests(unittest.TestCase):
    def test_running_dasha_is_read_from_the_kundli_when_facts_are_empty(self):
        from unittest import mock
        try:
            from aipandit import v10_engine
            import aipandit.kundli  # noqa: F401
        except Exception:
            self.skipTest("chart engine modules are not importable here")
        fake = {"maha": "Saturn", "maha_end": "2031-06-01", "antar": "Mercury", "antar_end": "2027-03-10"}
        with mock.patch("aipandit.kundli.dasha_at", return_value=fake):
            self.assertEqual(v10_engine._running_dasha(object())["maha"], "Saturn")
        with mock.patch("aipandit.kundli.dasha_at", side_effect=ValueError("withheld")):
            self.assertIsNone(v10_engine._running_dasha(object()))
