"""Pure-logic tests for AstroMuni v1.0 (no chart engine needed): python -m unittest tests.test_v10_pure"""
import datetime, unittest
from aipandit import ashtakoota, solar, retrieval


class T(unittest.TestCase):
    def test_ashtakoota_bounds(self):
        a = {"rashi": "Mesha", "nakshatra": "Ashwini"}
        b = {"rashi": "Tula", "nakshatra": "Swati"}
        r = ashtakoota.compute(a, b)
        self.assertLessEqual(r["total"], 36)
        self.assertGreaterEqual(r["total"], 0)
        self.assertEqual(len(r["kootas"]), 8)

    def test_solar_delhi(self):
        d = solar.day_timings(datetime.date(2026, 6, 21), 28.61, 77.21, 5.5)
        self.assertIn("sunrise", d)
        self.assertIn("rahu_kaal", d)

    def test_retrieval(self):
        hits = retrieval.search("what is sade sati", k=3)
        self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
