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
    def test_answer_is_plain_language_not_house_numbers(self):
        for topic in ("education", "career", "love", "money"):
            o = ask(topic)
            low = o["answer"].lower()
            for bad in ("house", "lord", "bhava", "lagna"):
                self.assertNotIn(bad, low, (topic, o["answer"]))
            self.assertTrue(o["followup_question"] and o["quick_replies"])
            self.assertTrue(o["reasons"], "technical reasons stay available behind 'Why this answer?'")

    def test_follow_up_continues_the_conversation(self):
        o = ask("education")
        self.assertEqual(o["expects"], "field")
        o2 = ask("marketing", hist(o))
        self.assertEqual(o2["topic"], "education")
        self.assertIn("Marketing", o2["answer"])
        self.assertEqual(o2["expects"], "timing")
        o3 = ask("yes", hist(o2))
        self.assertIn("Jupiter", o3["answer"])
        self.assertIn("Mar 2027", o3["answer"])

    def test_career_asks_status_then_field(self):
        o = ask("mera career kaisa rahega")
        self.assertEqual((o["lang"], o["expects"]), ("hg", "career_status"))
        o2 = ask("Job mein hoon", hist(o), lang="hg")
        self.assertEqual(o2["expects"], "field")

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
