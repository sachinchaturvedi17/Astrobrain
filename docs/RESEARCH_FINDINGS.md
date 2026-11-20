# Research findings & plan corrections (v0.1 foundation)

Everything below was either **measured here** (marked ✔ measured) or **read from a source and
not independently verified** (marked ○ sourced). Nothing is stated from memory as fact.

## 1. Empirical validation (✔ measured, `pytest -m oracle -s`)

Reference: Swiss Ephemeris (pyswisseph, SIDM_LAHIRI, whole-sign) as an *independent oracle*.
Sample: 200 seeded random charts, 1930–2025, latitude −55…62, longitude −180…180.

| Quantity | Worst-case error | Declared bound | Note |
|---|---|---|---|
| Sun…Saturn sidereal longitude | **1.82″** | 2.5″ | |
| Mean node (Rahu) | 0.08″ | 2.0″ | mean node only |
| MC | 2.20″ | 5″ | |
| **Lagna (Ascendant)** | **19.3″** | 20″ | see §2 — *this corrects an earlier claim* |
| Vimshottari maha dates, 60 charts | < 0.01 d (15 min) vs independent implementation | | uses 365.25-day year |

Median Lagna error is 1.5″; 43 of 200 charts exceed 5″, all at higher latitudes.
Earlier in this project I reported "Asc ≤ 2.4″" — that came from only 5 mostly low-latitude
charts and **overstated** accuracy. The 200-chart run supersedes it.

## 2. Root cause of the Lagna deviation (✔ measured)

Vedaksha computes the Ascendant with **mean obliquity** of the ecliptic; Swiss Ephemeris uses
**true obliquity** (mean + nutation in obliquity, up to ±9″). Test: substituting mean for true
obliquity in the standard Ascendant formula (validated to 0.000″ against Swiss when using true
obliquity) predicts Vedaksha's deviation with **correlation 1.000, slope 1.00**, residual 0.08″.
The effect scales with the Ascendant's speed, i.e. with latitude (≈0 at the equator).

Why it matters: ≤ 19″ ≈ 0.005° — irrelevant to interpretation except when the Lagna sits within
that distance of a sign / nakshatra / pada boundary (≈ 1 chart in several thousand), which is
exactly where a wrong sign would flip every house. **Mitigation implemented:** engines declare
error bounds; `kundli.py` withholds any sign/nakshatra/pada/house that is not identical under
±bound jitter. `test_lagna_deviation_is_fully_explained_by_mean_vs_true_obliquity` fails loudly if
Vedaksha's behaviour changes. Recommended upstream: report to the Vedaksha maintainers.
Hypotheses tested and **rejected**: equation-of-equinoxes omission (corr −0.05), latitude / year /
ascendant-position trends (|corr| < 0.2).

## 3. Corrections to the plan document (v0.1)

| # | Plan said | Finding | Action |
|---|---|---|---|
| A | Fall back to pyswisseph if Vedaksha fails | pyswisseph / Swiss / PyJHora / vedic-calc are **AGPL-3.0** (○ Astrodienst licence page, PyPI). Hosting them inside the service pulls the network clause over the product | Oracle/test use only. Production fallback = permissive engine (xalen-ephemeris, Apache-2.0, ○ docs.rs — **not yet validated by me**) or buy Swiss Professional Licence |
| A2 | Vedaksha as core engine | **BUSL-1.1** (○ repo/PyPI): commercial use needs a licence | Business decision before launch |
| B | Phase 0–1 via hosted MCP | Sends users' birth data to a third party | Self-host (`pip install vedaksha`, WASM, runs in-process — done) |
| C | Placidus/KP supported | Cusps beyond Lagna/MC not validated by me | v0.1 whole-sign only; extending needs an oracle pass |
| D | SessionConfig = ayanamsa + house system | Mean vs true node differ ≤ ~1.09°; dasha year length varies by software | `node_mode` and `dasha_year_days` added to config, hash and facts |
| E | Missing data → rule false | A withheld fact would silently make rules false | Three-valued (Kleene) predicates; Not() of UNKNOWN stays UNKNOWN |
| F | "Never blend systems" as policy | Policy ≠ enforcement | Enforced in `Rule.__post_init__` (no cross-system conditions; concordance rules carry no prose; Lal Kitab needs `translation_confidence`; remedies need declared licence) |
| G | Sockets A/B filled later | Nothing in public data can fill them (no outcome-verified astrologer judgments exist publicly) | Recruit advisory astrologers now; budget for rule audits |
| H | DPDP compliance late | ○ DPDP Rules 2025: consent-manager registration phases from Nov 2026; substantive duties incl. verifiable guardian consent for children's data from May 2027 | Minor flag + guardian consent already gate storage (`storage_allowed`); baby-kundli features need a verified-guardian flow |
| I | PyJHora as validation | It is an AGPL implementation, not ground truth | Used nowhere; Swiss is the oracle, with the caveat in §2 |
| J | — | Rule base-rate testing (idea from dekhopanchang.com, ○) | Planned for Phase 2: a "rare" yoga must not fire for ~40% of random charts |

## 4. Intake behaviours verified by test

- India's war-time (1942–45) clock handled via tzdata, with a pre-1970 reliability warning.
- DST overlap (e.g. New York 2023-11-05 01:30) refused for exact times; accepted with warning when
  the time is approximate. DST gap (2023-03-12 02:30) refused.
- (0,0) "null island", unknown tz, future dates, pre-1582 dates, missing time with `exact` → refused.
- UTC≈UT1 (< 0.9 s) used for Julian Day; Meeus reference JD values asserted.

## 5. Source areas consulted (names; deep links in the session transcript)

Vedaksha (GitHub, PyPI); Astrodienst Swiss Ephemeris licence page; PyPI PyJHora; docs.rs
xalen-ephemeris / xalen-lalkitab (remedy text confirmed *not* bundled); Wikipedia on Brihat
Parashara Hora Shastra and Roop Chand Joshi (copyright status); DPDP Rules 2025 commentary
(Mondaq, AZB, Khaitan); arXiv 2102.12127 (palmprint line detection); Roboflow palm datasets;
saravali.github.io (ayanamsa notes); dekhopanchang.com.

## 6. Open items

1. Commercial licence for Vedaksha vs alternative engine (decision).
2. Validate xalen-ephemeris as the permissive second engine; report mean-obliquity finding upstream.
3. Validate non-Lahiri ayanamsas and Placidus/KP cusps against the oracle.
4. Advisory astrologers for Sockets A/B and rule audits.
5. Guardian-consent flow before any minor's data is stored (May 2027).

---

# Phase 2 findings (derived facts, inference, seed rules)

## 7. Source verification (✔ read, not recalled)

The yoga definitions were compared against an English ebook of *Parashara Hora Sastra*
(archive.org item `ParasharaHoraSastra`, translator not stated) and the Sagar edition's table of
contents (wisdomlib). The text was read through an automated fetcher that paraphrased the
passages, so **verse numbers are unconfirmed and the comparison is of conditions, not wording**.

**Chapter numbering differs between editions.** E.g. Nabhasa yogas are Ch. 35 in the ebook but Ch. 37
in the Sagar edition; Raja yogas Ch. 39 vs Ch. 41; Pancha Mahapurusha Ch. 75 in the ebook and not
listed in Sagar's contents. Every rule therefore carries the edition it cites, and `definition_checked`
is only allowed when a chapter and edition are both pinned (enforced in `rules.py`).

| Verified against the ebook (`definition_checked`) | Ch. | Finding |
|---|---|---|
| Pancha Mahapurusha | 75 | own/exalted sign AND kendra from the **Lagna only** (not the Moon) |
| Sunapha / Anapha / Durudhara | 37 | planet "other than the Sun" 2nd / 12th / both from the Moon |
| Kemadruma | 37 | text also requires **no planet in a kendra from the Lagna** - stricter than the common modern definition. Both are shipped as separate rules (2.7% vs 32% of charts) |
| Vesi / Vosi / Ubhayachari | 38 | planet "other than the Moon" 2nd / 12th / both from the Sun |
| Raja yoga (kendra lord x kona lord) | 34 | conjunction, exchange **or full aspect**; same planet ruling both also qualifies |
| Nabhasa Asraya (Rajju/Musala/Nala) | 35 | all planets in movable / fixed / dual signs |
| Daridra: Mars+Saturn in 2nd; Sun in 2nd aspected by Saturn | 42 | Mercury's aspect reverses the first |

**Not verified (kept `draft`):** Gajakesari (attributed to Phaladeepika 6.1 by a secondary site only),
Vipareeta Raja, Neecha Bhanga, Budhaditya, Chandra-Mangala, Guru-Chandala, Angaraka, Shrapit, Vish,
Manglik, Kaal Sarp/Amrit (a later tradition; the Kaal Sarp half-naming differs between sources),
Parivartana types, most dhana pairs. Dignity and Lagna-lord *interpretations* are synthesized from
standard significations (`provenance: synthesized`).

**Deliberately not built:** combustion (degree thresholds differ by source and none was pinned),
moolatrikona, Rahu/Ketu dignity and aspects (traditions disagree), the Adhi yoga (wording ambiguous),
Nabhasa Dala/Sankhya groups (conditions ambiguous or exclusion-dependent).

## 8. Measurements

- **Independent cross-check:** 15 rules re-implemented planet-centrically from raw Swiss Ephemeris
  longitudes agree with the production pipeline on all 498 compared charts each (7,470 comparisons, 0 disagreements).
- **Frequencies:** see `docs/BASE_RATES.md`. My a-priori estimates assumed independent planets and were
  wrong for 3 of 74 rules (Kemadruma-common, Maha and Dainya Parivartana: measured ~29-32% against
  estimated 15-24%) because planets cluster (Mercury/Venus near the Sun). Declarations were updated to the
  measurement only after the cross-check confirmed the implementation.
- **What a chart produces (3000 charts):** mean 13.3 firings (median 13, max 24); only 3.3 are
  definition-checked, 4.9 classical-text. **98% of charts get at least one cautionary-flagged reading**
  (78% excluding debilitation and Manglik). Raja-yoga pair (strict reading) in 73%, dhana pair in 65%,
  Pancha Mahapurusha in 34%.

**Consequence for Phase 3:** listing everything that fires would tell almost every user they have both a
Raja yoga and several afflictions. The Composer needs (a) a salience/priority model (Socket A), (b) a cap and
grouping by life area, (c) the `adverse` flag routed through the Safety gate, and (d) honesty that frequency
is part of the finding ("this is present in about a third of charts").

## 9. Phase 2 corrections and open items

1. **Edition pinning is mandatory** (above). Obtain a licensed/commercial-use edition of BPHS before shipping
   any verse-level citation; the ebook used here has no stated licence.
2. **Raja-yoga strictness needs an astrologer's ruling**: the text as read admits a one-way full aspect, which
   would put "Raja yoga" in nearly every chart; the strict reading is used and flagged in `notes`.
3. **No rule is `astrologer_audited`.** Every `draft` and `definition_checked` rule needs a practising
   astrologer's review (a test asserts none is claimed audited prematurely). `docs/rules_parashari.json`
   is the export for that audit.
4. Cancellation conditions (Kemadruma-bhanga, Neecha-bhanga beyond one criterion, Manglik cancellations) are not
   implemented; adverse readings say so in their wording.

## 10. Phase 3 (composer, gates, chat): decisions and findings

**Crisis resources (read from PIB, not recalled).** Tele-MANAS 14416 / 1-800-891-4416 (PIB release PRID=2022057; the page does
not state operating hours, so none are claimed) and KIRAN 1800-599-0019, 24x7, 13 languages (PRID=1652240). findahelpline.com is
used for people outside India. These numbers should be re-verified before launch; helplines change.

**Design decisions**
1. *Hard stops precede everything.* Crisis wording is checked first, then lifespan/death; neither reaches selection or a model.
2. *The model never writes safety text.* Caveats, declines, facts, evidence lines and labels are system-generated; gates accept
   framing/caveat text only from the phrasebook or text with no chart entity.
3. *Grounding is mechanical.* Entity extraction (planets, signs, yogas, houses, nakshatras, years, degrees; English, Devanagari,
   common Hinglish spellings) is compared with the evidence of the cited rules. A sentence can be fluent and still be rejected.
4. *Fail closed.* LLM failure/timeouts/bad JSON/gate failure ⇒ retry ⇒ template. If the template ever fails the gates (a bug) the
   user receives a minimal safe message, never unverified text.
5. *Volume control.* Because ~98% of charts carry a cautionary reading, overview answers show at most one and never lead with it.

**Bugs found by the property test (300 charts x 14 questions x 3 variants).** A reading filed under another topic used the words
"close relationships" in a minor's chart; minors' readings are now also filtered on wording, not only on topic.
**Design judgement call:** "should I invest in crypto for money?" matches a wealth keyword; when the only wealth cue accompanies a
financial-advice request the Pandit gives no wealth reading, only the decline.

**Not verified / open**
- Live LLM behaviour (adapter untested against the API; prompt tuned only against a fake client).
- Hindi/Hinglish phrase lists (native-speaker review), and a Hindi template composer.
- Whether users read 400-word answers; the readings' *wording* still awaits astrologer review (0 rules audited).
- Rendering was checked in headless Chromium at 1200 px and 390 px widths; no accessibility audit or real-device test.

## 11. Hindi (v0.4)

**What was built.** Devanagari-aware planner and gates (shared `hindi.py`), Hindi fixed sentences, Hindi evidence lines,
language-aware composers, language switch in the web page, and `tools/live_llm_check.py`.

**Bugs found while building it (both fixed, both covered by tests).**
1. The Devanagari danda (।) is inside the Unicode Devanagari block, so "आपको धन मिलेगा।" was not flagged as a future claim: the
   word-boundary look-around treated the sentence-final danda as a letter. Boundaries now exclude it.
2. Normalising patterns turned a Devanagari-digit range inside a regex character class into `0-ॿ`, silently widening the class;
   the class is now written with raw `\u` escapes that normalisation cannot touch.
Also: the answer to "what is my dasha?" now contains only the dasha (previously six unrelated readings were appended).

**Not verified / open**
- Hindi wording of every fixed sentence is a draft by the assistant: needs a native-speaker read (tone, gender-neutral phrasing,
  helpline wording) and an astrologer's read of astrological terms.
- Real model Hindi output has not been seen. The gates are tested with hand-written good and bad Hindi, not with live generations.
- Hindi *rule* wording does not exist; Hindi readings depend entirely on the LLM composer.
- Hinglish answers use English fixed sentences by design (no standard Latin-script Hindi spelling to check against).


## 12. Numerology and Hinglish (v0.5)

**Numerology.** Indian/Chaldean scheme: Mulank = day reduced to one digit; Bhagyank = all digits of the date; name number =
Chaldean letter values (Latin letters only, >= 2 letters); personal year = day + month + current year. Number->planet:
1 Sun, 2 Moon, 3 Jupiter, 4 Rahu, 5 Mercury, 6 Venus, 7 Ketu, 8 Saturn, 9 Mars. Not implemented on purpose: master numbers
(11/22/33), Pythagorean names, Lo Shu grid, "lucky" colours/gems/remedies. **No classical Vedic source exists**; every rule is
`later_tradition` + `draft`, and every numerology answer carries a fixed note saying so. Spelling changes the name number.
- *Why numerology is a separate system:* the rule schema forbids blending, and a model must not decide that numerology
  "confirms" a kundli. The system itself adds "Both lenses single out X" notes from two facts (the number's planet; its dasha
  role or sign dignity in the kundli). That is a coincidence note: with 9 numbers and 9 planets, an overlap by chance is common.
- *Accuracy.* The request was to get closer to accurate answers by combining. There is no data showing the combination is
  more accurate; what it does give is (a) an answer when birth time is unknown, because numerology needs only the date, and
  (b) a second, independent-looking lens the user can compare. Treat accuracy as an open question for a blinded test.
- *Verified by test:* hand-checked numbers, exactly one rule of each family fires for any date, rule frequencies sit in the
  declared band over every date 1950-2025, no statement cites two systems, minors see no marriage wording in either lens.

**Hinglish.** `detect_language` returns `hg` for Latin-script Hindi (strong marker words, or two weak ones). Hinglish wording of
every rule lives in `rulepacks/hinglish.py` and `rulepacks/numerology.py`; tests require the same planets, signs, yogas and
houses as the English wording and no safety-pattern hits. Gates gained Hinglish house ordinals ("7th bhaav", "saatve bhaav"),
future-tense verbs, medical, remedy, financial, fear and minor vocabulary.

**Bugs found by the new tests (fixed).** Pandit wording "pratiyogi" matched a Hinglish future-tense pattern ("-ogi"); the English
house detector missed "1st and 11th houses" (so rule wording was only partly grounded); a Hinglish numerology sentence contained
"pyaar", which the minor filter blocks while the English one did not; Hinglish grammar for several Mulank/Bhagyank lines read
badly and was rewritten.

**Not verified / open.** All Hinglish and Hindi wording needs native-speaker and astrologer review. Hindi (Devanagari)
readings still need the LLM composer. Interface checked in headless Chromium at 1280 and 390 px, light mode; no dark-mode
screenshot review, screen-reader test or real-device test.


## v0.6 (AstroMuni): what changed and what it does not prove

- **Simulated latency.** The 2-3 s "thinking" is a deliberate UI delay (the engine answers in milliseconds). It makes the
  exchange feel considered; it does not mean more analysis happened, and the interface does not claim it did.
- **Horoscope** is built from the same verified readings as the chat, grouped by life area, de-duplicated across areas.
  It is a set of tendencies from the chart, not a forecast; there is no transit/rashifal engine, and three areas
  (education, children, family) still have no rules, so they are stated as unavailable rather than filled in.
- **Palm photos** are collected but unused by any model or rule. Reason to ask for them now: to learn whether users will
  provide them and to pass them to a human pandit on request. Reason to be careful: they are biometric-adjacent personal
  images. They are re-encoded client-side (metadata stripped), capped at ~600 KB, kept only in session memory, and written
  to disk only on an explicit pandit request with a separate tick box.
- **Real pandit** is a lead form, not an integrated service: no scheduling, payment or notification exists.
- **Not verified:** layout checked in headless Chromium at 1280 and 390 px (Hinglish; Hindi/English only by test of copy
  parity, not by screenshot), no screen-reader or real-device test, no dark mode. Hinglish/Hindi wording remains unreviewed
  by native speakers; the LLM path was not run live.
