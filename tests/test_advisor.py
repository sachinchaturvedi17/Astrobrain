import datetime as dt
import unittest
from unittest import mock

import chartkit  # noqa: F401 - activates unittest/pytest bridge when running unittest discover
from aipandit import advisor, brain, reasoner, voice
from aipandit.ashtakoota import RASHIS

TODAY = dt.date(2026, 11, 25)
SIGNS = {"Sun": "Vrishabha", "Moon": "Makara", "Mars": "Kumbha", "Mercury": "Mesha", "Jupiter": "Mithuna", "Venus": "Meena", "Saturn": "Makara",
         "Rahu": "Makara", "Ketu": "Karka"}
SKY = {"Jupiter": {"sign": "Mithuna"}, "Saturn": {"sign": "Meena"}}


def chart(lagna="Kanya", gender="male", dasha=True):
    li = RASHIS.index(lagna)
    pl = {p: {"sign": s, "house": (RASHIS.index(s) - li) % 12 + 1, "retrograde": False} for p, s in SIGNS.items()}
    return {"lagna": lagna, "moon": {"sign": "Makara", "nakshatra": "Shravana"}, "planets": pl, "time_certainty": "exact", "withheld": [],
            "profile": {"gender": gender}, "dasha": {"maha": "Venus", "antar": "Sun", "maha_end": "2031-05-01", "antar_end": "2027-03-01"} if dasha else None}


def fake_ephem(d):
    k = (d - TODAY).days
    return {"Jupiter": RASHIS[(2 + k // 365) % 12], "Saturn": RASHIS[(11 + k // 900) % 12]}


def adv(topic, q, c=None, lang="en", history=None, ephem=fake_ephem):
    return advisor.advise(topic, q, c or chart(), lang, SKY, history or [], ephem, TODAY)


class SheetTests(unittest.TestCase):
    def test_house_lords_and_aspects(self):
        s = reasoner.Sheet(chart())
        self.assertEqual((s.sign(7), s.lord(7)), ("Meena", "Jupiter"))
        self.assertEqual(s.rules("Venus"), [2, 9])
        self.assertIn(7, s.aspect_houses("Saturn"))        # Saturn in the 5th looks at the 7th
        self.assertIn("Saturn", s.aspectors(7))
        self.assertEqual(s.dignity("Venus"), "exalted")
        self.assertEqual(s.relation("Moon", "Saturn"), "conjunct")

    def test_neecha_bhanga_needs_a_kendra_dispositor(self):
        c = chart()
        c["planets"]["Mercury"] = {"sign": "Meena", "house": 7, "retrograde": False}
        self.assertEqual(reasoner.Sheet(c).dignity("Mercury"), "debilitated")
        self.assertTrue(reasoner.Sheet(c).neecha_bhanga("Mercury"))     # Jupiter, lord of Meena, is in the 10th (a kendra)


class IntentAndMemoryTests(unittest.TestCase):
    def test_questions_do_not_create_facts(self):
        self.assertEqual(advisor.extract_slots(["when will I get married"]), {})
        self.assertEqual(advisor.extract_slots(["I am single"]), {"rel": "single"})
        self.assertEqual(advisor.extract_slots(["there is a problem in the relationship"]), {"rel": "trouble"})
        self.assertEqual(advisor.extract_slots(["I have a job but want to switch"]), {"work": "working"})

    def test_a_short_status_word_is_read_as_the_persons_situation(self):
        for q in ("alone", "I am alone", "single", "akela"):
            self.assertEqual(advisor.extract_slots([q]).get("rel"), "single", q)
        self.assertNotEqual(advisor.extract_slots(["when will I get married"]).get("rel"), "single")

    def test_sub_questions_are_told_apart(self):
        want = {"when will I get married": "when", "what kind of partner suits me": "type", "partner type": "type", "love or arranged marriage": "love_arr",
                "what should I be careful about": "caution", "there is a problem in the relationship": "trouble", "should I change my job": "switch",
                "job or business": "business", "how can I earn more": "income", "I have a loan": "debt", "why can't I concentrate": "focus"}
        for q, k in want.items():
            self.assertEqual(advisor.detect_intent(q, "x"), k, q)


class AdviseTests(unittest.TestCase):
    def test_every_answer_carries_a_numbered_working_with_a_tally(self):
        for topic, q in (("marriage", "when will I get married"), ("career", "career kab badhega"), ("wealth", "how can I earn more"), ("education", "how will my exams go")):
            r = adv(topic, q)
            self.assertTrue(r["calc"][0].startswith("1."), topic)
            self.assertTrue(any(line.startswith("Tally") for line in r["calc"]), topic)
            self.assertIn(r["verdict"], ("strong", "good", "mixed", "demanding"))

    def test_when_gives_dated_transit_windows_from_the_moon_when_time_is_unknown(self):
        c = brain._moon_chart(dict(chart(dasha=False), time_certainty="unknown"))
        r = adv("marriage", "when will I get married", c)
        self.assertIn("Chandra Lagna", r["calc"][0])
        self.assertTrue(r["timing"])
        self.assertRegex(r["text"], r"20\d\d")
        self.assertTrue(any("not guessing" in line or "need an exact birth time" in line for line in r["calc"]))   # dasha is never invented

    def test_main_house_lord_in_a_hard_house_steps_the_verdict_down(self):
        r = adv("career", "will I get a promotion")          # 10th lord Mercury sits in the 8th
        self.assertTrue(any(line.startswith("Adjustment") for line in r["calc"]) or r["verdict"] in ("mixed", "demanding"))

    def test_status_is_acknowledged_once_and_changes_the_answer(self):
        r1 = adv("marriage", "tell me about love and marriage")
        self.assertTrue(any("single" in c.lower() for c in r1["quick_replies"]))
        h = [{"role": "user", "text": "tell me about love and marriage"}, {"role": "bot", "topic": "marriage", "intent": r1["intent"], "text": r1["text"]}]
        r2 = adv("marriage", "I am single", history=h)
        self.assertIn("You said you are single", r2["text"])
        self.assertNotEqual(r2["text"], r1["text"])
        self.assertEqual(r2["intent"], "type")
        self.assertEqual(r2["question"], "")

    def test_a_short_follow_up_answers_the_new_sub_question_without_the_same_opening(self):
        r1 = adv("marriage", "love")
        h = [{"role": "user", "text": "love"}, {"role": "bot", "topic": "marriage", "intent": r1["intent"], "text": r1["text"]}]
        r2 = adv("marriage", "alone", history=h)
        self.assertEqual(r2["intent"], "type")
        self.assertIn("You said you are single", r2["text"])
        self.assertNotIn(r1["text"].split("\n\n")[0], r2["text"])       # the verdict paragraph is not repeated
        self.assertNotEqual(r1["text"], r2["text"])
        r3 = adv("marriage", "tell me what kind of partner will suit me", history=h + [
            {"role": "user", "text": "alone"}, {"role": "bot", "topic": "marriage", "intent": r2["intent"], "text": r2["text"]}])
        self.assertNotEqual(r2["text"], r3["text"])                     # a repeated sub-question gets an advance, not a copy
        self.assertIn("will not repeat", r3["text"])

    def test_a_named_field_after_a_studies_answer_is_read_as_a_field_question(self):
        r1 = adv("education", "tell me something about my education")
        h = [{"role": "user", "text": "tell me something about my education"}, {"role": "bot", "topic": "education", "intent": r1["intent"], "text": r1["text"]}]
        r2 = adv("education", "Marketing/Sales", history=h)
        self.assertEqual(r2["intent"], "field")
        self.assertIn("marketing, sales", r2["text"].lower())
        self.assertIn("Mercury", r2["text"])
        self.assertNotEqual(r1["text"], r2["text"])
        self.assertNotIn("A reliable answer", r2["text"])

    def test_phase_without_a_birth_time_gives_the_moving_transits_and_their_end_dates(self):
        c = brain._moon_chart(dict(chart(dasha=False), time_certainty="unknown"))
        r = adv("marriage", "which phase am I in now", c)
        self.assertEqual(r["intent"], "phase")
        self.assertIn("will not invent life-phase", r["text"])
        self.assertRegex(r["text"], r"stays in that sign until about [A-Z][a-z]+ 20\d\d")
        self.assertNotIn("sub-period has its own tone", r["text"])
        self.assertNotEqual(r["text"], voice.TIMING_TAIL[0])

    def test_a_yes_to_the_phase_question_uses_the_specific_phase_reading(self):
        c = dict(chart(dasha=False), time_certainty="unknown")
        h = [{"role": "user", "text": "love"}, {"role": "bot", "topic": "marriage", "intent": "overview", "text": "overview", "expects": "timing"}]
        o = brain.answer("Yes, tell me", c, "en", SKY, use_llm=False, history=h)
        self.assertEqual(o["topic"], "marriage")
        self.assertEqual(o["intent"], "phase")
        self.assertIn("will not invent life-phase", o["answer"])
        self.assertNotIn("sub-period has its own tone", o["answer"])

    def test_a_repeated_question_is_not_answered_with_the_same_text(self):
        r1 = adv("marriage", "when will I get married")
        h = [{"role": "user", "text": "when will I get married"}, {"role": "bot", "topic": "marriage", "intent": r1["intent"], "text": r1["text"]}]
        r2 = adv("marriage", "when will I get married", history=h)
        self.assertNotEqual(r1["text"], r2["text"])
        self.assertIn("As I showed a moment ago", r2["text"])
        self.assertNotIn("when", [k for k, _e, _h in advisor.FOLLOW["marriage"] if k in [x for x in r2["quick_replies"]]])

    def test_trouble_reads_strain_points_dasha_and_gives_guidance_without_predicting_a_breakup(self):
        r = adv("marriage", "there is a problem in the relationship")
        self.assertEqual(r["intent"], "trouble")
        self.assertIn("What is straining things", r["text"])
        self.assertIn("What you can do", r["text"])
        low = r["text"].lower()
        for bad in ("divorce", "will break", "will end", "will separate", "will die"):
            self.assertNotIn(bad, low)

    def test_yes_after_trouble_moves_to_the_phase_reading(self):
        r1 = adv("marriage", "there is a problem in the relationship")
        h = [{"role": "user", "text": "there is a problem in the relationship"}, {"role": "bot", "topic": "marriage", "intent": "trouble", "text": r1["text"]}]
        self.assertEqual(adv("marriage", "Yes, tell me", history=h)["intent"], "phase")

    def test_love_or_arranged_counts_indicators(self):
        r = adv("marriage", "love marriage or arranged?")
        self.assertEqual(r["intent"], "love_arr")
        self.assertRegex(r["text"], r"leans|either way")
        self.assertTrue(any("indicator" in x for x in r["calc"]))

    def test_hinglish_is_written_in_hinglish(self):
        r = adv("marriage", "meri shaadi kab hogi", lang="hg")
        self.assertIn("aapka chart madadgaar hai", r["text"])
        self.assertTrue(any("Joda-ghata" in line for line in r["calc"]))

    def test_no_ephemeris_means_no_invented_dates(self):
        r = adv("marriage", "when will I get married", chart(dasha=False), ephem=None)
        self.assertFalse(r["timing"])
        self.assertIn("cannot give dated stretches", r["text"])

    def test_sade_sati_dates_come_from_the_transit_calendar(self):
        c = chart()
        c["moon"] = {"sign": "Meena", "nakshatra": "Revati"}
        sheet = reasoner.Sheet(c, "en", {"Saturn": {"sign": "Meena"}}, TODAY)
        self.assertEqual(sheet.sade_sati(), "peak")
        note = advisor._sade_sati_note(sheet, fake_ephem)
        self.assertRegex(note, r"movement of the planets.*20\d\d")

    def test_brain_answer_end_to_end_keeps_the_topic_for_short_follow_ups(self):
        c = chart()
        h = []
        for q in ("tell me about marriage", "when?", "I am single"):
            o = brain.answer(q, c, "en", SKY, use_llm=False, history=h)
            self.assertEqual(o["topic"], "marriage", q)
            self.assertTrue(o["calc"], q)
            h += [{"role": "user", "text": q}, {"role": "bot", "text": o["answer"], "topic": o["topic"], "expects": "", "intent": o.get("intent") or ""}]


class HindiRoutingTests(unittest.TestCase):
    def test_hindi_never_uses_the_hinglish_advisor(self):
        self.assertIsNone(adv("career", "मेरा करियर कैसा रहेगा?", lang="hi"))
        for q in ("मेरा करियर कैसा रहेगा?", "मेरी शादी कब होगी?"):
            o = brain.answer(q, chart(), "hi", SKY, use_llm=False)
            self.assertEqual(o["composer"], "voice", q)
            self.assertFalse(o["calc"], q)
            self.assertIsNone(o["intent"], q)
            self.assertNotRegex(o["answer"], r"[A-Za-z]", q)       # Devanagari only: no Hinglish body or mixed-script dates

    def test_hindi_follow_ups_stay_in_devanagari(self):
        c, h = chart(), []
        for q in ("मेरी शादी कब होगी?", "कब?", "मैं अकेला हूँ।"):
            o = brain.answer(q, c, "hi", SKY, use_llm=False, history=h)
            self.assertEqual(o["lang"], "hi", q)
            self.assertNotRegex(o["answer"], r"[A-Za-z]", q)
            h += [{"role": "user", "text": q}, {"role": "bot", "text": o["answer"], "topic": o["topic"], "expects": "", "intent": o.get("intent") or ""}]

    def test_hindi_health_and_safety_replies_are_devanagari(self):
        for q, kind in (("मेरा स्वास्थ्य कैसा रहेगा?", None), ("मेरी बीमारी कब ठीक होगी?", "medical")):
            o = brain.answer(q, chart(), "hi", SKY, use_llm=False)
            self.assertNotRegex(o["answer"], r"[A-Za-z]", q)
            self.assertEqual(o["safety"], kind, q)


class LivePathGateTests(unittest.TestCase):
    """The production /api/v10/ask path must not ship unverified model prose or chart material in a hard stop."""

    OUT = {"title": "Career", "reasons": ["Sun is strong in the chart."], "timing": [], "calc": [], "caveats": []}
    DRAFT = "Your chart shows a mixed picture for career. Sun is strong here, so steady effort helps."

    def test_a_paraphrase_may_reword_but_not_add_claims(self):
        ok = "Your chart shows some strengths for career. With steady effort, things move forward."
        self.assertTrue(brain._polish_ok(self.DRAFT, ok, "en", self.OUT))
        for bad in ("You will definitely become a manager in 2027, guaranteed.",
                    "Mars in your 7th house brings a promotion.",
                    "Your career will be perfect and you will earn crores."):
            self.assertFalse(brain._polish_ok(self.DRAFT, bad, "en", self.OUT), bad)

    def test_the_polish_must_stay_in_the_requested_script(self):
        hindi = "आपकी कुंडली करियर के लिए अच्छी है और मेहनत से तरक्की होती है।"
        self.assertTrue(brain._polish_ok("आपकी कुंडली ठीक है।", hindi, "hi", self.OUT))
        self.assertFalse(brain._polish_ok(self.DRAFT, hindi, "en", self.OUT))
        self.assertFalse(brain._polish_ok(self.DRAFT, "Your career looks good and steady.", "hi", self.OUT))

    def test_a_rejected_polish_falls_back_to_the_checked_draft(self):
        c = chart()
        original_adv, original_pol = brain.advisor.advise, brain._llm_polish
        brain.advisor.advise = lambda *a, **k: None                    # force the older voice path, which uses the polish
        brain._llm_polish = lambda q, out, lang: "You will definitely become a manager in 2027, guaranteed."
        try:
            o = brain.answer("How is my career?", c, "en", use_llm=True)
        finally:
            brain.advisor.advise, brain._llm_polish = original_adv, original_pol
        self.assertNotEqual(o["composer"], "llm")
        self.assertNotIn("2027", o["answer"])
        self.assertNotIn("definitely", o["answer"])
        self.assertTrue(o["answer"])

    def test_a_hard_stop_never_carries_chart_material(self):
        self.assertEqual(brain._fixed_reply("Please call Tele-MANAS on 14416."), "Please call Tele-MANAS on 14416.")
        with mock.patch.dict(brain.SAFETY_TEXT["medical"], {"en": "Mars in your 6th house will cure the disease."}):
            o = brain.answer("I have cancer", chart(), "en", use_llm=False)
        self.assertEqual(o["composer"], "safety")
        self.assertEqual(o["answer"], brain.SAFE_MINIMAL)

    def test_every_hard_stop_constant_is_entity_free_in_all_languages(self):
        for kind, texts in brain.SAFETY_TEXT.items():
            for lang, text in texts.items():
                self.assertEqual(brain._fixed_reply(text), text, (kind, lang))

    def test_shared_crisis_hard_stop_and_safety_violation_blocking(self):
        for q in ("I don't want to live anymore", "mujhe jeena nahi hai", "मुझे जीने का मन नहीं है"):
            o = brain.answer(q, chart(), "en", use_llm=False)
            self.assertEqual(o["safety"], "self_harm", q)
            self.assertIn("14416", o["answer"], q)
        with mock.patch.dict(brain.SAFETY_TEXT["medical"], {"en": "You will definitely be cured, 100% guaranteed."}):
            o = brain.answer("I have cancer", chart(), "en", use_llm=False)
        self.assertEqual(o["answer"], brain.SAFE_MINIMAL)

    def test_minor_profile_blocks_marriage_and_logs_advisor_fallbacks(self):
        minor_chart = dict(chart(), profile={"gender": "male", "minor": True})
        o = brain.answer("When will I get married?", minor_chart, "en", use_llm=False)
        self.assertEqual(o["safety"], "minor_topic")
        self.assertIn("under 18", o["answer"])
        with mock.patch.object(brain.advisor, "advise", side_effect=RuntimeError("boom")):
            with self.assertLogs("aipandit.brain", level="WARNING") as cm:
                fallback = brain.answer("How is my career?", chart(), "en", use_llm=False)
        self.assertTrue(fallback["answer"])
        self.assertTrue(any("advisor.advise failed" in msg for msg in cm.output))


class LaymanTests(unittest.TestCase):
    JARGON = ("tally", "verdict", "lord ", " lord", "mahadasha", "antardasha", "aspect", "house", "bhava", "lagna", "natal", "transit", "debilitat", "exalt", "dusthana", "kendra", "yoga")

    def test_visible_answers_use_no_astrology_jargon_but_calc_keeps_the_working(self):
        for topic, qs in (("marriage", ["when will I get married", "what kind of partner suits me", "there is a problem in the relationship", "what should I be careful about"]),
                          ("love", ["how does romance work in my chart", "can an old relationship reconcile", "when will love blossom"]),
                          ("career", ["when will my career grow", "should I change my job"]),
                          ("wealth", ["how can I earn more"]),
                          ("education", ["how will my exams go"]),
                          ("health", ["how is my overall vitality", "what daily routine suits me"])):
            for q in qs:
                r = adv(topic, q)
                low = r["text"].lower()
                for bad in self.JARGON:
                    self.assertNotIn(bad, low, (q, bad))
                self.assertNotRegex(r["text"], r"\b\d+(st|nd|rd|th) house", q)
                self.assertTrue(r["calc"], q)                          # the backend working is still produced
                self.assertTrue(any("house" in line.lower() for line in r["calc"]), q)


class SixFieldTrainingAndCalculationTests(unittest.TestCase):
    def test_internet_fetcher_and_corpus_cover_all_six_fields(self):
        from aipandit import training_ingestion as ti
        fetcher = ti.InternetAstrologyFetcher()
        records = fetcher.fetch_all_6fields(allow_network=False, max_shastra_per_field=5)
        self.assertGreaterEqual(len(records), 12)
        covered = {r["topic"] for r in records}
        for fld in ti.TARGET_FIELDS:
            self.assertIn(fld, covered, fld)
        for rec in records:
            vr = ti.AnswerQualityValidator.validate_passage(rec)
            self.assertTrue(vr.passed, (rec["id"], vr.violations))

    def test_validation_framework_blocks_unsafe_and_ungrounded_answers(self):
        from aipandit import training_ingestion as ti
        c = chart()
        good = adv("career", "when will my career grow", c)
        vr_ok = ti.AnswerQualityValidator.validate_qa(
            "when will my career grow", good["text"], good["calc"], c, "career", "en", SKY
        )
        self.assertTrue(vr_ok.passed, vr_ok.violations)
        self.assertEqual(vr_ok.ungrounded_entities, [])

        vr_bad = ti.AnswerQualityValidator.validate_qa(
            "when will my career grow",
            "You will definitely get a 100% guaranteed promotion in 1999 and cure cancer in the 10th house.",
            good["calc"], c, "career", "en", SKY,
        )
        self.assertFalse(vr_bad.passed)
        self.assertTrue(any("safety:" in v for v in vr_bad.violations), vr_bad.violations)
        self.assertIn("year:1999", vr_bad.ungrounded_entities)

    def test_sample_chart_calculations_cover_all_six_fields_with_zero_errors(self):
        from aipandit import training_ingestion as ti
        samples = ti.SampleChartCalculator.generate_sample_calculations_all_fields(lang="en")
        self.assertEqual(set(samples.keys()), set(ti.TARGET_FIELDS))
        for fld, res in samples.items():
            self.assertTrue(res["validation"]["passed"], (fld, res["validation"]))
            self.assertTrue(res["calc"][0].startswith("1."), fld)
            self.assertTrue(any(line.startswith("Tally") for line in res["calc"]), fld)
            self.assertIn(res["verdict"], ("strong", "good", "mixed", "demanding"), fld)
            self.assertTrue(res["houses"], fld)
            self.assertTrue(res["karakas"], fld)

    def test_permutation_training_session_trains_all_six_fields_and_languages(self):
        from aipandit import training_ingestion as ti
        out = ti.run_training_session(
            duration_seconds=5.0,
            max_permutations=180,
            allow_network=False,
            persist=False,
        )
        rep = out["report"]
        self.assertEqual(rep["sample_calculations_verified"], 6)
        self.assertEqual(rep["permutations_rejected"], 0)
        self.assertEqual(rep["pass_rate"], 100.0)
        self.assertGreaterEqual(rep["permutations_passed"], 60)


if __name__ == "__main__":
    unittest.main()

