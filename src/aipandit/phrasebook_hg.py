"""Hinglish (Hindi in Roman script, the way Indians chat) versions of every fixed system sentence.
Same names and meaning as phrasebook.py / phrasebook_hi.py.

DRAFT: written by the assistant, NOT yet reviewed by a native speaker or an astrologer. Neutral in grammatical gender
(no first-person verbs) because the Pandit's persona gender is undecided. Avoids future-tense verb forms about the
person, so the Hinglish safety patterns stay strict.
"""
from __future__ import annotations

SCOPES = ("career", "marriage", "wealth", "education", "children", "character", "mind", "status", "family", "general")
DECLINED = ("medical", "financial", "legal")
SCOPE_HG = {"career": "career", "marriage": "shaadi aur rishte", "wealth": "dhan", "education": "padhai",
            "children": "santan", "character": "swabhav", "mind": "mann", "status": "pratishtha", "family": "parivaar",
            "general": "saamanya baatein"}

INTRO_OVERVIEW = ("Yeh aapki kundli ki mukhya baatein hain, mahatva ke kram mein. Yeh paramparik Parashari niyamon par aadhaarit hain.")
INTRO_COMBINED = ("Yeh mukhya baatein do alag nazariyon se hain: aapki kundli (paramparik Parashari niyam) aur janm-tithi ka "
                  "numerology. Dono ko alag rakha gaya hai, aur jahan dono ek hi grah ki taraf ishara karte hain, woh bataya gaya hai.")
INTRO_NUMEROLOGY = "Yeh aapke ank hain aur Indian numerology ki parampara unke baare mein kya kehti hai."
INTRO_DASHA = "Aapki kundli mein abhi jo dasha chal rahi hai, woh yeh hai."
INTRO_DECLINED_ONLY = "Yahan bataya gaya hai ki kis baat mein madad mil sakti hai aur kis mein nahi."
INVITE = ("Kisi khaas topic ke baare mein poochhiye, jaise career, dhan, swabhav, numerology ya chal rahi dasha, "
          "toh us par vistaar se baat ho sakti hai.")
CAVEAT_TENDENCY = "Yeh paramparik paath hain, yaani sochne layak rujhaan; yeh bhavishyavani nahi hain, koi prediction nahi."
CAVEAT_PROVISIONAL = ("Niyamon ki samiksha abhi practising jyotishiyon dwara ho rahi hai; 'abhi jaanch baaki' chinhit paathon ko "
                      "abhi kisi jyotishi ne audit nahi kiya hai.")
CAVEAT_NUMEROLOGY = ("Numerology ek aadhunik lokpriya parampara hai; iske peeche koi shastriya Vedic granth ya saabit hua "
                     "predictive record nahi hai. Ise sochne ka ek aur nazariya maniye, kundli ke liye atirikt saboot nahi.")
CAVEAT_NONAME = "Name number ke liye English letters mein aapka naam chahiye; ise jodna ho toh naam bataiye."
CAVEAT_TIME = ("Aapka janm samay pakka nahi hai, isliye sirf wahi baatein batayi gayi hain jo possible samay ki poori range mein "
               "ek jaisi rehti hain; jo exact minute par nirbhar hain, unhein chhod diya gaya hai.")
CAVEAT_TIMING = ("Ghatnayein kab hongi, iski tithiyan nahi batayi ja sakti; chal rahi dasha batayi ja sakti hai, par samay ki "
                 "bhavishyavani nahi.")
CAVEAT_NOREADINGS = "Is topic par aapki kundli mein batane layak koi paath nahi mila."
CAVEAT_NODASHA = "Uplabdh janm vivaran se chal rahi dasha nikali nahi ja saki."
CAVEAT_UNDETERMINED = ("Kuch niyamon ki jaanch nahi ho saki, kyunki woh aise janm vivaran par nirbhar hain jinhein bharose ke saath tay "
                       "nahi kiya ja saka; andaza lagane ke bajay unhein chhod diya gaya hai.")

_DECLINE = {
    "medical": "Medical salah ya rog-nidaan yahan nahi diya jata; is hisse ke liye kripya doctor se milein.",
    "financial": "Financial ya investment salah yahan nahi di jati; is hisse ke liye kripya kisi yogya adviser se milein.",
    "legal": "Legal salah yahan nahi di jati; is hisse ke liye kripya vakeel se milein.",
}
LABEL_PROVISIONAL = "abhi jaanch baaki"
LABEL_CHECKED = "srot se jaanchi hui"


def intro_targeted(scope: str) -> str:
    return f"Yeh {SCOPE_HG.get(scope, scope)} ke baare mein aapki kundli ki baatein hain, paramparik Parashari niyamon ke anusaar."


def intro_combined_targeted(scope: str) -> str:
    return (f"Yeh {SCOPE_HG.get(scope, scope)} ke baare mein aapki kundli aur janm-tithi ke numerology ki baatein hain. "
            "Dono nazariye alag rakhe gaye hain, aur jahan dono ek hi grah ki taraf ishara karte hain, woh bataya gaya hai.")


def caveat_coverage(scope: str, minor: bool = False) -> str:
    if minor and scope == "marriage":
        return "18 saal se kam umar ke vyakti ki kundli ke liye shaadi ya rishton par charcha nahi ki jati."
    return f"{SCOPE_HG.get(scope, scope)} ke liye abhi koi paath uplabdh nahi hai, isliye andaza nahi lagaya jayega."


def caveat_declined(topic: str) -> str:
    return _DECLINE[topic]


CRISIS = ("Aap jis dard se guzar rahe hain, uske liye sach mein dukh hai, aur abhi kundli ki baat karna theek nahi hoga. "
          "Aap kisi bhi paath se kahin zyada zaroori hain. Agar aap khud ko nuksan pahunchane ke baare mein soch rahe hain ya khatre mein hain, "
          "toh kripya abhi apne local emergency number par call karein.\n\n"
          "India mein aap Tele-MANAS se 14416 ya 1-800-891-4416 par, ya KIRAN se 1800-599-0019 par baat kar sakte hain "
          "(24x7, kai bhashaon mein). India ke bahar findahelpline.com desh ke hisaab se sewayein batata hai.\n\n"
          "Ho sake toh apne aas-paas kisi ko bataiye ki aap kaisa mehsoos kar rahe hain. Main bhi sunne ke liye yahan hoon.")
DEATH = ("Jeevan ki avadhi ya mrityu ke samay ke baare mein yahan koi kathan nahi kiya jata. Koi kundli yeh imaandaari se nahi bata sakti, "
         "aur aisa dikhava karna theek nahi hoga. Career, swabhav ya chal rahi dasha jaise doosre topics par baat ho sakti hai.")
SAFE_MINIMAL = ("Abhi is sawaal ka bharosemand jawab taiyaar nahi ho saka. Kripya doosre shabdon mein poochhiye, "
                "ya kisi khaas topic, jaise career, dhan ya swabhav ke baare mein poochhiye.")
NEED_BIRTH = "Pehle aapka janm vivaran chahiye. Kripya janm ki tareekh, samay aur sthaan bataiye."


def all_fixed() -> frozenset:
    s = {INTRO_OVERVIEW, INTRO_COMBINED, INTRO_NUMEROLOGY, INTRO_DASHA, INTRO_DECLINED_ONLY, INVITE, CAVEAT_TENDENCY,
         CAVEAT_PROVISIONAL, CAVEAT_NUMEROLOGY, CAVEAT_NONAME, CAVEAT_TIME, CAVEAT_TIMING, CAVEAT_NOREADINGS,
         CAVEAT_NODASHA, CAVEAT_UNDETERMINED, CRISIS, DEATH, SAFE_MINIMAL, NEED_BIRTH}
    s |= set(_DECLINE.values())
    for sc in SCOPES:
        s |= {intro_targeted(sc), intro_combined_targeted(sc), caveat_coverage(sc), caveat_coverage(sc, minor=True)}
    return frozenset(s)
