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


class ProductEndToEndTests(unittest.TestCase):
    """End-to-end live HTTP product test covering all v1.4.0 /api/v10/* routes."""

    PROFILE = {
        "name": "Sachin Chaturvedi",
        "dob": "1990-05-15",
        "tob": "14:30",
        "time_certainty": "exact",
        "place": "Bhopal",
        "lat": 23.2599,
        "lon": 77.4126,
        "tz": "Asia/Kolkata",
        "gender": "male",
    }

    def test_v10_product_routes_over_http(self):
        import json
        import re
        import threading
        import urllib.request
        from datetime import datetime, timezone
        from aipandit.orchestrator import Pandit
        from aipandit.web.server import make_server

        srv = make_server(Pandit(now=lambda: datetime(2026, 11, 25, tzinfo=timezone.utc)), port=0, log_dir=None)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        def post(path, payload):
            req = urllib.request.Request(
                base + path,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))

        try:
            cfg = post("/api/v10/config", {})
            self.assertEqual(cfg["version"], "1.4.0")

            ch = post("/api/v10/chart", {"profile": self.PROFILE})
            self.assertTrue(ch["ok"])
            self.assertEqual(ch["lagna"], "Kanya")
            self.assertEqual(ch["moon"]["sign"], "Makara")
            self.assertEqual(ch["profile"]["name"], "Sachin Chaturvedi")
            self.assertEqual(ch["profile"]["place"], "Bhopal")

            import urllib.parse
            qs = urllib.parse.urlencode({
                "name": self.PROFILE["name"],
                "dob": self.PROFILE["dob"],
                "tob": self.PROFILE["tob"],
                "place": self.PROFILE["place"],
                "lat": self.PROFILE["lat"],
                "lon": self.PROFILE["lon"],
                "tz": self.PROFILE["tz"],
            })
            with urllib.request.urlopen(f"{base}/api/v10/kundli-pdf?{qs}", timeout=15) as pdf_resp:
                self.assertEqual(pdf_resp.status, 200)
                self.assertEqual(pdf_resp.headers.get("Content-Type"), "application/pdf")
                pdf_raw = pdf_resp.read()
                self.assertTrue(pdf_raw.startswith(b"%PDF-1.4"))
                self.assertIn(b"Sachin Chaturvedi", pdf_raw)
                self.assertIn(b"Kanya", pdf_raw)

            ask_en = post("/api/v10/ask", {"profile": self.PROFILE, "question": "When will my career grow?", "lang": "en"})
            self.assertEqual(ask_en["topic"], "career")
            self.assertEqual(ask_en["intent"], "when")
            self.assertTrue(ask_en["calc"])

            ask_hg = post("/api/v10/ask", {"profile": self.PROFILE, "question": "Meri shaadi kab hogi?", "lang": "hg"})
            self.assertEqual(ask_hg["lang"], "hg")
            self.assertEqual(ask_hg["topic"], "marriage")
            self.assertTrue(ask_hg["calc"])

            ask_hi = post("/api/v10/ask", {"profile": self.PROFILE, "question": "मेरा करियर कैसा रहेगा?", "lang": "hi"})
            self.assertEqual(ask_hi["lang"], "hi")
            self.assertIsNone(re.search(r"[A-Za-z]", ask_hi["answer"]))

            crisis = post("/api/v10/ask", {"profile": self.PROFILE, "question": "mujhe jeene ka mann nahi hai", "lang": "hg"})
            self.assertEqual(crisis["safety"], "self_harm")
            self.assertIn("14416", crisis["answer"])

            minor = post("/api/v10/ask", {"profile": dict(self.PROFILE, dob="2012-05-15"), "question": "When will I get married?", "lang": "en"})
            self.assertEqual(minor["safety"], "minor_topic")

            horo = post("/api/v10/horoscope", {"profile": self.PROFILE, "lang": "en"})
            self.assertTrue(horo["ok"])
            self.assertEqual(len(horo["signs"]), 12)

            pan = post("/api/v10/panchang", {"profile": self.PROFILE, "lang": "en"})
            self.assertTrue(pan["ok"])
            self.assertTrue(pan["karana"])

            partner = dict(self.PROFILE, name="Partner", dob="1992-08-20", tob="10:15")
            comp = post("/api/v10/compat", {"person_a": self.PROFILE, "person_b": partner, "lang": "en"})
            self.assertTrue(comp["ok"])

            calc = post("/api/v10/calculator", {"type": "nakshatra", "profile": self.PROFILE, "lang": "en"})
            self.assertTrue(calc["ok"])
            self.assertIn("Pada", calc["headline"])

            rep = post("/api/v10/report", {"topic": "career", "profile": self.PROFILE, "lang": "en"})
            self.assertTrue(rep["ok"])
            self.assertTrue(rep["houses"])

            with urllib.request.urlopen(f"{base}/api/v10/admin/users?limit=10", timeout=15) as adm_resp:
                adm = json.loads(adm_resp.read().decode("utf-8"))
                self.assertTrue(adm["ok"])
                self.assertGreaterEqual(adm["counts"]["users_profiles"], 1)
                self.assertGreaterEqual(adm["counts"]["chat_interactions"], 1)
                self.assertGreaterEqual(adm["counts"]["kundli_downloads"], 1)
                self.assertTrue(any(u["full_name"] == "Sachin Chaturvedi" for u in adm["users"]))
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
