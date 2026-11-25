"""Parashari rules, batch 1: the effects of the houses (BPHS ebook chapters 11-16).

Same honesty rules as parashari.py:
  * Every interpretation is our own wording, a *traditional reading*, never a prediction. The source
    ebook is not under a declared licence, so nothing here is copied from it.
  * Only conditions the fact store can state are encoded. Where the text adds a clause we cannot
    evaluate (benefic aspect on a house, combustion, navamsa strength, planetary war) the rule keeps
    the part we can test and says so in `notes`, so an auditing astrologer sees exactly what is missing.
  * Verses that the text ties to a child's death, to a sibling's death, to a mother's life span, or to
    the age at which a child is born are deliberately NOT encoded: the app does not make such claims.
  * review_status stays "draft": verse numbers come from an automated digest of the ebook and have not
    been compared line by line.
"""
from __future__ import annotations

from ..derive import DUSTHANA, KENDRA, SEVEN, pair
from ..predicate import all_of, any_of
from ..rules import Rule
from .parashari import E, I, P, bphs

RULES: list[Rule] = []
HINGLISH: dict = {}

KENDRA_TRIKONA = (1, 4, 5, 7, 9, 10)
BENEFICS = ("Jupiter", "Venus")          # unambiguous natural benefics (Mercury and the Moon depend on company / phase)
MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")


def planets_in(planets, houses):
    return any_of(*[I(g, "house", houses) for g in planets])


def lord_in(n, houses):
    return I(f"house{n}", "lord_house", houses)


def lord_dignified(n, digs):
    """The planet that rules house n stands in one of the given dignities (sign-level)."""
    return any_of(*[all_of(E(f"house{n}", "lord", g), I(g, "dignity", digs)) for g in SEVEN])


def lord_joined_by(n, planet):
    """The ruler of house n shares a sign with `planet` (the ruler being a different planet)."""
    return any_of(*[all_of(E(f"house{n}", "lord", g), E(pair(g, planet), "conjunct", True))
                    for g in SEVEN if g != planet])


def R(rule_id, cond, scope, text, hinglish, chapter, verse, *, adverse=False, rarity=None, notes=""):
    RULES.append(Rule(rule_id=f"{P}.{rule_id}", system=P, condition=cond, scope=tuple(scope),
                      interpretation=text, source=bphs(chapter, verse), review_status="draft",
                      provenance="classical_text", adverse=adverse, rarity=rarity, notes=notes))
    HINGLISH[f"{P}.{rule_id}"] = hinglish


# ---------------------------------------------------------------- Chapter 12: the 1st house (Tanu bhava)
R("bhava1.benefic_in_lagna", planets_in(BENEFICS, (1,)), ("character",),
  "Jupiter or Venus stands in the 1st house. Traditionally read as a pleasing presence and appearance, "
  "and a body that carries its owner comfortably.",
  "Guru ya Shukra 1st bhaav mein hai. Parampara se ise aakarshak vyaktitva aur sukhad, sahaj kaaya ka sanket mana jata hai.",
  "12", "4", rarity="moderate",
  notes="Text says 'a benefic'. Only Jupiter and Venus are counted; Mercury (company-dependent) and the Moon "
        "(phase-dependent) are left out so the rule never fires on an unclear benefic. Malefic-in-lagna is "
        "not encoded: with five malefic grahas it would apply to about a third of charts.")
R("bhava1.lagna_lord_debilitated",
  lord_dignified(1, ("debilitated",)), ("health", "character"),
  "The ruler of the 1st house is in its sign of debilitation. Traditionally a caution that vitality and "
  "self-confidence need steady care; classical texts list conditions that offset it.",
  "1st bhaav ke swami apni neech rashi mein hain. Parampara se ise sanket mana jata hai ki urja aur "
  "aatm-vishwas ko niyamit dekhbhaal chahiye; classical granth ise kam karne wali sthitiyan bhi batate hain.",
  "12", "1-2", adverse=True, rarity="moderate",
  notes="Text pairs debilitation with combustion and enemy signs; combustion and sign friendship are not "
        "evaluated here. Health scope is withheld from the user by the selection policy.")

# ---------------------------------------------------------------- Chapter 13: the 2nd house (Dhan bhava)
R("bhava2.lord_supportive",
  lord_in(2, (1, 2, 4, 5, 7, 9, 10)), ("wealth",),
  "The ruler of the 2nd house stands in the 1st, 2nd, 4th, 5th, 7th, 9th or 10th house. Traditionally read as "
  "resources and family support that tend to grow steadily.",
  "2nd bhaav ke swami 1st, 2nd, 4th, 5th, 7th, 9th ya 10th bhaav mein hain. Parampara se ise sansadhan aur "
  "parivaar ke sahare ke dheere-dheere badhne ka sanket mana jata hai.",
  "13", "1-2", rarity="common",
  notes="Text names the 2nd, a kendra or a trikona; that is exactly {1,4,7,10} plus {5,9} plus the 2nd itself.")
R("bhava2.lord_dusthana",
  lord_in(2, DUSTHANA), ("wealth",),
  "The ruler of the 2nd house stands in the 6th, 8th or 12th house. Traditionally a caution that savings and "
  "family resources ask for extra care; other chart factors can offset it.",
  "2nd bhaav ke swami 6th, 8th ya 12th bhaav mein hain. Parampara se ise sanket mana jata hai ki bachat aur "
  "parivaarik sansadhanon par zyada dhyaan dena padta hai; chart ke dusre karak ise sambhal sakte hain.",
  "13", "1-2", adverse=True, rarity="common",
  notes="Text says 'decline'; our wording is softened to a caution, per the project's tendency-not-prediction rule. "
        "Roughly a quarter of charts: the Composer must not treat it as a rare warning.")
R("bhava2.lord_dignified",
  lord_dignified(2, ("own", "exalted")), ("wealth", "character"),
  "The ruler of the 2nd house is in its own sign or its sign of exaltation. Traditionally read as generosity "
  "of speech and hand, and a good reputation around money and family.",
  "2nd bhaav ke swami apni swarashi ya uchch rashi mein hain. Parampara se ise vaani aur haath ki udarta tatha "
  "dhan aur parivaar ke maamlon mein achhi saakh ka sanket mana jata hai.",
  "13", "10", rarity="moderate",
  notes="Sign-level dignity only; degree-level strength is not assessed. 'Own' includes any sign the planet rules.")
R("bhava2.lord2_kendra_lord11_trikona",
  all_of(lord_in(2, KENDRA), lord_in(11, (5, 9))), ("wealth",),
  "The ruler of the 2nd house is in an angular house while the ruler of the 11th house is in the 5th or 9th house. "
  "Traditionally read as a supportive pattern for earnings and gains.",
  "2nd bhaav ke swami kendra mein hain aur 11th bhaav ke swami 5th ya 9th bhaav mein hain. Parampara se ise kamai "
  "aur laabh ke liye sahayak sthiti ka sanket mana jata hai.",
  "13", "5", rarity="moderate",
  notes="The text adds an alternative clause (both lords joined or aspected by Jupiter and Venus) whose "
        "wording in this ebook is ambiguous; only the placement clause is encoded.")
R("bhava2.lords_2_11_dusthana_malefic_in_2",
  all_of(lord_in(2, DUSTHANA), lord_in(11, DUSTHANA), planets_in(MALEFICS, (2,))),
  ("wealth",),
  "The rulers of both the 2nd and 11th houses are in the 6th, 8th or 12th house, and a malefic stands in the 2nd house. "
  "Traditionally a caution about steady accumulation, which tends to need deliberate planning.",
  "2nd bhaav aur 11th bhaav dono ke swami 6th, 8th ya 12th bhaav mein hain aur 2nd bhaav mein koi paap grah hai. Parampara se "
  "ise sanket mana jata hai ki dhan ka jodna soch-samajhkar yojana banane se hi sthir hota hai.",
  "13", "6", adverse=True, rarity="uncommon",
  notes="Text speaks of lifelong want; softened. Malefics counted: Sun, Mars, Saturn, Rahu, Ketu.")
R("bhava2.jupiter_ruler_of_2_in_2_or_with_mars",
  all_of(E("house2", "lord", "Jupiter"),
         any_of(E("Jupiter", "house", 2), E(pair("Jupiter", "Mars"), "conjunct", True))),
  ("wealth",),
  "Jupiter rules the 2nd house and stands in it, or shares a sign with Mars. Traditionally read as a good "
  "foundation for wealth.",
  "Guru 2nd bhaav ke swami hain aur usi bhaav mein hain, ya Mangal ke saath ek rashi mein hain. Parampara se ise "
  "dhan ki achhi neev ka sanket mana jata hai.",
  "13", "3", rarity="uncommon",
  notes="Jupiter rules the 2nd only for Vrischika and Kumbha lagnas.")

# ---------------------------------------------------------------- Chapter 14: the 3rd house (Sahaj bhava)
R("bhava3.jupiter_or_venus_in_3", planets_in(BENEFICS, (3,)), ("family", "character"),
  "Jupiter or Venus stands in the 3rd house. Traditionally read as good support from siblings and a "
  "courteous, steady kind of courage.",
  "Guru ya Shukra 3rd bhaav mein hai. Parampara se ise bhai-behnon ke achhe sahare aur vinamra, sthir himmat "
  "ka sanket mana jata hai.",
  "14", "1", rarity="moderate",
  notes="Text says 'a benefic on the 3rd'. Same benefic set as bhava1.benefic_in_lagna. The text's sibling-loss "
        "verses (Sun, Saturn or Mars in the 3rd) are not encoded.")

# ---------------------------------------------------------------- Chapter 15: the 4th house (Bandhu bhava)
R("bhava4.lord_or_lagna_lord_in_4",
  any_of(lord_in(4, (4,)), lord_in(1, (4,))), ("home", "family"),
  "The ruler of the 4th house, or the ruler of the 1st house, stands in the 4th house. Traditionally read as domestic "
  "comfort and a settled home life.",
  "4th bhaav ke swami, ya 1st bhaav ke swami, 4th bhaav mein hain. Parampara se ise gharelu sukh aur sthir "
  "ghar-jeevan ka sanket mana jata hai.",
  "15", "2", rarity="moderate",
  notes="The text also requires a benefic aspect on the 4th; house-level aspect is not a stored fact, so only "
        "the occupancy clause is encoded and the rule fires more widely than the verse.")
R("bhava4.lord_dignified",
  lord_dignified(4, ("own", "exalted")), ("home", "property"),
  "The ruler of the 4th house is in its own sign or its sign of exaltation. Traditionally read as comfort in "
  "land, houses and conveyances.",
  "4th bhaav ke swami apni swarashi ya uchch rashi mein hain. Parampara se ise zameen, ghar aur vahan ke sukh "
  "ka sanket mana jata hai.",
  "15", "3", rarity="moderate",
  notes="Text also names the navamsa; only sign-level dignity is evaluated.")
R("bhava4.lord4_with_lord10_in_kendra_trikona",
  all_of(I("lord4+lord10", "relation", ("conjunct",)), lord_in(4, KENDRA_TRIKONA)),
  ("home", "property"),
  "The rulers of the 4th and 10th houses share a sign, and that sign is an angular or trine house. "
  "Traditionally read as a good residence and settled property.",
  "4th aur 10th bhaav ke swami ek hi rashi mein hain, aur wo rashi kendra ya trikon bhaav hai. Parampara se ise "
  "achhe nivaas aur sthir sampatti ka sanket mana jata hai.",
  "15", "4", rarity="uncommon",
  notes="'Share a sign' is the conjunction reading. The two lords are always different planets, since the 4th and "
        "10th are opposite signs.")

# ---------------------------------------------------------------- Chapter 16: the 5th house (Putra bhava)
R("bhava5.lord_supportive",
  any_of(lord_in(5, (2, 5, 9)), lord_dignified(5, ("exalted",)), lord_joined_by(5, "Jupiter")),
  ("children",),
  "The ruler of the 5th house is exalted, stands in the 2nd, 5th or 9th house, or shares a sign with Jupiter. "
  "Traditionally read as support for children and the matters of the 5th house.",
  "5th bhaav ke swami uchch hain, ya 2nd, 5th ya 9th bhaav mein hain, ya Guru ke saath ek rashi mein hain. "
  "Parampara se ise santaan tatha 5th bhaav ke vishayon ke liye sahayak sthiti ka sanket mana jata hai.",
  "16", "16", rarity="common",
  notes="Scope is 'children' only: the 5th house also governs learning, but the education topic is withheld until "
        "the planner defines how it is read. The text's verses on the number and sex of children, on the age at which children arrive and on child loss "
        "are deliberately not encoded.")

# ---------------------------------------------------------------- Education: house lords placed in key houses (chapter 24)
# The text gives a reading for every house lord in every house. Those that speak of learning, intelligence or
# speech are encoded here, grouped by lord so each rule keeps its verse numbers. Scope is education only.
R("edu.lagna_lord_in_1_2_9", lord_in(1, (1, 2, 9)), ("education",),
  "The ruler of the 1st house stands in the 1st, 2nd or 9th house. Traditionally read as a quick, studious mind "
  "and skill in speech and expression; the 1st-house placement is also said to bring some restlessness of attention.",
  "1st bhaav ke swami 1st, 2nd ya 9th bhaav mein hain. Parampara se ise tez, padhaku mann aur vaani tatha abhivyakti "
  "mein kushalta ka sanket mana jata hai; 1st bhaav mein hone par dhyaan ki thodi chanchalta bhi batayi gayi hai.",
  "24", "1, 2, 9", rarity="moderate",
  notes="Verse 1 (1st house): intelligent but fickle. Verse 2 (2nd house): scholarly. Verse 9 (9th house): skill "
        "and eloquence in speech. The verse on the 8th house (accomplished scholar with other faults) is not encoded.")
R("edu.lord4_in_4", lord_in(4, (4,)), ("education",),
  "The ruler of the 4th house stands in the 4th house. Traditionally read as a learned, skilled and "
  "well-regarded person.",
  "4th bhaav ke swami 4th bhaav mein hain. Parampara se ise vidvaan, kushal aur maan-yogya vyakti ka sanket "
  "mana jata hai.",
  "24", "40", rarity="moderate",
  notes="Overlaps bhava4.lord_or_lagna_lord_in_4, which reads the same placement for home life; scopes differ.")
R("edu.lord4_in_5", lord_in(4, (5,)), ("education",),
  "The ruler of the 4th house stands in the 5th house. Traditionally read as a high level of education, with some "
  "hesitation when speaking before groups.",
  "4th bhaav ke swami 5th bhaav mein hain. Parampara se ise ucch shiksha ka sanket mana jata hai, saath hi "
  "samooh ke saamne bolne mein thodi jhijhak bhi.",
  "24", "43", rarity="moderate",
  notes="Text pairs high education with being tongue-tied in assemblies; worded as hesitation before groups.")
R("edu.lord5_in_1_4_9_11", lord_in(5, (1, 4, 9, 11)), ("education",),
  "The ruler of the 5th house stands in the 1st, 4th, 9th or 11th house. Traditionally read as a scholarly "
  "inclination, a sharp intellect and, in the 9th and 11th houses, a bent for writing or authorship.",
  "5th bhaav ke swami 1st, 4th, 9th ya 11th bhaav mein hain. Parampara se ise vidvata ki ruchi, tez buddhi aur "
  "9th tatha 11th bhaav mein lekhan ki pravritti ka sanket mana jata hai.",
  "24", "49, 52, 57, 59", rarity="common",
  notes="Verse 49: 1st house, scholarly. Verse 52: 4th house, intelligent. Verse 57: 9th house, author of treatises. "
        "Verse 59: 11th house, learned and an author.")
R("edu.lord9_in_2", lord_in(9, (2,)), ("education",),
  "The ruler of the 9th house stands in the 2nd house. Traditionally read as a scholarly, well-informed person.",
  "9th bhaav ke swami 2nd bhaav mein hain. Parampara se ise vidvaan aur jaankar vyakti ka sanket mana jata hai.",
  "24", "98", rarity="moderate",
  notes="Single verse; wording is our own.")
R("edu.lord10_in_1_5", lord_in(10, (1, 5)), ("education", "career"),
  "The ruler of the 10th house stands in the 1st or 5th house. Traditionally read as a scholarly, many-sided "
  "learning that feeds a person's work.",
  "10th bhaav ke swami 1st ya 5th bhaav mein hain. Parampara se ise vidvata aur bahumukhi gyaan ka sanket mana jata "
  "hai, jo kaam mein kaam aata hai.",
  "24", "109, 113", rarity="moderate",
  notes="Verse 109: 1st house, scholarly and poetic. Verse 113: 5th house, learning of every kind.")
R("edu.lord11_in_1_5_11", lord_in(11, (1, 5, 11)), ("education",),
  "The ruler of the 11th house stands in the 1st, 5th or 11th house. Traditionally read as an educated, articulate "
  "person whose learning grows over the years.",
  "11th bhaav ke swami 1st, 5th ya 11th bhaav mein hain. Parampara se ise shikshit, vaakpatu vyakti ka sanket "
  "mana jata hai, jiska gyaan saalon ke saath badhta hai.",
  "24", "121, 125, 131", rarity="common",
  notes="Verse 121: 1st house, poetic and eloquent. Verse 125: 5th house, educated. Verse 131: 11th house, learning "
        "grows over time.")
R("edu.lord12_in_1_5_7", lord_in(12, (1, 5, 7)), ("education",),
  "The ruler of the 12th house stands in the 1st, 5th or 7th house. Traditionally a caution that formal study may "
  "ask for extra patience and effort; other chart factors can offset it.",
  "12th bhaav ke swami 1st, 5th ya 7th bhaav mein hain. Parampara se ise sanket mana jata hai ki aupcharik "
  "padhai mein zyada sabr aur mehnat lag sakti hai; chart ke dusre karak ise sambhal sakte hain.",
  "24", "133, 137, 139", adverse=True, rarity="common",
  notes="Text speaks of lack of learning; softened to a caution. Roughly a quarter of charts, so not a rare warning.")


def bhava_rules() -> list[Rule]:
    return list(RULES)
