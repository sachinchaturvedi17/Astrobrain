"""Hindi (Devanagari) versions of the fixed system sentences. Same names and meaning as phrasebook.py.

DRAFT: written by the assistant, NOT yet reviewed by a native speaker or an astrologer. Wording is deliberately
neutral in grammatical gender (no first-person verbs) because the Pandit's persona gender is undecided.
"""
from __future__ import annotations

from .hindi import SCOPE_HI

SCOPES = ("career", "marriage", "wealth", "education", "children", "character", "mind", "status", "family", "general")
DECLINED = ("medical", "financial", "legal")

INTRO_OVERVIEW = ("यहाँ आपकी कुंडली की मुख्य बातें हैं, महत्व के क्रम में। ये पारंपरिक पाराशरी नियमों पर आधारित हैं।")
INTRO_DASHA = "आपकी कुंडली में इस समय जो दशा चल रही है, वह यह है।"
INTRO_DECLINED_ONLY = "यहाँ बताया गया है कि किस बात में सहायता मिल सकती है और किसमें नहीं।"
INVITE = ("किसी खास विषय के बारे में पूछिए, जैसे करियर, धन, स्वभाव या चल रही दशा, तो उस पर विस्तार से बात हो सकती है।")
CAVEAT_TENDENCY = "ये पारंपरिक पाठ हैं, यानी विचार करने योग्य रुझान; ये भविष्यवाणी नहीं हैं।"
CAVEAT_PROVISIONAL = ("नियमों की समीक्षा अभी अभ्यासरत ज्योतिषियों द्वारा हो रही है; 'अनंतिम' चिह्नित पाठों की "
                      "अभी किसी ज्योतिषी ने जाँच नहीं की है।")
CAVEAT_TIME = ("आपका जन्म समय अनिश्चित है, इसलिए केवल वही बातें बताई गई हैं जो संभावित समय की पूरी सीमा में एक जैसी रहती हैं; "
               "जो ठीक मिनट पर निर्भर हैं, उन्हें छोड़ दिया गया है।")
CAVEAT_TIMING = ("घटनाएँ कब होंगी, इसकी तिथियाँ नहीं बताई जा सकतीं; चल रही दशा बताई जा सकती है, पर समय की भविष्यवाणी नहीं।")
CAVEAT_NOREADINGS = "इस विषय पर आपकी कुंडली में बताने योग्य कोई पाठ नहीं मिला।"
CAVEAT_NODASHA = "उपलब्ध जन्म विवरण से चल रही दशा निकाली नहीं जा सकी।"
CAVEAT_UNDETERMINED = ("कुछ नियमों की जाँच नहीं हो सकी, क्योंकि वे ऐसे जन्म विवरण पर निर्भर हैं जिन्हें भरोसे के साथ तय नहीं किया जा सका; "
                       "अनुमान लगाने के बजाय उन्हें छोड़ दिया गया है।")
INTRO_COMBINED = ("यहाँ दो अलग नज़रियों से मुख्य बातें हैं: आपकी कुंडली (पारंपरिक पाराशरी नियम) और जन्म-तिथि का अंकशास्त्र। "
                  "दोनों को अलग रखा गया है, और जहाँ दोनों एक ही ग्रह की ओर इशारा करते हैं वह बताया गया है।")
INTRO_NUMEROLOGY = "यहाँ आपके अंक हैं और भारतीय अंकशास्त्र की परंपरा उनके बारे में क्या कहती है।"
CAVEAT_NUMEROLOGY = ("अंकशास्त्र एक आधुनिक लोकप्रिय परंपरा है; इसके पीछे कोई शास्त्रीय वैदिक ग्रंथ या प्रमाणित भविष्यसूचक रिकॉर्ड नहीं है। "
                     "इसे चिंतन का एक और नज़रिया मानिए, कुंडली के लिए अतिरिक्त प्रमाण नहीं।")
CAVEAT_NONAME = "नाम-अंक के लिए अंग्रेज़ी अक्षरों में आपका नाम चाहिए; उसे जोड़ना हो तो नाम बताइए।"
NOTE_ENGLISH_ANSWER = "इस उत्तर का हिंदी पाठ अभी उपलब्ध नहीं है, इसलिए नीचे का उत्तर अंग्रेज़ी में है।"

_DECLINE = {
    "medical": "चिकित्सा सलाह या रोग-निदान यहाँ नहीं दिया जाता; इस हिस्से के लिए कृपया डॉक्टर से मिलें।",
    "financial": "वित्तीय या निवेश सलाह यहाँ नहीं दी जाती; इस हिस्से के लिए कृपया किसी योग्य सलाहकार से मिलें।",
    "legal": "कानूनी सलाह यहाँ नहीं दी जाती; इस हिस्से के लिए कृपया वकील से मिलें।",
}
LABEL_PROVISIONAL = "अनंतिम"
LABEL_CHECKED = "स्रोत से जाँचा हुआ"


def intro_targeted(scope: str) -> str:
    return f"यहाँ {SCOPE_HI.get(scope, scope)} के बारे में आपकी कुंडली की बातें हैं, पारंपरिक पाराशरी नियमों के अनुसार।"


def intro_combined_targeted(scope: str) -> str:
    return (f"यहाँ {SCOPE_HI.get(scope, scope)} के बारे में आपकी कुंडली और जन्म-तिथि के अंकशास्त्र की बातें हैं। "
            "दोनों नज़रिए अलग रखे गए हैं, और जहाँ दोनों एक ही ग्रह की ओर इशारा करते हैं वह बताया गया है।")


def caveat_coverage(scope: str, minor: bool = False) -> str:
    if minor and scope == "marriage":
        return "18 वर्ष से कम उम्र के व्यक्ति की कुंडली के लिए विवाह या संबंधों पर चर्चा नहीं की जाती।"
    return f"{SCOPE_HI.get(scope, scope)} के लिए अभी कोई पाठ उपलब्ध नहीं है, इसलिए अनुमान नहीं लगाया जाएगा।"


def caveat_declined(topic: str) -> str:
    return _DECLINE[topic]


CRISIS = ("आप जिस पीड़ा से गुज़र रहे हैं, उसके लिए मुझे सचमुच दुख है, और अभी कुंडली की बात करना ठीक नहीं होगा। "
          "आप किसी भी पाठ से कहीं ज़्यादा महत्वपूर्ण हैं। अगर आप खुद को नुकसान पहुँचाने के बारे में सोच रहे हैं या खतरे में हैं, "
          "तो कृपया अभी अपने स्थानीय आपातकालीन नंबर पर कॉल करें।\n\n"
          "भारत में आप Tele-MANAS से 14416 या 1-800-891-4416 पर, या KIRAN से 1800-599-0019 पर बात कर सकते हैं "
          "(24x7, कई भाषाओं में)। भारत से बाहर findahelpline.com देश के अनुसार सेवाएँ बताता है।\n\n"
          "हो सके तो अपने आसपास किसी को बताइए कि आप कैसा महसूस कर रहे हैं। मैं भी सुनने के लिए यहाँ हूँ।")
DEATH = ("जीवन की अवधि या मृत्यु के समय के बारे में यहाँ कोई कथन नहीं किया जाता। कोई कुंडली यह ईमानदारी से नहीं बता सकती, "
         "और ऐसा दिखावा करना ठीक नहीं होगा। करियर, स्वभाव या चल रही दशा जैसे दूसरे विषयों पर बात हो सकती है।")
SAFE_MINIMAL = ("अभी इस प्रश्न का भरोसेमंद उत्तर तैयार नहीं हो सका। कृपया दूसरे शब्दों में पूछिए, "
                "या किसी खास विषय, जैसे करियर, धन या स्वभाव के बारे में पूछिए।")
NEED_BIRTH = "पहले आपका जन्म विवरण चाहिए। कृपया जन्म की तारीख, समय और स्थान बताइए।"


def all_fixed() -> frozenset:
    s = {INTRO_OVERVIEW, INTRO_DASHA, INTRO_DECLINED_ONLY, INVITE, CAVEAT_TENDENCY, CAVEAT_PROVISIONAL, CAVEAT_TIME,
         CAVEAT_TIMING, CAVEAT_NOREADINGS, CAVEAT_NODASHA, CAVEAT_UNDETERMINED, NOTE_ENGLISH_ANSWER, CRISIS, DEATH,
         SAFE_MINIMAL, NEED_BIRTH, INTRO_COMBINED, INTRO_NUMEROLOGY, CAVEAT_NUMEROLOGY, CAVEAT_NONAME}
    s |= set(_DECLINE.values())
    for sc in SCOPES:
        s |= {intro_targeted(sc), intro_combined_targeted(sc), caveat_coverage(sc), caveat_coverage(sc, minor=True)}
    return frozenset(s)
