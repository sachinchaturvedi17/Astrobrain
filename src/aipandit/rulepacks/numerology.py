"""Seed numerology rules (v0.5): Mulank, Bhagyank, name number, personal year. System "numerology".

Honesty: numerology (Indian / Chaldean-based) has no classical Vedic text behind it and no validated predictive record.
Every rule is provenance "later_tradition", review "draft", wording is our own and phrased as traditional readings
(tendencies, with the usual flip side), never predictions. No remedies, lucky stones or colours are given.
"""
from __future__ import annotations

import re

from ..predicate import Eq
from ..rules import UNPINNED, Rule

N = "numerology"
SRC_TEXT = "Indian numerology, modern popular tradition (Chaldean name values; number-planet scheme 1 Sun ... 9 Mars)"
from ..rules import Source  # noqa: E402

SRC = Source(SRC_TEXT, UNPINNED)
NOTES = ("No classical source; treat as folk/modern tradition. Variants exist: Pythagorean name values, master numbers "
         "11/22/33, other number-planet schemes (this pack uses the common Indian one). Audit wording with a practising numerologist.")

PL = {1: "the Sun", 2: "the Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury", 6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}
GL = {1: "Surya", 2: "Chandra", 3: "Guru", 4: "Rahu", 5: "Budh", 6: "Shukra", 7: "Ketu", 8: "Shani", 9: "Mangal"}
DAYS = {1: "1st, 10th, 19th or 28th", 2: "2nd, 11th, 20th or 29th", 3: "3rd, 12th, 21st or 30th", 4: "4th, 13th, 22nd or 31st",
        5: "5th, 14th or 23rd", 6: "6th, 15th or 24th", 7: "7th, 16th or 25th", 8: "8th, 17th or 26th", 9: "9th, 18th or 27th"}
DAYS_HG = {1: "1, 10, 19 ya 28", 2: "2, 11, 20 ya 29", 3: "3, 12, 21 ya 30", 4: "4, 13, 22 ya 31", 5: "5, 14 ya 23",
           6: "6, 15 ya 24", 7: "7, 16 ya 25", 8: "8, 17 ya 26", 9: "9, 18 ya 27"}

# (scope, English theme, Hinglish theme) per number
MULANK = {
    1: (("character", "career"),
        "a self-starting, independent and leadership-minded nature that prefers to steer rather than follow; stubbornness is the usual flip side.",
        "ek self-starter, independent aur leadership wala swabhav, jo follow karne se zyada lead karna pasand karta hai; ziddipan iska aam doosra pehlu hai."),
    2: (("character", "marriage"),
        "a sensitive, cooperative and intuitive nature that does well in partnerships; moods can shift with the surroundings.",
        "ek samvedansheel, milansaar aur intuitive swabhav, jo partnership mein achha chalta hai; maahaul ke saath mood badal sakta hai."),
    3: (("character", "career"),
        "an optimistic, expressive and growth-minded nature with a pull towards teaching, advising and creativity; focus can scatter across too many interests.",
        "ek optimistic, expressive aur aage badhne wala swabhav, jisme sikhane, salah dene aur creativity ki taraf jhukaav hota hai; bahut saari ruchiyon mein dhyan bikhar sakta hai."),
    4: (("character", "career"),
        "a practical, systematic and unconventional thinker who works hard and likes doing things their own way; the path can feel uneven or full of detours.",
        "ek practical, systematic aur hatke sochne wala vyakti, jo mehnat karta hai aur kaam apne tareeke se karna pasand karta hai; raasta kabhi-kabhi unevan ya mod-mod wala lag sakta hai."),
    5: (("character", "career"),
        "a quick, curious and adaptable nature with a gift for communication and trade; restlessness is the usual flip side.",
        "ek tez, jigyasu aur adaptable swabhav, jisme baat-cheet aur vyapar ki achhi samajh hoti hai; bechaini iska aam doosra pehlu hai."),
    6: (("character", "marriage"),
        "a warm, appreciative and family-minded nature with a taste for beauty and comfort; a pull towards indulgence or people-pleasing is the usual flip side.",
        "ek garmjoshi bhara, kadrdaan aur parivar-pasand swabhav, jisme sundarta aur aaram ka shauk hota hai; zyada aish ya sabko khush rakhne ki aadat iska aam doosra pehlu hai."),
    7: (("character", "mind"),
        "a reflective, analytical and privacy-loving nature drawn to study and inner life; it can seem distant or hard to read.",
        "ek soch-vichar karne wala, analytical aur apni privacy pasand karne wala swabhav, jo padhai aur andar ki duniya ki taraf khinchta hai; kabhi-kabhi doori ya samajhne mein mushkil lag sakta hai."),
    8: (("character", "career"),
        "a disciplined, patient and ambitious nature that builds slowly and lastingly; seriousness and delayed rewards are the usual flip side.",
        "ek anushasit, dhairyavaan aur mahatvakanshi swabhav, jo dheere-dheere par tikau tareeke se banata hai; gambhirta aur der se milne wale phal iska aam doosra pehlu hai."),
    9: (("character", "mind"),
        "an energetic, courageous and generous nature that takes up causes; impatience or a short fuse is the usual flip side.",
        "ek urja se bhara, himmati aur udaar swabhav, jo kisi uddeshya ko apna leta hai; adheerta ya jaldi gussa aana iska aam doosra pehlu hai."),
}
BHAGYANK = {
    1: (("career", "status"), "towards leadership, independence and being known for one's own initiative.",
        "leadership, aatmnirbharta aur apni pehal se pehchaan banane ki taraf."),
    2: (("career", "marriage"), "towards cooperation, care and work that rests on people and trust; supportive, partnership-based and advisory roles suit it.",
        "sahyog, dekhbhal aur aise kaam ki taraf jo logon aur bharose par tika ho; sahayak, partnership wale aur salahkar bhoomikaayein suit karti hain."),
    3: (("career", "status"), "towards teaching, guidance, learning and creative or advisory work; growth tends to come through sharing knowledge.",
        "sikhane, margdarshan, padhai aur creative ya salahkar kaam ki taraf; vikas aksar gyaan baantne se aata hai."),
    4: (("career", "wealth"), "towards building systems, technical or unconventional work, and success through persistent, unorthodox effort.",
        "systems banane, technical ya hatke kaam ki taraf, aur lagatar, alag tareeke ki koshish se safalta ki taraf."),
    5: (("career", "wealth"), "towards communication, trade, media and analysis, and work that rewards speed and adaptability.",
        "baat-cheet, vyapar, media aur analysis ki taraf, aur aise kaam ki taraf jo tezi aur adaptability ko inaam deta hai."),
    6: (("career", "marriage"), "towards beauty, hospitality, the arts, comfort-related work and family or community responsibility.",
        "sundarta, mehmaannawazi, kalaa, aaram se jude kaam aur parivar ya samaj ki zimmedari ki taraf."),
    7: (("career", "mind"), "towards research, specialist or spiritual pursuits, and work that rewards depth over visibility.",
        "research, specialist ya aadhyatmik kaamon ki taraf, aur aise kaam ki taraf jo dikhawe se zyada gehrai ko maanta hai."),
    8: (("career", "wealth", "status"), "towards long-haul achievement, organisation, authority and enterprise that grows slowly through discipline.",
        "lambe samay ki uplabdhi, sangathan, adhikaar aur aise udyam ki taraf jo anushasan se dheere-dheere badhta hai."),
    9: (("career", "status"), "towards action, service, protective or competitive fields, and causes bigger than oneself.",
        "action, seva, suraksha ya pratiyogi kshetron, aur khud se bade uddeshyon ki taraf."),
}
NAME = {
    1: "confident, direct and ready to take the lead.", 2: "gentle, agreeable and diplomatic.",
    3: "cheerful, expressive and encouraging.", 4: "steady, practical and no-nonsense.",
    5: "lively, witty and quick on their feet.", 6: "charming, caring and easy to be around.",
    7: "reserved, thoughtful and a little mysterious.", 8: "composed, serious and authoritative.",
    9: "spirited, forthright and warm-hearted.",
}
NAME_HG = {
    1: "confident, seedha aur lead lene ko taiyaar.", 2: "komal, milansaar aur kootneetik.",
    3: "hansmukh, expressive aur hausla badhane wala.", 4: "sthir, practical aur seedhi baat karne wala.",
    5: "zindadil, hazirjawab aur tez.", 6: "aakarshak, parwah karne wala aur jiske saath rehna aasaan ho.",
    7: "sankoch wala, vichaarshil aur thoda rahasyamayi.", 8: "sanyamit, gambhir aur rob wala.",
    9: "josheela, saaf-saaf bolne wala aur dil ka narm.",
}
YEAR = {
    1: (("general", "career"), "fresh beginnings, taking initiative and setting a direction (the start of a nine-year cycle).",
        "nayi shuruaat, pehal karne aur disha tay karne (nau saal ke chakra ki shuruaat)."),
    2: (("general", "marriage"), "patience, partnerships, cooperation and letting things develop slowly.",
        "sabr, partnership, sahyog aur cheezon ko dheere-dheere viksit hone dene."),
    3: (("general", "status"), "expression, social life, creativity and widening one's circle.",
        "abhivyakti, saamajik jeevan, creativity aur apna daayra badhane."),
    4: (("general", "career"), "foundations, hard work, organisation and steady building.",
        "neev, mehnat, vyavastha aur tikau nirmaan."),
    5: (("general",), "change, movement, variety and flexibility.", "badlaav, halchal, vividhta aur lachilapan."),
    6: (("general", "marriage"), "home, family, responsibility and relationships.", "ghar, parivar, zimmedari aur rishton."),
    7: (("general", "mind"), "reflection, study, rest and inner work.", "chintan, padhai, aaram aur andar ke kaam."),
    8: (("general", "wealth", "career"), "effort and results, money matters and authority.",
        "mehnat aur uske nateeje, paise ke maamlon aur adhikaar."),
    9: (("general",), "completion, clearing out and letting go before a new cycle begins.",
        "poorn karne, safai karne aur naye chakra se pehle chhodne."),
}
HINGLISH: dict = {}
NUMEROLOGY_RULES: list = []


def _add(rule_id, subject, n, scope, en, hg, hint):
    NUMEROLOGY_RULES.append(Rule(
        rule_id=f"numerology.{rule_id}", system=N, condition=Eq(N, subject, "value", n), scope=tuple(scope),
        interpretation=en, source=SRC, review_status="draft", provenance="later_tradition", adverse=False,
        rarity="moderate", salience_hint=hint, notes=NOTES))
    HINGLISH[f"numerology.{rule_id}"] = hg


for n, (scope, en, hg) in MULANK.items():
    _add(f"mulank_{n}", "mulank", n, scope,
         f"Mulank {n} (birth number: born on the {DAYS[n]}), linked with {PL[n]} in Indian numerology. Traditionally read as {en}",
         f"Mulank {n} (janm-ank: mahine ki {DAYS_HG[n]} tareekh ko janm), Indian numerology mein {GL[n]} se juda hai. "
         f"Parampara se ise {re.sub(r', (jo|jisme)', lambda m: ' mana jata hai, ' + m.group(1), hg, count=1)}", 3.0)
for n, (scope, en, hg) in BHAGYANK.items():
    _add(f"bhagyank_{n}", "bhagyank", n, scope,
         f"Bhagyank {n} (destiny number), linked with {PL[n]}. Traditionally read as a life direction {en}",
         f"Bhagyank {n} (bhagya-ank), {GL[n]} se juda hai. Parampara se ise jeevan ki disha ka sanket mana jata hai: {hg}", 2.5)
for n, en in NAME.items():
    _add(f"name_{n}", "name_number", n, ("character", "status"),
         f"Name number {n} (Chaldean method), linked with {PL[n]}. Traditionally read as the way a person comes across to others: {en} "
         "The number depends on the spelling used, and changes if the spelling changes.",
         f"Name number {n} (Chaldean method), {GL[n]} se juda hai. Parampara se ise yeh mana jata hai ki aap doosron ko aise lagte hain: {NAME_HG[n]} "
         "Yeh number spelling par nirbhar hai, aur spelling badalne par badal jata hai.", 2.0)
for n, (scope, en, hg) in YEAR.items():
    _add(f"year_{n}", "personal_year", n, scope,
         f"Personal year {n}: numerology treats this year as a theme of {en} It is a theme of the year, not a forecast of events.",
         f"Personal year {n}: numerology is saal ko {hg.rstrip('.')} ka theme maanti hai. Yeh saal ka ek theme hai, ghatnaon ki bhavishyavaani nahi.", 1.5)


def numerology_rules() -> list:
    return list(NUMEROLOGY_RULES)
