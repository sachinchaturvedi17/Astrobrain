"""v1.1 conversation layer, Chandra Lagna fallback and horoscope areas. Pure: no ephemeris, no network."""
import unittest

from aipandit import brain, gochara_live, voice

CHART = {"lagna": "Mithuna", "moon": {"sign": "Dhanu", "nakshatra": "Mula"}, "time_certainty": "exact",
         "planets": {"Sun": {"sign": "Vrishabha", "house": 12}, "Moon": {"sign": "Dhanu", "house": 7}, "Mercury": {"sign": "Mithuna", "house": 1},
                     "Jupiter": {"sign": "Karka", "house": 2}, "Venus": {"sign": "Simha", "house": 3}, "Saturn": {"sign": "Mesha", "house": 11},
                     "Mars": {"sign": "Karka", "house": 2}, "Rahu": {"sign": "Kumbha", "house": 9}},
         "dasha": {"maha": "Moon", "antar": "Jupiter", "maha_end": "2030-01-01", "antar_end": "2027-03-01"}}
SKY = {"Sun": {"sign": "Tula"}, "Moon": {"sign": "Mesha"}, "Mars": {"sign": "Kanya"}, "Mercury": {"sign": "Tula"}, "Jupiter": {"sign": "Mithuna"},
       "Venus": {"sign": "Vrishchika"}, "Saturn": {"sign": "Meena"}, "Rahu": {"sign": "Kumbha"}}
CHIPS = {"en": ["How is my career going to be?", "Tell me about love and marriage", "How are my studies?", "What about money?", "Which phase am I in right now?"],
         "hg": ["Mera career kaisa rahega?", "Pyaar aur shaadi ke baare mein batao", "Meri padhai kaisi rahegi?", "Paise ka kya haal hai?", "Abhi main kaunse daur mein hoon?"],
         "hi": ["मेरा करियर कैसा रहेगा?", "प्रेम और विवाह के बारे में बताइए", "मेरी पढ़ाई कैसी रहेगी?", "पैसे का क्या हाल है?", "अभी मैं किस दौर में हूँ?"]}
WANT = ["career", "marriage", "education", "wealth", "dasha"]


def ask(q, history=None, chart=CHART, lang="en"):
    return brain.answer(q, chart, lang, None, use_llm=False, history=history)


def hist(o):
    return [{"role": "bot", "topic": o["topic"], "expects": o["expects"]}]


class VoiceTests(unittest.TestCase):
    def test_every_quick_reply_parses_back_to_its_own_option(self):
        for lang, li in voice.LI.items():
            for expects, a in voice.ASK.items():
                for opt in a["opts"]:
                    label = voice.FIELDS[opt[0]][2][li] if expects == "field" else opt[2][li]
                    self.assertEqual(voice.parse_reply(expects, label), opt[0], (lang, expects, label))

    def test_language_follows_how_the_person_writes(self):
        self.assertEqual(voice.detect_lang("mera career kaisa rahega", "en"), "hg")
        self.assertEqual(voice.detect_lang("how is my career", "en"), "en")
        self.assertEqual(voice.detect_lang("मेरा करियर", "en"), "hi")
        self.assertEqual(voice.detect_lang("career", "hg"), "hg")

    def test_suggestion_chips_route_to_the_right_topic(self):
        for lang, chips in CHIPS.items():
            self.assertEqual([brain.classify(c) for c in chips], WANT, lang)


class ConversationTests(unittest.TestCase):
    def test_answer_shows_the_working_and_is_specific(self):
        for topic in ("education", "career", "love", "money"):
            o = ask(topic)
            self.assertTrue(o["calc"], topic)                      # the calculation is shown with every chart answer
            self.assertTrue(any("Tally" in line for line in o["calc"]), topic)
            self.assertTrue(o["quick_replies"], topic)
            self.assertRegex(o["answer"], r"supportive|mixed|patience", topic)

    def test_follow_ups_are_specific_and_never_repeat(self):
        h = []
        seen = set()
        for q in ("education", "Which field suits me, I like medical", "why can't I concentrate", "how will my exams go", "when will I succeed"):
            o = ask(q, h)
            self.assertEqual(o["topic"], "education", q)
            self.assertNotIn(o["answer"], seen, q)                 # no canned paragraph twice
            seen.add(o["answer"])
            h += [{"role": "user", "text": q}, {"role": "bot", "text": o["answer"], "topic": o["topic"], "expects": o["expects"] or "", "intent": o.get("intent") or ""}]
        self.assertIn("medic", "".join(seen).lower())

    def test_stated_facts_are_remembered_and_not_asked_again(self):
        o = ask("tell me about love and marriage")
        self.assertTrue(any("single" in c.lower() for c in o["quick_replies"]))          # asked once, as a tap, not a blocking question
        h = [{"role": "user", "text": "tell me about love and marriage"}, {"role": "bot", "topic": o["topic"], "intent": o.get("intent") or "", "text": o["answer"]}]
        o2 = ask("I am single", h)
        self.assertEqual(o2["topic"], "marriage")
        self.assertIn("single", o2["answer"].lower())
        self.assertNotIn("single", " ".join(o2["quick_replies"]).lower())
        self.assertFalse(o2["followup_question"])

    def test_career_status_is_read_from_free_text(self):
        o = ask("mera career kaisa rahega", lang="hg")
        self.assertEqual(o["lang"], "hg")
        o2 = ask("I have a job but want to switch, when", [{"role": "user", "text": "mera career kaisa rahega"}, {"role": "bot", "topic": "career", "text": o["answer"], "intent": o.get("intent") or ""}])
        self.assertEqual((o2["topic"], o2["intent"]), ("career", "switch"))
        self.assertIn("working", o2["answer"])

    def test_new_topic_beats_stale_follow_up(self):
        o = ask("education")
        o2 = ask("tell me about my marriage", hist(o))
        self.assertEqual(o2["topic"], "marriage")

    def test_greeting_and_safety(self):
        self.assertEqual(ask("hi")["topic"], "greet")
        s = ask("I want to end my life", [{"role": "bot", "topic": "career", "expects": "career_status"}])
        self.assertEqual(s["safety"], "self_harm")

    def test_chandra_lagna_fallback_when_birth_time_unknown(self):
        unknown = dict(CHART, time_certainty="unknown", lagna="")
        o = ask("education", None, unknown)
        self.assertFalse(o.get("needs_profile"))
        self.assertEqual(o["confidence"]["level"], "low")
        self.assertIn("Moon sign", o["confidence"]["why"])
        mc = brain._moon_chart(unknown)
        self.assertEqual(mc["lagna"], "Dhanu")
        self.assertEqual(mc["planets"]["Moon"]["house"], 1)
        self.assertEqual(mc["planets"]["Mercury"]["house"], 7)  # Mithuna is the 7th sign from Dhanu

    def test_without_any_chart_it_asks_for_birth_details(self):
        o = ask("education", None, None)
        self.assertTrue(o["needs_profile"])


class HoroscopeTests(unittest.TestCase):
    def test_four_life_areas_with_bounded_scores_in_every_language(self):
        for lang in ("en", "hg", "hi"):
            r = gochara_live.reading_for_moon_sign("Dhanu", SKY, lang)
            self.assertEqual([a["key"] for a in r["areas"]], ["love", "career", "health", "money"])
            self.assertTrue(all(0 <= a["score"] <= 100 and a["text"] for a in r["areas"]))
            self.assertTrue(r["paragraph"])

    def test_no_invented_lucky_numbers(self):
        r = gochara_live.reading_for_moon_sign("Dhanu", SKY, "en")
        self.assertFalse({"lucky", "colour", "color"} & set(r["paragraph"].lower().split()))


if __name__ == "__main__":
    unittest.main()


class V111Tests(unittest.TestCase):
    """New in 1.1.1: computed dosha checks, FAQ knowledge, no-upsell remedies, new topics."""

    def test_manglik_is_computed_from_the_chart_and_not_scary(self):
        o = ask("is there manglik dosha in my kundli")
        self.assertEqual(o["topic"], "manglik")
        self.assertIn("does not stop marriage", o["answer"])

    def test_conceptual_manglik_question_gets_reference_then_offers_to_check(self):
        o = ask("what is manglik dosha")
        self.assertEqual(o["expects"], "dosha_check")
        o2 = ask("yes", hist(o))
        self.assertIn("In your chart", o2["answer"])

    def test_kaal_sarp_is_honest_about_sign_level_data(self):
        from aipandit import doshas
        ch = {"planets": {p: {"sign": s} for p, s in zip(("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"),
                                                         ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Mesha"))}}
        self.assertEqual(doshas.kaal_sarp(ch), "borderline")  # Sun shares Rahu's sign: degrees would decide
        ch["planets"]["Sun"]["sign"] = "Vrishabha"
        ch["planets"]["Saturn"]["sign"] = "Kanya"
        self.assertEqual(doshas.kaal_sarp(ch), "formed")
        self.assertEqual(doshas.kaal_sarp(CHART), "absent")

    def test_remedies_never_sell(self):
        for q in ("remedy for saturn", "should I wear a gemstone", "do pujas really work"):
            a = ask(q)["answer"].lower()
            self.assertTrue("never" in a or "not" in a, q)
            for bad in ("buy now", "rs.", "price", "₹", "book a puja"):
                self.assertNotIn(bad, a)

    def test_new_topics_foreign_property_and_faq(self):
        o = ask("will I settle abroad")
        self.assertEqual(o["topic"], "foreign")
        self.assertTrue(o["calc"])
        self.assertEqual(ask("when will I buy a house")["topic"], "property")
        o = ask("What is sade sati?", None, None)
        self.assertIn("seven and a half", o["answer"])
        self.assertEqual(ask("kundli milan kaise hota hai")["action"], "compat")

    def test_every_faq_entry_is_original_and_searchable(self):
        from aipandit import kb_faq, retrieval
        self.assertGreaterEqual(len(kb_faq.FAQ), 28)
        for title, tags, text in kb_faq.FAQ:
            self.assertGreater(len(text), 120)
            hit = retrieval.search(title + " " + " ".join(tags[:4]), k=8, tiers=("core",))
            self.assertTrue(hit and any(h["title"] == title for h in hit), title)
