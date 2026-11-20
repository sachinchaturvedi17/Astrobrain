"""Every fixed sentence the system itself speaks. Fixed on purpose: nothing here is model-written, so it
can be reviewed once (ideally by a native speaker and an astrologer) and trusted afterwards.
The gates accept framing/caveat text only if it is one of these (or contains no chart entity at all).
English only for now; Hindi/Hinglish rendering is a Phase 4 item and needs native review.
"""
from __future__ import annotations

SCOPES = ("career", "marriage", "wealth", "education", "children", "character", "mind", "status", "family", "general")
DECLINED = ("medical", "financial", "legal")

INTRO_OVERVIEW = ("Here is what stands out in your chart, ordered by how much weight I would give it. "
                  "These come from the traditional Parashari rules.")
INTRO_DASHA = "Here is the period your chart is running through right now."
INTRO_DECLINED_ONLY = "Here is what I can and cannot help with."
INTRO_COMBINED = ("Here is what stands out, through two separate lenses: your kundli (traditional Parashari rules) and "
                  "your birth-date numerology. I keep them apart and point out where both single out the same planet.")
INTRO_NUMEROLOGY = "Here are your numbers and what the Indian numerology tradition says about them."
CAVEAT_NUMEROLOGY = ("Numerology is a modern popular tradition with no classical Vedic text behind it and no proven "
                     "predictive record. Treat it as one more lens for reflection, not as extra proof for the kundli.")
CAVEAT_NONAME = ("Your name number needs your name in English letters; share it if you want that number included.")
INVITE = ("Ask me about a specific area, for example career, wealth, character or the running dasha period, "
          "and I will go deeper.")
CAVEAT_TENDENCY = "These are traditional readings: tendencies to reflect on, not a prediction of what will happen."
CAVEAT_PROVISIONAL = ("The rule set is still being reviewed by practising astrologers; readings marked provisional "
                      "have not yet been audited by one.")
CAVEAT_TIME = ("Your birth time is uncertain, so I only state what holds across the whole range of possible times "
               "and leave out anything that depends on the exact minute.")
CAVEAT_TIMING = ("I cannot give dates for when events will happen; I can describe the running period but not "
                 "predict timing.")
CAVEAT_NOREADINGS = "Nothing in your chart met the bar for a reading on this topic."
CAVEAT_NODASHA = "I could not work out your running period from the birth details available."
CAVEAT_UNDETERMINED = ("Some rules could not be checked because they depend on birth details I could not "
                       "establish with confidence, so I have left them out rather than guess.")

_DECLINE = {
    "medical": "I do not give medical advice or diagnoses; please speak to a doctor about that part of your question.",
    "financial": "I do not give financial or investment advice; please speak to a qualified adviser about that part.",
    "legal": "I do not give legal advice; please speak to a lawyer about that part of your question.",
}


def intro_targeted(scope: str) -> str:
    return f"Here is what your chart says about {scope}, according to the traditional Parashari rules I have encoded."


def intro_combined_targeted(scope: str) -> str:
    return (f"Here is what your kundli and your birth-date numerology say about {scope}. I keep the two lenses "
            "separate and point out where both single out the same planet.")


def caveat_coverage(scope: str, minor: bool = False) -> str:
    if minor and scope == "marriage":
        return "I do not discuss marriage or relationships for charts of people under 18."
    return f"I do not have any readings for {scope} yet, so I will not guess."


def caveat_declined(topic: str) -> str:
    return _DECLINE[topic]


# ---- hard-stop replies -----------------------------------------------------------------------------
CRISIS = ("I'm really sorry you are in this much pain, and I'm not going to talk about charts right now. "
          "You matter more than any reading. If you might act on these thoughts or are in danger, please call "
          "your local emergency number now.\n\n"
          "In India you can reach Tele-MANAS on 14416 or 1-800-891-4416, or KIRAN on 1800-599-0019 (24x7, many "
          "languages). Outside India, findahelpline.com lists services by country.\n\n"
          "If you can, please tell someone near you how you are feeling. I'm here to listen too.")
DEATH = ("I do not make statements about lifespan or when someone may die. No chart can honestly tell that, and I "
         "will not pretend otherwise. I am happy to look at other areas, such as career, character or the "
         "running dasha period.")
SAFE_MINIMAL = ("I could not prepare a reliable answer to that just now. Please try rephrasing, or ask about a "
                "specific area such as career, wealth or character.")
NEED_BIRTH = "I need your birth details first. Please share your date, time and place of birth."


def all_fixed() -> frozenset:
    s = {INTRO_OVERVIEW, INTRO_DASHA, INTRO_DECLINED_ONLY, INVITE, CAVEAT_TENDENCY, CAVEAT_PROVISIONAL, CAVEAT_TIME, CAVEAT_TIMING,
         CAVEAT_NOREADINGS, CAVEAT_NODASHA, CAVEAT_UNDETERMINED, CRISIS, DEATH, SAFE_MINIMAL, NEED_BIRTH,
         INTRO_COMBINED, INTRO_NUMEROLOGY, CAVEAT_NUMEROLOGY, CAVEAT_NONAME}
    s |= set(_DECLINE.values())
    for sc in SCOPES:
        s.add(intro_targeted(sc))
        s.add(intro_combined_targeted(sc))
        s.add(caveat_coverage(sc))
        s.add(caveat_coverage(sc, minor=True))
    return frozenset(s)


from . import phrasebook_hg as hg          # noqa: E402  (Hinglish draft, see that module)
from . import phrasebook_hi as hi          # noqa: E402  (Hindi draft, see that module)

FIXED = all_fixed() | hi.all_fixed() | hg.all_fixed()


def bundle(lang: str):
    """The phrasebook module for a language ('en', 'hi' or 'hg'); anything else is English."""
    import sys
    return hi if lang == "hi" else hg if lang == "hg" else sys.modules[__name__]


def is_system_text(text: str) -> bool:
    return text in FIXED
