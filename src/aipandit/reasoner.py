"""Classical working-out for a chart question (pure, stdlib only; the chart dict is the same one brain.py uses).

An astrologer does not answer from a template. For each question they (1) pick the house(s) that rule the matter,
(2) find the lord of that house and judge where it sits and how strong it is, (3) look at who occupies and aspects the house,
(4) check the natural significator (karaka), (5) check the running dasha and the current transits for timing.
This module does exactly those steps and returns every step as a plain line (`calc`), plus the supports / obstacles found,
so the answer can quote what was actually computed. Nothing here is random and no score is invented: a verdict is a
label produced by counting the listed supports and obstacles.

Language: English and Hinglish are written in full; Hindi (Devanagari) currently falls back to the Hinglish text.
"""
from __future__ import annotations

import datetime as _dt
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import timeline
from .ashtakoota import RASHIS
from .derive import (
    ASPECT_OFFSETS as _DERIVE_ASPECTS,
    DEBIL_SIGN as _DEBIL_SIGN,
    DUSTHANA,
    EXALT_SIGN as _EXALT_SIGN,
    KENDRA,
    OWN_SIGNS as _OWN_SIGNS,
    SIGN_LORD,
)

SIGN_EN = dict(zip(RASHIS, ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")))
PL_HG = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"}
EXALT = {g: RASHIS[idx] for g, idx in _EXALT_SIGN.items()}
DEBIL = {g: RASHIS[idx] for g, idx in _DEBIL_SIGN.items()}
OWN = {g: tuple(RASHIS[idx] for idx in idxs) for g, idxs in _OWN_SIGNS.items()}
BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")
MALEFIC = ("Saturn", "Mars", "Sun", "Rahu", "Ketu")
GOOD_HOUSES = (1, 4, 5, 7, 9, 10, 11)
UPACHAYA = (3, 6, 10, 11)
ASPECTS = {g: offs for g, offs in _DERIVE_ASPECTS.items()} | {"Rahu": (), "Ketu": ()}   # sourced directly from derive.py
MOVABLE, FIXED = ("Mesha", "Karka", "Tula", "Makara"), ("Vrishabha", "Simha", "Vrishchika", "Kumbha")
GOOD_JUPITER_FROM_MOON = (2, 5, 7, 9, 11)   # classical Gochara (Phaladeepika): Jupiter's transit is supportive from these houses
GOOD_SATURN_FROM_MOON = (3, 6, 11)

class Txt(str):
    """Technical sentence (shown only in the hidden working) that also carries a plain-language version for the answer."""
    plain: str = ""


Item = Tuple[str, Txt]   # ("+" | "-" | "·", text)

HOUSE_SUBJECT = {
    1: ("you and your overall life", "aap aur aapka poora jeevan"), 2: ("money, savings and family", "paisa, bachat aur parivaar"),
    3: ("effort, courage and communication", "mehnat, himmat aur baat-cheet"), 4: ("home and peace of mind", "ghar aur man ki shanti"),
    5: ("learning, romance and children", "padhai, pyaar aur santan"), 6: ("daily work, health and obstacles", "rozmarra kaam, sehat aur rukavatein"),
    7: ("marriage and partnership", "vivah aur saajhedari"), 8: ("sudden changes and hidden matters", "achaanak badlaav aur chhipi baatein"),
    9: ("luck and guidance", "bhagya aur margdarshan"), 10: ("career and standing", "career aur samaaj mein sthaan"),
    11: ("income, gains and friendships", "aay, laabh aur dostiyan"), 12: ("expenses and distance", "kharch aur doori"),
}


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


class Sheet:
    """The numbers an astrologer reads off the chart, in one language."""

    def __init__(self, chart: Dict[str, Any], lang: str = "en", sky: Optional[Dict[str, Any]] = None, today: Optional[_dt.date] = None):
        self.chart, self.lang = chart, "en" if lang == "en" else "hg"
        self.moon_basis = chart.get("basis") == "moon"
        self.store = chart.get("store") if not self.moon_basis else None
        self.li = RASHIS.index(chart["lagna"])
        self.today = today or _dt.date.today()
        self.sky = sky or {}
        self.pl: Dict[str, Dict[str, Any]] = {}
        for p, v in (chart.get("planets") or {}).items():
            if v.get("sign") in RASHIS:
                h = v.get("house") or (RASHIS.index(v["sign"]) - self.li) % 12 + 1
                self.pl[p] = {"sign": v["sign"], "house": int(h), "retro": bool(v.get("retrograde")), "dignity": v.get("dignity")}
        g = ((chart.get("profile") or {}).get("gender") or "").lower()
        self.gender = "female" if g.startswith("f") else "male" if g.startswith("m") else ""

    # ---------------------------------------------------------------- language helpers
    def t(self, en: str, hg: str, **kw: Any) -> str:
        return (en if self.lang == "en" else hg).format(**kw)

    def tp(self, en: str, hg: str, pen: str = "", phg: str = "", **kw: Any) -> Txt:
        """technical text + its plain-language twin"""
        x = Txt(self.t(en, hg, **kw))
        x.plain = self.t(pen, phg, **kw) if pen else ""
        return x

    def subj(self, h: int) -> str:
        return HOUSE_SUBJECT[h][0 if self.lang == "en" else 1]

    def p(self, planet: str) -> str:
        return planet if self.lang == "en" else PL_HG.get(planet, planet)

    def sg(self, sign: str) -> str:
        return f"{SIGN_EN.get(sign, sign)} ({sign})" if self.lang == "en" else sign

    def ho(self, h: int) -> str:
        return f"{ordinal(h)} house" if self.lang == "en" else f"{h}ve bhav"

    def plist(self, ps: List[str]) -> str:
        return ", ".join(self.p(x) for x in ps)

    # ---------------------------------------------------------------- chart arithmetic
    def sign(self, h: int) -> str:
        return RASHIS[(self.li + h - 1) % 12]

    def lord(self, h: int) -> str:
        if self.store is not None:
            val = self.store.value(f"house{h}", "lord", "parashari")
            if val:
                return val
        return SIGN_LORD[RASHIS.index(self.sign(h))]

    def rules(self, planet: str) -> List[int]:
        return [h for h in range(1, 13) if self.lord(h) == planet]

    def house_of(self, planet: str) -> Optional[int]:
        if self.store is not None and planet in self.pl:
            val = self.store.value(planet, "house", "parashari")
            if val is not None:
                return int(val)
        return self.pl[planet]["house"] if planet in self.pl else None

    def sign_of(self, planet: str) -> Optional[str]:
        if self.store is not None and planet in self.pl:
            val = self.store.value(planet, "sign", "parashari")
            if val:
                return val
        return self.pl[planet]["sign"] if planet in self.pl else None

    def dignity(self, planet: str) -> str:
        if self.store is not None and planet in self.pl:
            val = self.store.value(planet, "dignity", "parashari")
            if val:
                return val
        if planet in self.pl and self.pl[planet].get("dignity"):
            return str(self.pl[planet]["dignity"])
        s = self.sign_of(planet)
        if not s:
            return "neutral"
        if EXALT.get(planet) == s:
            return "exalted"
        if s in OWN.get(planet, ()):
            return "own"
        if DEBIL.get(planet) == s:
            return "debilitated"
        return "neutral"

    def occupants(self, h: int) -> List[str]:
        return [p for p, v in self.pl.items() if v["house"] == h]

    def aspect_houses(self, planet: str) -> List[int]:
        a = self.house_of(planet)
        if a is None:
            return []
        offs = ASPECTS.get(planet, (7,))
        return [(a + n - 2) % 12 + 1 for n in offs if n != 1]

    def aspectors(self, h: int) -> List[str]:
        return [p for p in self.pl if self.house_of(p) != h and h in self.aspect_houses(p)]

    def relation(self, a: str, b: str) -> str:
        """conjunct | exchange | mutual | a_on_b | b_on_a | none (graha drishti by sign position)."""
        ha, hb = self.house_of(a), self.house_of(b)
        if ha is None or hb is None or a == b:
            return "same" if a == b else "none"
        if ha == hb:
            return "conjunct"
        if self.sign_of(a) in self.rules_signs(b) and self.sign_of(b) in self.rules_signs(a):
            return "exchange"
        ab, ba = hb in self.aspect_houses(a), ha in self.aspect_houses(b)
        return "mutual" if ab and ba else "a_on_b" if ab else "b_on_a" if ba else "none"

    @staticmethod
    def rules_signs(planet: str) -> Tuple[str, ...]:
        return tuple(s for s, l in zip(RASHIS, SIGN_LORD) if l == planet)

    def neecha_bhanga(self, planet: str) -> bool:
        """Debilitation cancelled when the lord of the debilitation sign sits in a kendra from the lagna (classical condition)."""
        s = self.sign_of(planet)
        if self.dignity(planet) != "debilitated" or not s:
            return False
        disp = SIGN_LORD[RASHIS.index(s)]
        return (self.house_of(disp) or 0) in KENDRA

    def sw(self, planet: str) -> str:
        """strength as a word in the reply language"""
        return {"strong": self.t("strong", "majboot"), "weak": self.t("under pressure", "dabaav mein"), "ok": self.t("average", "madhyam")}[self.strength(planet)]

    def strength(self, planet: str) -> str:
        """strong | weak | ok from dignity and house only."""
        d = self.dignity(planet)
        h = self.house_of(planet)
        if d in ("exalted", "own"):
            return "strong"
        if d == "debilitated" and not self.neecha_bhanga(planet):
            return "weak"
        if planet not in ("Rahu", "Ketu") and h in DUSTHANA:
            return "weak"
        return "ok"

    # ---------------------------------------------------------------- judging a house the way a pandit does
    def judge(self, h: int, full: bool = True) -> List[Item]:
        out: List[Item] = []
        lord = self.lord(h)
        lh, ls = self.house_of(lord), self.sign_of(lord)
        sb = self.subj(h)
        if lh:
            if lh == h:
                tag, why = "+", self.t("in its own house, which protects the matter", "apne hi bhav mein hai, jo is vishay ko surakshit rakhta hai")
                pl = ("The main planet for {sb}, {L}, sits comfortably in its own home, which protects this area.", "{sb} ka mukhya graha {L} apne hi ghar mein aaram se hai, jo is kshetra ko surakshit rakhta hai.")
            elif lh in GOOD_HOUSES:
                tag, why = "+", self.t("a supportive position", "madadgaar sthiti hai")
                pl = ("The main planet for {sb}, {L}, is well placed in your chart, which helps.", "{sb} ka mukhya graha {L} aapke chart mein achhi jagah hai, jo madad karta hai.")
            elif lh in DUSTHANA:
                tag, why = "-", self.t("a difficult position (6/8/12) that makes results come with effort or delay", "kathin sthiti (6/8/12) hai, nateeje mehnat ya der se aate hain")
                pl = ("The main planet for {sb}, {L}, sits in a difficult spot, so results here come with extra effort or some delay.", "{sb} ka mukhya graha {L} kathin jagah par hai, isliye yahan nateeje mehnat se ya der se aate hain.")
            else:
                tag, why, pl = "·", self.t("a neutral position", "sam sthiti hai"), ("", "")
            out.append((tag, self.tp("The {h} is {s}; its lord {L} sits in your {lh} in {ls}: {why}.",
                                     "{h} {s} ka hai; uska swami {L} aapke {lh} mein {ls} mein hai: {why}.", pl[0], pl[1],
                                     h=self.ho(h) if self.lang == "en" else f"{h}ve bhav", s=self.sg(self.sign(h)), L=self.p(lord),
                                     lh=self.ho(lh), ls=self.sg(ls), why=why, sb=sb)))
            d = self.dignity(lord)
            if d == "exalted":
                out.append(("+", self.tp("{L} is exalted, so it can deliver strongly.", "{L} uchch ka hai, isliye phal dene mein sakshm hai.",
                                         "{L} is at its strongest here, so it can deliver well.", "{L} yahan sabse majboot hai, isliye achha phal de sakta hai.", L=self.p(lord))))
            elif d == "own":
                out.append(("+", self.tp("{L} is in its own sign, so it is comfortable and strong.", "{L} apni rashi mein hai, isliye majboot hai.",
                                         "{L} is comfortable and strong in your chart.", "{L} aapke chart mein aaram se aur majboot hai.", L=self.p(lord))))
            elif d == "debilitated":
                if self.neecha_bhanga(lord):
                    out.append(("+", self.tp("{L} is debilitated but the lord of that sign is in a kendra, which classically cancels the fall (Neecha Bhanga).",
                                             "{L} neech ka hai par us rashi ka swami kendra mein hai, jo parampara se neech-bhang karta hai.",
                                             "{L} looks weak by position, but a classical rule cancels that weakness, so it still holds up.",
                                             "{L} sthiti se kamzor lagta hai, par ek parampara ka niyam us kamzori ko kaat deta hai.", L=self.p(lord))))
                else:
                    out.append(("-", self.tp("{L} is debilitated with no cancellation, so this area needs extra effort.", "{L} neech ka hai aur bhang nahi, isliye is kshetra mein adhik mehnat chahiye.",
                                             "{L} is weak in your chart, so {sb} needs extra effort.", "{L} aapke chart mein kamzor hai, isliye {sb} mein adhik mehnat chahiye.", L=self.p(lord), sb=sb)))
            if lh != h and lh and full:
                co = [x for x in self.occupants(lh) if x != lord]
                ben = [x for x in co if x in BENEFIC]
                mal = [x for x in co if x in MALEFIC]
                if ben:
                    out.append(("+", self.tp("{L} is joined by {b}, a natural supporter.", "{L} ke saath {b} hai, jo prakritik sahayak hai.",
                                             "{L} gets friendly support from {b}.", "{L} ko {b} ka dostana saath mil raha hai.", L=self.p(lord), b=self.plist(ben))))
                if mal and lh not in UPACHAYA:
                    out.append(("-", self.tp("{L} is joined by {m}, which adds pressure.", "{L} ke saath {m} hai, jo dabaav badhata hai.",
                                             "{L} is under pressure from {m}.", "{L} par {m} ka dabaav hai.", L=self.p(lord), m=self.plist(mal))))
        if not full:
            return out
        for p in self.occupants(h):
            if p in BENEFIC:
                out.append(("+", self.tp("{p} sits in the {h}, a traditional support.", "{p} {h} mein baitha hai, jo parampara se sahayak hai.",
                                         "{p}, a supportive planet, sits right in the area of {sb}.", "{p}, ek sahayak graha, seedha {sb} ke kshetra mein baitha hai.", p=self.p(p), h=self.ho(h), sb=sb)))
            elif h in UPACHAYA:
                out.append(("+", self.tp("{p} in the {h} works well there (growth houses suit tough planets).", "{p} {h} mein achha kaam karta hai (vriddhi bhav mein kroor graha theek rehte hain).",
                                         "{p} sits in the area of {sb} and works well there.", "{p} {sb} ke kshetra mein baitha hai aur wahan achha kaam karta hai.", p=self.p(p), h=self.ho(h), sb=sb)))
            else:
                out.append(("-", self.tp("{p} sits in the {h}, adding intensity and some friction.", "{p} {h} mein baitha hai, jo tivrata aur ghisaav laata hai.",
                                         "{p} sits right in the area of {sb} and adds intensity and some friction.", "{p} seedha {sb} ke kshetra mein baitha hai aur tivrata aur ghisaav laata hai.", p=self.p(p), h=self.ho(h), sb=sb)))
        for p in self.aspectors(h):
            if p in ("Jupiter", "Venus", "Mercury", "Moon"):
                out.append(("+", self.tp("{p} looks at the {h}, a protective influence.", "{p} ki drishti {h} par hai, jo raksha karti hai.",
                                         "{p} watches over {sb} with a protective influence.", "{p} {sb} par raksha wali nazar rakhta hai.", p=self.p(p), h=self.ho(h), sb=sb)))
            elif h not in UPACHAYA:
                out.append(("-", self.tp("{p} aspects the {h}, a pressuring influence.", "{p} ki drishti {h} par hai, jo dabaav daalti hai.",
                                         "{p} puts steady pressure on {sb}.", "{p} {sb} par lagataar dabaav daalta hai.", p=self.p(p), h=self.ho(h), sb=sb)))
        return out

    def karaka_items(self, karakas: Tuple[str, ...]) -> List[Item]:
        from .voice import DOMAIN
        out: List[Item] = []
        for k in karakas:
            if k not in self.pl:
                continue
            st, h, s = self.strength(k), self.house_of(k), self.sign_of(k)
            word = {"strong": self.t("strong", "majboot"), "weak": self.t("under pressure", "dabaav mein"), "ok": self.t("average", "madhyam")}[st]
            tag = {"strong": "+", "weak": "-", "ok": "·"}[st]
            dom = DOMAIN[k][0 if self.lang == "en" else 1]
            plain = ("" if st == "ok" else self.t("{k}, the planet of {d}, is {w} in your chart.", "{k}, jo {d} ka graha hai, aapke chart mein {w} hai.", k=self.p(k), d=dom, w=word))
            out.append((tag, self.tp("Natural significator {k} is in {s} in your {h}: {w}.", "Karak graha {k} {s} rashi mein aapke {h} mein hai: {w}.", plain, plain,
                                     k=self.p(k), s=self.sg(s), h=self.ho(h), w=word)))
        return out

    # ---------------------------------------------------------------- dasha
    def dasha(self) -> Optional[Dict[str, Any]]:
        d = self.chart.get("dasha")
        return d if d and d.get("maha") and d.get("antar") else None

    def roles(self, planet: str, houses: Tuple[int, ...], karakas: Tuple[str, ...]) -> List[str]:
        r = []
        mine = [h for h in self.rules(planet) if h in houses]
        if mine:
            r.append(self.t("rules the " + "/".join(ordinal(h) for h in mine), "swami hai " + "/".join(f"{h}ve" for h in mine) + " bhav ka"))
        if (self.house_of(planet) in houses):
            r.append(self.t("sits in the {h}", "{h} mein hai", h=self.ho(self.house_of(planet))))
        if planet in karakas:
            r.append(self.t("is a natural significator", "karak graha hai"))
        return r

    def dasha_lines(self, houses: Tuple[int, ...], karakas: Tuple[str, ...]) -> List[Item]:
        d = self.dasha()
        if not d:
            return [("·", self.t("Dasha dates need an exact birth time, so I am not guessing them; timing below comes from transits counted from your Moon sign.",
                                 "Dasha ki tarikhein exact janm samay maangti hain, isliye main andaaza nahi laga raha; neeche ka samay Chandra rashi se gochar par aadharit hai."))]
        out: List[Item] = []
        ma, an = d["maha"], d["antar"]
        for who, lab in ((ma, self.t("Mahadasha", "Mahadasha")), (an, self.t("Antardasha", "Antardasha"))):
            r = self.roles(who, houses, karakas)
            until = d.get("maha_end") if who == ma else d.get("antar_end")
            out.append(("+" if r else "·", self.t("{lab} {w} (until {u}): " + (", ".join(r) if r else "no direct link to this matter") + ".",
                                                  "{lab} {w} ({u} tak): " + (", ".join(r) if r else "is vishay se seedha sambandh nahi") + ".",
                                                  lab=lab, w=self.p(who), u=until or "?")))
        return out

    def dasha_windows(self, involved: List[str], limit: int = 3) -> List[str]:
        if not self.dasha():
            return []
        out = []
        for w in timeline.windows(self.chart, involved, self.today, years_ahead=6, limit=limit):
            a, b = max(w["start"], self.today), w["end"]
            out.append(self.t("{a} to {b}: {an} period inside {ma}{now}", "{a} se {b}: {ma} mein {an} ka daur{now}",
                              a=timeline._mon(a, self.lang), b=timeline._mon(b, self.lang), an=self.p(w["antar"]), ma=self.p(w["maha"]),
                              now=self.t(" (running now)", " (abhi chal raha hai)") if w["now"] else ""))
        return out

    # ---------------------------------------------------------------- transits (need the sky now; future windows use `ephem`)
    def transit_house(self, planet: str) -> Optional[int]:
        s = (self.sky.get(planet) or {}).get("sign")
        return (RASHIS.index(s) - self.li) % 12 + 1 if s in RASHIS else None

    def transit_lines(self, primary: int) -> List[Item]:
        out: List[Item] = []
        if not self.sky:
            return out
        base = self.t("counted from your Moon sign", "Chandra rashi se ginne par") if self.moon_basis else self.t("counted from your lagna", "lagna se ginne par")
        sb = self.subj(primary)
        for p in ("Jupiter", "Saturn"):
            th = self.transit_house(p)
            if not th:
                continue
            infl = th == primary or primary in [(th + n - 2) % 12 + 1 for n in ASPECTS.get(p, (7,))]
            if p == "Jupiter":
                tag = "+" if infl else "·"
                txt = self.tp("Transit Jupiter is in your {h} now ({b})" + (" and it influences the {pr}, which supports this matter." if infl else "; it is not touching the {pr} right now."),
                              "Gochar mein Guru abhi aapke {h} mein hai ({b})" + (" aur woh {pr} ko prabhavit karta hai, jo is vishay ko sahara deta hai." if infl else "; abhi woh {pr} ko nahi chhoo raha."),
                              "Jupiter, the planet of blessings, is moving through a favourable part of your chart for {sb} right now." if infl else "",
                              "Guru, aashirwad ka graha, abhi aapke chart ke {sb} ke liye anukool hisse se guzar raha hai." if infl else "",
                              h=self.ho(th), b=base, pr=self.ho(primary), sb=sb)
            else:
                tag = "-" if infl else "·"
                txt = self.tp("Transit Saturn is in your {h} now ({b})" + (" and it influences the {pr}: expect seriousness, slowness and tests of commitment there." if infl else "; it is not pressing the {pr} right now."),
                              "Gochar mein Shani abhi aapke {h} mein hai ({b})" + (" aur woh {pr} ko prabhavit karta hai: wahan gambhirta, dheemapan aur pareeksha rahegi." if infl else "; abhi woh {pr} par dabaav nahi daal raha."),
                              "Saturn is passing through a part of your chart that touches {sb}, so things here feel slower, more serious and test your commitment." if infl else "",
                              "Shani aapke chart ke us hisse se guzar raha hai jo {sb} ko chhoota hai, isliye yahan cheezein dheemi, gambhir aur aapke commitment ki pareeksha leti hain." if infl else "",
                              h=self.ho(th), b=base, pr=self.ho(primary), sb=sb)
            out.append((tag, txt))
        return out

    def sade_sati(self) -> Optional[str]:
        ms = (self.chart.get("moon") or {}).get("sign")
        s = (self.sky.get("Saturn") or {}).get("sign")
        if ms not in RASHIS or s not in RASHIS:
            return None
        rel = (RASHIS.index(s) - RASHIS.index(ms)) % 12 + 1
        return {12: "rising", 1: "peak", 2: "setting"}.get(rel)


def tally(items: List[Item]) -> Tuple[int, int, str]:
    plus = sum(1 for t, _ in items if t == "+")
    minus = sum(1 for t, _ in items if t == "-")
    net = plus - minus
    label = "strong" if net >= 5 and minus <= 1 else "good" if net >= 2 else "mixed" if net >= -1 else "demanding"
    return plus, minus, label


# ------------------------------------------------------------------------------------------ future transit windows
Ephem = Callable[[_dt.date], Dict[str, str]]    # date -> {planet: sign}


def sky_ephem(lat: float = 23.26, lon: float = 77.41) -> Optional[Ephem]:
    """Planet signs on a date from the same engine the Panchang uses. None when the engine is not installed."""
    try:
        from .engines.vedaksha_engine import VedakshaEngine
        from .v09_engine import _jd_now
    except Exception:
        return None
    eng = VedakshaEngine()
    cache: Dict[_dt.date, Dict[str, str]] = {}
    lock = threading.Lock()

    def at(d: _dt.date) -> Dict[str, str]:
        d = _dt.date.fromordinal(d.toordinal() // 10 * 10)      # fixed 10-day grid so every request shares the same cached samples
        with lock:
            if d not in cache:
                sk = eng.natal(_jd_now(_dt.datetime(d.year, d.month, d.day, 6, 30, tzinfo=_dt.timezone.utc)), lat, lon)
                cache[d] = {g: RASHIS[int(sk.planets[g].longitude // 30.0) % 12] for g in sk.planets}
            return cache[d]
    return at


def warm(ephem: Optional[Ephem] = None, years: float = 9.0) -> None:
    """Fill the ephemeris cache in the background so the first 'when' question is not slow."""
    if ephem is None:
        try:
            from . import brain
            ephem = brain._ephem()
        except Exception:
            return
    if ephem is None:
        return
    d, end = _dt.date.today(), _dt.date.today() + _dt.timedelta(days=int(years * 365.25))
    while d <= end:
        try:
            ephem(d)
        except Exception:
            return
        d += _dt.timedelta(days=10)


def transit_windows(sheet: Sheet, planet: str, primary: int, ephem: Optional[Ephem], years: float = 5.0, step: int = 10, limit: int = 3) -> List[Tuple[_dt.date, _dt.date]]:
    """Date ranges in which `planet` (Jupiter) occupies or aspects the house `primary`. [] when no ephemeris is available."""
    if ephem is None:
        return []
    offs = ASPECTS.get(planet, (7,))
    ranges: List[List[_dt.date]] = []
    d, end = sheet.today, sheet.today + _dt.timedelta(days=int(years * 365.25))
    while d <= end:
        try:
            s = ephem(d).get(planet)
        except Exception:
            return []
        if s in RASHIS:
            h = (RASHIS.index(s) - sheet.li) % 12 + 1
            hit = h == primary or primary in [(h + n - 2) % 12 + 1 for n in offs]
            if hit:
                if ranges and (d - ranges[-1][1]).days <= step * 4:
                    ranges[-1][1] = d
                else:
                    ranges.append([d, d])
        d += _dt.timedelta(days=step)
    return [(a, b) for a, b in ranges][:limit]


def fmt_range(a: _dt.date, b: _dt.date, lang: str) -> str:
    return f"{timeline._mon(a, lang)} - {timeline._mon(b, lang)}"
