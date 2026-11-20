"""Hinglish (Hindi in Roman script, as Indians chat) wording of every Parashari rule, so the template composer can
answer in Hinglish without an LLM. Same meaning and the same chart entities as the English wording (tests enforce
the entity parity). DRAFT: written by the assistant, not yet reviewed by a native speaker or an astrologer.
Numerology rules carry their Hinglish wording in rulepacks/numerology.py.
"""
from __future__ import annotations

from .numerology import HINGLISH as _NUM_HG
from .parashari import ordn

G = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra",
     "Saturn": "Shani"}
QUAL = {"Sun": "jeevan-shakti, adhikaar aur aatm-vishwas", "Moon": "mann, bhavnayein aur palan-poshan",
        "Mars": "urja, himmat aur pehal", "Mercury": "buddhi, vaani aur vyapar", "Jupiter": "gyaan, margdarshan aur bhagya",
        "Venus": "rishte, aaram aur kalaa", "Saturn": "anushasan, dhairya aur zimmedari"}
FREQUENCY_HG = {
    "common": "Yeh pattern aam hai (25% se zyada kundliyon mein milta hai).",
    "moderate": "Yeh pattern lagbhag 5-25% kundliyon mein milta hai.",
    "uncommon": "Yeh pattern lagbhag 1-5% kundliyon mein milta hai.",
    "rare": "Yeh pattern 1% se kam kundliyon mein milta hai.",
}
LABEL_HG = {"provisional": "abhi jaanch baaki", "source-checked": "srot se jaanchi hui"}

T: dict = {}
MAHA = {
    "ruchaka": ("Mars", "himmat, rob-daar upasthiti, josh aur competitive ya action wale kshetron mein pehchaan"),
    "bhadra": ("Mercury", "tez, saaf bolne wale dimaag, padhai, communication, vyapar aur analysis mein kushalta"),
    "hamsa": ("Jupiter", "samajh, achhe nirnay, naitik jhukaav, aur salahkar ya sikhane wali samaanit bhoomika"),
    "malavya": ("Venus", "nafaasat, aakarshan, kalaa aur aaram ki kadr, aur karibi rishton mein achha bhagya"),
    "shasha": ("Saturn", "anushasan, sahansheelta, aur lagatar mehnat tatha sangathan se kamaya hua adhikaar"),
}
for k, (p, what) in MAHA.items():
    T[f"yoga.{k}"] = (f"{k.capitalize()} yoga (paanch 'mahapurush' yogon mein se ek). {G[p]} majboot hai aur kendra (angular) bhaav mein hai. "
                      f"Parampara se ise {what} ka sanket mana jata hai.")

T.update({
    "yoga.sunapha": "Sunapha yoga: Chandra se 2nd bhaav mein koi grah (Surya ko chhodkar) hai. Parampara se ise apni kamai se bane sansadhan aur capable dimaag ka sanket mana jata hai; asar is par nirbhar karta hai ki grah shubh hai ya ashubh.",
    "yoga.anapha": "Anapha yoga: Chandra se 12th bhaav mein koi grah (Surya ko chhodkar) hai. Parampara se ise sanyamit vyaktitva aur achhi saakh ka sanket mana jata hai; asar grah ke shubh ya ashubh hone par nirbhar karta hai.",
    "yoga.durudhara": "Durudhara yoga: Chandra ke dono taraf (2nd aur 12th bhaav mein) grah hain. Parampara se ise sukh-suvidha, udarta aur sahara paane wale jeevan ka sanket mana jata hai.",
    "yoga.kemadruma": "Kemadruma yoga: Chandra akela hai, uske saath ya aas-paas koi grah nahi, aur Lagna se kendra mein bhi koi grah nahi. Parampara se ise akelepan ya aatm-nirbharta ke daur ka sanket mana jata hai; classical granth ise radd karne wali kai sthitiyan bhi batate hain.",
    "yoga.kemadruma_common": "Kemadruma yoga (aaj ki aam paribhasha): Chandra ke saath ya usse 2nd ya 12th bhaav mein koi grah nahi. Parampara se ise akelepan ya aatm-nirbharta ke daur ka sanket mana jata hai; radd karne wali sthitiyan lagu hoti hain.",
    "yoga.vesi": "Vesi yoga: Surya se 2nd bhaav mein koi grah (Chandra ko chhodkar) hai. Parampara se ise sthir, achhi tarah bolne wale swabhav ka sanket mana jata hai; shubh grah anukool roop dete hain aur ashubh grah ulta.",
    "yoga.vosi": "Vosi yoga: Surya se 12th bhaav mein koi grah (Chandra ko chhodkar) hai. Parampara se ise mehnat aur capable, sakriya swabhav ka sanket mana jata hai; shubh grah anukool roop dete hain aur ashubh grah ulta.",
    "yoga.ubhayachari": "Ubhayachari yoga: Surya ke dono taraf grah hain. Parampara se ise santulit, achhi saakh wale swabhav ka sanket mana jata hai.",
    "raja.yogakaraka": "Yogakaraka: is Lagna ke liye ek hi grah kendra aur trikon dono ka swami hai. Parampara se ise ek khaas sahayak grah mana jata hai, jiski dashayein uplabdhi ke liye anukool rehti hain.",
    "wealth.daridra_mars_saturn_2h": "2nd bhaav mein Mangal aur Shani saath hain: parampara se dhan aur parivarik sansadhan jodne mein saavdhani ka sanket; Budh ki drishti padne par yeh asar kam maana jata hai.",
    "wealth.daridra_sun_2h_saturn_aspect": "Surya 2nd bhaav mein hai aur us par Shani ki drishti hai: parampara se jeevan ke shuruaati hisse mein aarthik sthirta aur parivar ke sahare mein saavdhani ka sanket.",
    "nabhasa.rajju": "Rajju yoga (Nabhasa, Asraya varg): saaton grah chara (movable) rashiyon mein hain: parampara se sakriya, mahatvakanshi aur ghoomne-firne wale swabhav ka sanket.",
    "nabhasa.musala": "Musala yoga (Nabhasa, Asraya varg): saaton grah sthir (fixed) rashiyon mein hain: parampara se sthirta, dridh sankalp aur aatm-samman ka sanket.",
    "nabhasa.nala": "Nala yoga (Nabhasa, Asraya varg): saaton grah dvisvabhav (dual) rashiyon mein hain: parampara se adaptability aur versatility ka sanket.",
    "lagna_lord.kendra": "Lagna ke swami kendra bhaav mein hain: parampara se aatmnirbhar aur achhe sahare wali jeevan disha.",
    "lagna_lord.trikona": "Lagna ke swami trikon (5th ya 9th) mein hain: parampara se bhagyashali aur uddeshyapoorn jhukaav.",
    "lagna_lord.dusthana": "Lagna ke swami 6th, 8th ya 12th mein hain: parampara se mehnat, seva, badlaav ya piche hatne se aakaar leti jeevan disha.",
    "lagna_lord.upachaya_2_3_11": "Lagna ke swami 2nd, 3rd ya 11th mein hain: parampara se mehnat, sansadhan aur networks se dheere-dheere badhne wale laabh.",
    "yoga.gajakesari": "Gajakesari yoga: Guru, Chandra se kendra bhaav mein hai. Parampara se ise buddhi, achhi saakh aur samaaj mein sahara dene wali sthiti ka sanket mana jata hai.",
    "yoga.budhaditya": "Budhaditya yoga: Surya aur Budh ek hi rashi mein hain. Parampara se ise tez buddhi aur communication tatha analysis mein kushalta ka sanket mana jata hai.",
    "yoga.chandra_mangala": "Chandra-Mangala yoga: Chandra aur Mangal ek hi rashi mein hain. Parampara se ise udyam aur kamai ki lagan ka sanket mana jata hai.",
    "yoga.guru_chandala": "Guru-Chandala yoga: Guru aur Rahu ek hi rashi mein hain. Parampara se ise aastha, guruon aur parampara ke prati hatke ya sawal uthane wale nazariye ka sanket mana jata hai.",
    "yoga.angaraka": "Angaraka yoga: Mangal aur Rahu ek hi rashi mein hain. Parampara se ise teevrata aur jaldbaazi ka sanket mana jata hai, jise soch-samajhkar disha dene se faayda hota hai.",
    "yoga.shrapit": "Shrapit yoga: Shani aur Rahu ek hi rashi mein hain. Parampara se ise bhaari zimmedariyon ya baar-baar hone wali deri ka sanket mana jata hai, jinke liye sabr chahiye.",
    "yoga.vish": "Vish yoga: Chandra aur Shani ek hi rashi mein hain. Parampara se ise gambhir, sanyamit bhavnaatmak swabhav ka sanket mana jata hai, jo kabhi-kabhi bojh mehsoos kar sakta hai.",
    "dosha.kaal_sarp": "Saaton grah Rahu-Ketu ke ek taraf hain, Rahu se Ketu wale aadhe hisse mein (Kaal Sarp, jaisa adhiktar srot paribhashit karte hain). Parampara se ise kendrit karmic themes wale jeevan pattern ka sanket mana jata hai; yeh dhaarna baad ki parampara ki hai aur yahan padhe gaye classical granthon mein nahi milti.",
    "dosha.kaal_amrit": "Saaton grah Rahu-Ketu ke ek taraf hain, Ketu se Rahu wale aadhe hisse mein (kuch srot ise Kaal Amrit ya ulta pattern kehte hain). Baad ki parampara ki dhaarna, yahan padhe gaye classical granthon mein nahi milti.",
    "yoga.neecha_bhanga_dispositor_kendra": "Neech rashi ka grah, jiski rashi ka swami Lagna se kendra bhaav mein hai: neecha-bhanga ki classical sthitiyon mein se ek, jise parampara se kamzori ka taakat mein badalna mana jata hai.",
    "parivartana.maha": "Maha Parivartana: do shubh bhaavon (1, 2, 4, 5, 7, 9, 10, 11) ke swami rashi badalte hain. Parampara se ise un bhaavon ke maamlon mein paraspar majboot sahare ka sanket mana jata hai.",
    "parivartana.dainya": "Dainya Parivartana: 6th, 8th ya 12th ke swami kisi aur bhaav ke swami se rashi badalte hain. Parampara se ise un bhaavon ke maamlon ke kathinai ya mehnat se uljhne ka sanket mana jata hai.",
    "parivartana.khala": "Khala Parivartana: 3rd ke swami kisi shubh bhaav ke swami se rashi badalte hain. Parampara se ise mishrit, mehnat se chalne wala par mahatvakanshi pattern mana jata hai.",
})
for who, label in (("lagna", "Lagna"), ("moon", "Chandra"), ("venus", "Shukra")):
    T[f"dosha.manglik_from_{who}"] = (
        f"Mangal {label} se ginti mein 1st, 4th, 7th, 8th ya 12th mein hai (Manglik / Kuja dosh). Vivah-milan mein ise parampara se "
        "saajhedaari mein tez, dridh urja ka sanket mana jata hai; kai parampara ise radd karne wali sthitiyan batati hain aur saathi ki kundli ke saath taulti hain.")
for k, t in (("l4_l5", (4, 5)), ("l4_l9", (4, 9)), ("l7_l5", (7, 5)), ("l7_l9", (7, 9)), ("l10_l5", (10, 5)), ("l10_l9", (10, 9))):
    T[f"raja.{k}"] = (f"Raja yoga: {ordn(t[0])} (kendra) aur {ordn(t[1])} (trikon) ke swami yuti, rashi-vinimay ya parasparik drishti se jude hain. "
                      "Parampara se ise pad-pratishtha aur uplabdhi mein sahara mana jata hai, jo tab sabse zyada hota hai jab yeh grah khud achhi sthiti mein hon.")
for k, (a, b) in (("l2_l11", (2, 11)), ("l5_l9", (5, 9)), ("l1_l11", (1, 11)), ("l2_l5", (2, 5)), ("l9_l11", (9, 11))):
    T[f"wealth.dhana_{k}"] = (f"Dhana yoga: {ordn(a)} aur {ordn(b)} bhaav ke swami yuti, rashi-vinimay ya parasparik drishti se jude hain. "
                              "Parampara se ise kamai aur sanchay mein sahara mana jata hai, jo shamil grahon ki dasha mein zyada dikhta hai.")
for k, v in (("harsha", "6th"), ("sarala", "8th"), ("vimala", "12th")):
    T[f"yoga.vipareeta_{k}"] = (f"Vipareeta Raja yoga ({k.capitalize()}): {v} ke swami kisi aur kathin bhaav (6th, 8th ya 12th) mein baithe hain. "
                                "Parampara se ise aisi mushkilein mana jata hai jo aage chalkar laabh mein badal jaati hain.")
for p, g in G.items():
    q = QUAL[p]
    T[f"dignity.{p.lower()}_exalted"] = (f"{g} apni uchch rashi mein hai, jo parampara se uski sabse majboot rashi maani jaati hai. "
                                         f"Jin cheezon ka woh pratinidhitva karta hai ({q}), woh aasani aur majbooti se vyakt hoti hain.")
    T[f"dignity.{p.lower()}_debilitated"] = (f"{g} apni neech rashi mein hai, jo parampara se uski sabse kamzor rashi maani jaati hai. "
                                             f"Jin cheezon ka woh pratinidhitva karta hai ({q}), unmein zyada mehnat lag sakti hai ya nateeje unevan reh sakte hain; "
                                             "classical granth is asar ko kam karne wali sthitiyan bhi batate hain.")
    T[f"dignity.{p.lower()}_own"] = (f"{g} apni swarashi mein hai, jo parampara se aaram wali, sthir sthiti maani jaati hai. "
                                     f"Jin cheezon ka woh pratinidhitva karta hai ({q}), woh sthirta se vyakt hoti hain.")

HINGLISH_PARASHARI = {f"parashari.{k}": v for k, v in T.items()}
HINGLISH_ALL = {**HINGLISH_PARASHARI, **_NUM_HG}


def hinglish_text(rule_id: str):
    return HINGLISH_ALL.get(rule_id)
