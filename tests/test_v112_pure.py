"""v1.1.2: yogas, static character assets, split Ask layout wiring. Pure stdlib."""
import re
import unittest
from pathlib import Path

from aipandit import brain, yogas

STATIC = Path(__file__).resolve().parents[1] / "src" / "aipandit" / "web" / "static"
SERVER = Path(__file__).resolve().parents[1] / "src" / "aipandit" / "web" / "server.py"

CH = {"lagna": "Simha", "moon": {"sign": "Karka", "nakshatra": "Pushya"}, "time_certainty": "exact", "planets": {
    "Sun": {"sign": "Mithuna", "house": 12}, "Moon": {"sign": "Karka", "house": 1}, "Mars": {"sign": "Karka", "house": 1},
    "Mercury": {"sign": "Mithuna", "house": 12}, "Jupiter": {"sign": "Tula", "house": 3}, "Venus": {"sign": "Kanya", "house": 2},
    "Saturn": {"sign": "Makara", "house": 6}, "Rahu": {"sign": "Dhanu", "house": 5}, "Ketu": {"sign": "Mithuna", "house": 11}}}


class YogaTests(unittest.TestCase):
    def keys(self, chart, ok=True):
        return [y["key"] for y in yogas.find_yogas(chart, ok)]

    def test_known_yogas_are_detected(self):
        self.assertEqual(self.keys(CH)[:3], ["gajakesari", "budhaditya", "chandramangal"])

    def test_mahapurusha_needs_own_sign_and_kendra_and_reliable_lagna(self):
        ch = {"planets": {"Jupiter": {"sign": "Dhanu", "house": 4}, "Moon": {"sign": "Meena", "house": 3}}, "moon": {"sign": "Meena"}}
        self.assertIn("mahapurusha", self.keys(ch))
        self.assertNotIn("mahapurusha", self.keys(ch, ok=False))
        ch["planets"]["Jupiter"]["house"] = 3
        self.assertNotIn("mahapurusha", self.keys(ch))

    def test_guru_chandal_is_gentle(self):
        ch = {"planets": {"Jupiter": {"sign": "Kanya", "house": 1}, "Rahu": {"sign": "Kanya", "house": 1}, "Moon": {"sign": "Mesha", "house": 8}}, "moon": {"sign": "Mesha"}}
        self.assertIn("gurucandal", self.keys(ch))
        for lang in ("en", "hg", "hi"):
            txt = yogas.yoga_text(ch, lang)
            self.assertNotRegex(txt.lower(), r"curse is|doom|must perform|buy")

    def test_no_yoga_is_not_alarming(self):
        ch = {"planets": {"Jupiter": {"sign": "Mesha", "house": 2}, "Moon": {"sign": "Mesha", "house": 2}}, "moon": {"sign": "Mesha"}}
        ch["planets"]["Jupiter"]["sign"] = "Vrishabha"
        self.assertEqual(self.keys(ch), [])
        self.assertIn("very little", yogas.yoga_text(ch, "en"))

    def test_brain_routes_personal_yoga_questions_in_three_languages(self):
        for q, lang, needle in (("which yogas do I have?", "en", "Gajakesari"), ("mere yog kya hain", "hg", "Gajakesari"), ("मेरे योग क्या हैं", "hi", "गजकेसरी")):
            r = brain.answer(q, CH, lang, None, False, [])
            self.assertEqual(r["topic"], "yoga")
            self.assertIn(needle, r["answer"])

    def test_conceptual_yoga_question_uses_reference_not_chart(self):
        r = brain.answer("what is gajakesari yoga", CH, "en", None, False, [])
        self.assertNotIn("in your chart", r["answer"].lower()[:40])

    def test_yoga_without_chart_asks_for_birth_details(self):
        self.assertTrue(brain.answer("my yogas", None, "en", None, False, [])["needs_profile"])


class AssetTests(unittest.TestCase):
    def test_character_images_exist_and_are_jpeg(self):
        for f in ("naradvani.jpg", "naradvani-avatar.jpg"):
            b = (STATIC / f).read_bytes()
            self.assertEqual(b[:3], b"\xff\xd8\xff", f)
            self.assertLess(len(b), 400_000, f)

    def test_server_serves_jpg(self):
        self.assertIn('".jpg": "image/jpeg"', SERVER.read_text(encoding="utf-8"))

    def test_no_stale_svg_reference_and_avatar_is_photo(self):
        for f in ("app.js", "index.html", "v11.css", "onboarding.js"):
            self.assertNotIn("naradvani.svg", (STATIC / f).read_text(encoding="utf-8"), f)
        self.assertIn("naradvani-avatar.jpg", (STATIC / "app.js").read_text(encoding="utf-8"))

    def test_split_layout_and_strings_exist_in_all_languages(self):
        css = (STATIC / "v11.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.askpage\{display:grid;grid-template-columns:")
        self.assertIn("@media(max-width:860px)", css)
        js = (STATIC / "i18n11.js").read_text(encoding="utf-8")
        for key in ("listening", "ai_guide", "stage_cap", "ai_char", "useful_q", "not_quite", "fb_yes", "fb_no", "voice_on", "voice_off"):
            self.assertEqual(len(re.findall(r"\b" + key + r":", js)), 3, key)

    def test_csp_friendly_no_inline_style_or_handlers_in_new_markup(self):
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        i = js.index("function stageHtml")
        j = js.index("function speak")
        self.assertNotRegex(js[i:j], r"style=|onclick=")


if __name__ == "__main__":
    unittest.main()
