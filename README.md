# AstroNaradMuni / AstroMuni (formerly AI Pandit) — kundli, horoscope and an AI guide in English, Hinglish and Hindi (v1.4.0)

The deterministic core of AstroNaradMuni (`aipandit` v1.4.0): **birth input → validated chart → immutable facts → classical working (`reasoner.Sheet` + 131-rule engine) → gated plain-language answer**.
No LLM is ever allowed to calculate. Every statement traces back to a computed chart fact or classical rule, and nothing reaches the user without passing the deterministic grounding and safety gates (`gates.py`).
See [`CHANGELOG_v1.md`](CHANGELOG_v1.md) for the v1.0.0 – v1.4.0 release history (`advisor.py`, `reasoner.py`, `v10_engine.py`, live-path safety gates, Hindi script parity, and NaradVani voice/portrait integration).

```
BirthInput ──intake──▶ ResolvedBirth ──engine──▶ RawChart ──kundli──▶ FactStore (frozen)
  (tz, DST,             (UTC, JD,                 (sidereal               facts + withheld
   certainty)            window)                   longitudes)             + warnings
```

## What exists

| Module | Job |
|---|---|
| `intake.py` | Historical timezone (IANA), DST overlap/gap detection, null-island refusal, Julian Day, certainty windows, consent gate (minors need guardian consent), `birth_hash` cache key |
| `engines/` | `AstronomyEngine` protocol + Vedaksha adapter (whole-sign, Lahiri validated) |
| `kundli.py` | Lagna, 9 grahas (sign, nakshatra, pada, house, retrograde), Vimshottari dasha → facts. **Withholds** anything that is not stable (see below) |
| `fact_ir.py` | Append-only, freezable fact store. Conflicting writes raise; the same predicate in two systems never merges |
| `predicate.py` | Three-valued (TRUE / FALSE / UNKNOWN) rule conditions. A withheld fact makes a rule UNKNOWN, never FALSE |
| `rules.py` | Rule schema with **schema-level** guarantees: no cross-system blending, concordance rules carry no prose, Lal Kitab rules need `translation_confidence`, remedies need a declared licence |

## Phase 2: derived facts -> rules -> findings

```
Kundli facts ──derive.enrich──▶ + dignity, lordship, conjunction, aspects, lord relations
             ──inference.infer(rules)──▶ firings (with fact ids) | undetermined (with missing facts)
```

| Module | Job |
|---|---|
| `derive.py` | Deterministic classical relationships; a derived fact exists only if all its inputs do |
| `inference.py` | Evaluates rules: *fired* (cites the facts), *undetermined* (names the withheld facts), or not fired |
| `rulepacks/parashari.py` | 74 seed rules. Each declares `review_status`, `provenance`, `adverse`, expected `rarity`, auditor `notes`, edition-pinned source |
| `diagnostics.py`, `tools/base_rates.py` | Measure how often each rule fires over random charts |

Rule status today: **18 `definition_checked`** (conditions compared with a named chapter/edition),
**56 `draft`**, **0 `astrologer_audited`**. 21 rules are flagged `adverse` for the Safety gate.
See `docs/BASE_RATES.md` for measured frequencies and `docs/RESEARCH_FINDINGS.md` §7-9 for what was and was not verified.

```bash
aipandit-kundli ... --yogas                              # list fired / undecidable rules
aipandit-kundli ... --yogas --min-status definition_checked
```

## Run

```bash
pip install -e '.[dev]'          # dev extra pulls pyswisseph (AGPL) as a TEST ORACLE ONLY
pytest                           # 220+ tests (~80 s; includes 3000-chart base-rate check)
pytest -m oracle -s              # 200-chart comparison against Swiss Ephemeris
aipandit-kundli --date 1990-05-15 --time 14:30 --place Bhopal \
                --lat 23.2599 --lon 77.4126 --tz Asia/Kolkata
```

## Honesty mechanisms (the part that makes it "accurate")

1. **Uncertain birth time is never guessed.** The chart is recomputed at ±window
   (`approx_15min`→15, `part_of_day`→360, `unknown`→720 minutes). A fact is asserted only if
   identical at every sample; otherwise it is recorded in `Kundli.withheld` with a reason.
2. **Engine precision is never overclaimed.** Each engine declares measured error bounds
   (`lagna_error_arcsec`, `planet_error_arcsec`). A sign/nakshatra/pada closer to a boundary than
   that bound is withheld, the same way. A Moon near a nakshatra boundary withholds the dasha.
3. **Ambiguity is refused, not resolved.** DST overlap with an exact time, non-existent local
   times, failed geocodes (0,0), unknown timezones → `IntakeRefusal` with what to ask the user.
4. **Configuration is part of the cache key.** Ayanamsa, node mode (mean/true differ ≤1.1°),
   house system and engine version are hashed; dasha year length (365.25 d) is a recorded fact.

## Licensing posture (read before shipping)

- **Vedaksha is BUSL-1.1** — fine for development; a commercial licence is needed for a paid
  product. Decide before launch.
- **Swiss Ephemeris / pyswisseph / PyJHora / vedic-calc are AGPL-3.0** (or paid Swiss
  Professional Licence). They are imported **only** in `tests/test_oracle.py`. Nothing under
  `src/` may import them — their network clause would otherwise cover the hosted service.
- Lal Kitab text (Roop Chand Joshi, d. 1982) stays in copyright until ~2043 and each edition
  is separately copyrighted; BPHS translations are copyrighted. Rules must be written in our
  own words with citations; `Source.licence` defaults to `unspecified` and remedies are
  blocked unless a licence is declared.

## Known limits (deliberate, v0.1)

- **Whole-sign houses only.** Placidus / KP cusps have not been validated; requesting them raises.
- **Only Lahiri is validated.** Other ayanamsas work but every chart carries a warning.
- **Lagna accuracy is ≤ ~19″, not sub-arcsecond** — Vedaksha uses mean obliquity where Swiss uses
  true obliquity. Details and the guard in `docs/RESEARCH_FINDINGS.md`.
- `confidence` on facts is 1.0 for computed values. It is reserved for Socket A (evidence
  weighing) and will not be used to encode astronomical uncertainty — that is what *withheld* is for.
- Polar latitudes: the engine refuses (`EngineLimit`) rather than silently falling back.

## Phase 3: the Pandit (selection, composition, gates, chat)

```
question ──planner──▶ crisis / death  ─▶ fixed reply (no astrology, no model)
             │
             └▶ readings ──select──▶ compose ──gates──▶ answer
                (caps, supersedes,   template (default)   grounding + safety, plain code
                 adverse limit,      or LLM (optional)    fail ⇒ retry ⇒ template ⇒ safe minimal message
                 minor/health blocks)
```

| Module | Job |
|---|---|
| `planner.py` | Keyword intent routing (English/Hindi/Hinglish). Crisis and lifespan questions are hard stops; medical/financial/legal parts are declined; timing questions get "no dates" |
| `salience.py` | Default Socket-A: picks at most 6 readings, 3 per topic, **1 cautionary** (2 if the user asked about that topic), cautions never lead, subsumed yogas dropped |
| `composer.py` | `TemplateComposer` (rule wording + frequency + provenance label; no model) and `LLMComposer` (model rephrases reading prose only, as JSON with rule citations) |
| `gates.py` | Every statement must cite a rule that fired **and** was selected; every planet/sign/house/yoga/year it names must appear in that evidence; banned-phrase safety checks; cautionary text only with the "not a prediction" caveat; minors; uncertain-time disclosure |
| `phrasebook.py`, `phrasebook_hi.py`, `phrasebook_hg.py` | All fixed system sentences (caveats, declines, crisis reply) in English, Hindi and Hinglish, in reviewable places |
| `orchestrator.py` | `Pandit.start(birth)` / `ask(session, question)`; never emits text that did not pass the gates |
| `chat.py`, `web/` | `aipandit-chat` (terminal) and `aipandit-web` (localhost page: birth form, North-Indian kundli, chat with "Why this?" evidence) |

```bash
aipandit-chat --adult --date 1990-05-15 --time 14:30 --place Bhopal --lat 23.2599 --lon 77.4126 --tz Asia/Kolkata
astromuni-web --port 8000         # (aipandit-web still works) then open http://127.0.0.1:8000
pip install -e '.[llm]' && export ANTHROPIC_API_KEY=... && aipandit-chat --llm ...   # optional LLM composer
```

**What the model may and may not do.** With the LLM composer on, the model writes only the wording of the
selected readings. Intro choice, dasha facts, "Why this?" evidence, labels and every caveat are generated by the
system, so a model cannot drop a disclaimer. Its output is untrusted until the gates pass; failure twice ⇒ the
template answer is used. Crisis and lifespan questions never reach the model.

**Measured over 300 random charts** (overview question): 6.0 readings shown on average (cap 6), at most 1
cautionary reading, ~400 words, 0 empty answers. 14 question types × 300 charts × adult/minor/uncertain-time
all pass the gates with the template composer (`tests/test_phase3.py::test_property_*`).

### Hindi (v0.4)

| What | Status |
|---|---|
| Devanagari, Hinglish and English **questions** | Understood (`hindi.py`, `planner.py`): spelling variants folded (नुक्ता, चंद्रबिंदु, Devanagari digits); crisis / lifespan hard stops work in Devanagari |
| Hindi **fixed sentences** (caveats, declines, crisis reply, dasha statement, "Why this?" evidence lines) | Written (`phrasebook_hi.py`, `explain.py`); **draft, not yet reviewed by a native speaker** |
| Hindi **reading text** | Only through the LLM composer (rule wording is English). Without a working LLM a Hindi question with readings gets the English answer plus a one-line Hindi note; questions with nothing to show (declines, coverage gaps, dasha, hard stops) are answered fully in Hindi |
| Gates in Hindi | Planet / sign / house ("सातवें भाव") / yoga / nakshatra / year (incl. २०३१) names must be grounded in the cited evidence; Hindi safety lexicon (मृत्यु, आयु, कैंसर, जरूर, रत्न, उपाय, निवेश, श्राप, future-tense -गा/-गी/-गे ...) |
| Web page | Language switch (English / हिन्दी), Hindi chips and evidence labels |

**Live LLM check.** The LLM path has never run against the live API from here. Run it yourself:
`pip install -e '.[llm]' && export ANTHROPIC_API_KEY=... && python tools/live_llm_check.py --show`.
It asks 17 English / Hinglish / Hindi questions (including injection attempts), and reports accepted-first-try, retried
and fallback counts per language, the most common gate rejections, and writes every answer so you can read the Hindi.
`--selftest` runs the harness against a fake model to prove the harness works offline.

**Known limits (Phase 3)**
- The `AnthropicClient` adapter has **not been run against the live API** (no key/network here); the LLM path is tested with a fake client including adversarial outputs. Test it live before relying on it.
- Hinglish (Latin-script Hindi) questions are answered with English fixed sentences; Devanagari questions get Hindi ones. Gates check names, numbers and banned phrases in Hindi, but **cannot check that Hindi prose is correct, natural or faithful** to the rule: that needs a native-speaker/astrologer read of real model output (see the live check).
- Devanagari matching is substring-based: weekday words such as शनिवार/मंगलवार count as mentioning the planet, so a harmless sentence may be rejected (fails safe). The nakshatras हस्त, मूल, चित्रा, पुष्य are not detected in Hindi text (too common as ordinary words).
- No readings exist yet for education, children or family; the Pandit says so instead of improvising.
- 400 words is long for chat; shorter default answers and "tell me more" turns are a UX item.
- Questions are single-turn: no memory of earlier questions beyond the session's chart.
- The web server is a development server (no auth, TLS or rate limiting, in-memory sessions). Consent and retention policy must be decided before any hosting.
- Selection weights are metadata-based placeholders (status, provenance, rarity). Real weighting needs astrologer data (Socket A); intent routing is keyword-based (Socket B).
- 0 rules are `astrologer_audited`; all answers carry the "provisional" notice where draft rules are used.

## v0.6: AstroMuni - separate tools, new look

**Run (Mac/Linux):** double-click `start.command` or run `bash start.sh` (creates `.venv` on first run, needs Python 3.10+).
Manual: `pip install -e . && astromuni-web`.

Flow: **details** (name, gender, date/time/place of birth, photos of both palms) -> **choose a tool** -> Kundli | Horoscope |
AstroMuni (AI guide, with a hazy seated silhouette) | Real pandit. The details are entered once and reused by every tool.

| What | Status |
|---|---|
| **Thinking pause** | The answer is fetched at once, then shown after a 2.2-3.4 s pause with "thinking" lines and a progressive reveal. This is **presentation pacing**, not computation time. |
| **Kundli** | Chart, planet table, current dasha + the 120-year dasha timeline, numerology numbers |
| **Horoscope** | Life-area tendencies (character, mind, career, wealth, marriage, status) assembled from the same rule-backed readings as the chat. **Not** a daily/weekly rashifal: no transit engine yet. Education, children and family have no rules yet and are listed as "not available" |
| **AstroMuni** | The chat, same rules and gates. It is labelled an AI, not a person; the silhouette is a generic figure |
| **Real pandit** | A request form (phone, slot, topic). Saved to `aipandit-feedback/pandit_requests.jsonl` **for the owner to follow up by hand**: nothing is sent automatically |
| **Palm photos** | Collected, re-encoded in the browser (EXIF/GPS dropped), kept in memory for the session. **AstroMuni does not read palms.** Photos reach disk only if the user sends a pandit request and ticks the palm box |
| **Theme** | Beige/white-yellow gradient, chocolate-brown text, strict CSP unchanged (`blob:` added to `img-src` for the photo preview only) |

Set `REQUIRE_PALMS = false` at the top of `web/static/app.js` to make the photos optional.

## v0.5: numerology, Hinglish, new interface, first-test tooling

**Quickstart (details in `docs/FIRST_TEST.md`)**

```bash
pip install -e .
aipandit-web                       # http://127.0.0.1:8000 ; feedback -> ./aipandit-feedback/feedback.jsonl
python tools/feedback_summary.py   # read what testers said
```

| What | Status |
|---|---|
| **Numerology lens** | Mulank, Bhagyank, name number (Chaldean), personal-year number from the civil date and name; 36 rules, all `draft` / `later_tradition`. Works without a birth time. Kept **separate** from the kundli: no statement blends the two (a gate rejects it) |
| **Combined answers** | Readings are labelled Kundli / Numerology; where the number's planet is also the running dasha lord or is exalted / in its own sign (or debilitated, adults only) in the kundli, the system adds a "Both lenses single out ..." note built from facts of both systems. Total readings stay <= 6 (numerology takes 2 in an overview, 3 on a topic, 4 when asked for) |
| **Hinglish** | Latin-script Hindi is detected and answered in Hinglish **without any model**: Hinglish wording exists for all 110 rules and every fixed sentence; Hinglish safety vocabulary and house/planet detection are in the gates |
| **Interface** | Static page (`web/static/`), fonts bundled (OFL, no CDN), Hinglish / हिन्दी / English switch, kundli chart + numbers panel (bottom sheet on phones), per-answer thumbs, overall feedback, strict CSP |
| **Feedback** | `/api/feedback` -> JSONL (ratings, comments, rule ids, composer, language). Question text only with consent; birth details and name never |

**Honest limits.** Combining two systems does not make an answer more accurate; it makes it broader, and neither has a
validated predictive record. Hinglish and Hindi sentences are unreviewed by native speakers; 0 rules are astrologer-audited;
the LLM path has not run live; the web server has no auth or TLS. Details in `docs/RESEARCH_FINDINGS.md` section 12.

Fonts: Young Serif, Figtree, Tiro Devanagari Hindi, Hind (SIL OFL 1.1; licences in `web/static/fonts/`).
Audit export: `python tools/export_rules.py > docs/rules_all.json`.
