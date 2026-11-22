"""v1.2.0: living portrait (Chat = silent blinking, Talk = voice + lip movement). Static checks plus a node harness; stdlib only."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ST = Path(__file__).resolve().parent.parent / "src" / "aipandit" / "web" / "static"
NODE = shutil.which("node")


def read(name):
    return (ST / name).read_text(encoding="utf-8")


def node_eval(js):
    harness = ('global.document={createElement:()=>({getContext:()=>({})})};global.window={};global.performance={now:()=>0};'
               'global.requestAnimationFrame=()=>0;require(%s);const A=window.AMLive;' % json.dumps(str(ST / "live.js")))
    r = subprocess.run([NODE, "-e", harness + js], capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class WiringTests(unittest.TestCase):
    def test_files_and_page(self):
        html = read("index.html")
        self.assertTrue((ST / "live.js").exists())
        self.assertLess(html.index("/static/live.js"), html.index("/static/app.js"))
        self.assertEqual(len(re.findall(r"\?v=1\.2\.0", html)), html.count("?v="))
        self.assertNotIn(" style=", html)

    def test_no_inline_style_or_handlers_in_new_markup(self):
        for f in ("app.js", "live.js"):
            src = read(f)
            self.assertIsNone(re.search(r"""<[a-z][^>]*\sstyle\s*=""", src), f)
            self.assertIsNone(re.search(r"""\son(click|load|error|change)\s*=\s*["']""", src), f)

    def test_chat_is_silent_and_talk_speaks(self):
        app = read("app.js")
        self.assertIn("if (!A || !S.talk || !txt) return", app)          # nothing is spoken unless Talk is on
        self.assertIn("data-talk", app)
        self.assertNotIn("S.voice", app)
        self.assertIn("AMLive.mount", app.replace("window.AMLive.mount", "AMLive.mount"))
        self.assertIn('window.AMLive.stop(); window.AMLive.stopListening();', app)   # leaving Ask silences him

    def test_ai_disclosure_kept(self):
        self.assertIn("ai_char", read("app.js"))

    def test_strings_in_three_languages(self):
        i18n = read("i18n11.js")
        keys = ["mode_chat", "mode_talk", "mode_aria", "tap_to_talk", "mic_listening", "speaking", "mic_unsupported", "mic_denied", "mic_btn", "talk_hello", "voice_note"]
        for k in keys:
            self.assertEqual(len(re.findall(r"\b%s:" % k, i18n)), 3, k)

    def test_css_has_modes(self):
        css = read("v11.css")
        for sel in (".modes", "#nvCanvas" if False else ".portrait canvas", ".btn.mic"):
            self.assertIn(sel, css)


@unittest.skipUnless(NODE, "node not installed")
class LiveJsTests(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(subprocess.run([NODE, "--check", str(ST / "live.js")]).returncode, 0)

    def test_lips_close_on_labials_and_open_on_vowels(self):
        out = node_eval("console.log(JSON.stringify({m:A.openness('m'),b:A.openness('b'),pa:A.openness('प'),a:A.openness('a'),aa:A.openness('आ'),o:A.openness('o'),e:A.openness('e'),sp:A.openness(' '),dot:A.openness('.')}))")
        self.assertLess(out["m"], 0.1); self.assertLess(out["b"], 0.1); self.assertLess(out["pa"], 0.1)
        self.assertEqual(out["a"], 1); self.assertEqual(out["aa"], 1)
        self.assertGreater(out["o"], out["e"]); self.assertLess(out["dot"], out["sp"] + 1e-9)

    def test_track_length_matches_text_and_is_bounded(self):
        out = node_eval("const t=A.visemeTrack('Namaste, main NaradVani hoon.');console.log(JSON.stringify({n:t.length,mn:Math.min(...t),mx:Math.max(...t)}))")
        self.assertEqual(out["n"], len("Namaste, main NaradVani hoon."))
        self.assertGreaterEqual(out["mn"], 0); self.assertLessEqual(out["mx"], 1)

    def test_api_surface(self):
        out = node_eval("console.log(JSON.stringify(['mount','setMode','speak','stop','listen','stopListening','micSupported'].map(k=>typeof A[k])))")
        self.assertEqual(set(out), {"function"})

    def test_missing_speech_support_fails_quietly(self):
        out = node_eval("let err='';const r=A.speak('hello','en',{onError:e=>err=e});console.log(JSON.stringify({r:r,err:err,mic:A.micSupported()}))")
        self.assertFalse(out["r"]); self.assertEqual(out["err"], "unsupported"); self.assertFalse(out["mic"])


if __name__ == "__main__":
    unittest.main()
