# AstroNaradMuni 1.3.0

NaradVani in 3D (page side). The Ask screen can now show a real-time 3D NaradVani instead of the 2D portrait, with the portrait as the automatic fallback.

- **How:** `static/avatar3d.js` (classic script, lazy-loads three.js, GLTFLoader and the meshopt decoder from `static/vendor/` by absolute path, strict-CSP safe). `live.js` stays the speech brain (text position, word-boundary re-sync, mic) and hands the stage over once the model is ready; its public `AMLive` API is unchanged (`is3d()` added).
- **Motion:** text to the 15 Oculus mouth shapes (Latin and Devanagari, digraphs sh/ch/th/ph, labials close the lips), eased in about 40 ms and out in about 70 ms; natural blinks (double blinks 18%); brows lift on questions and new sentences; small eye saccades; breathing, head sway, a nod while speaking, a tilt while listening; a light resting smile. Bones are rotated about world axes, so the export's bone roll does not matter. Reduced-motion users get calmer movement.
- **Fallback chain:** 3D, then the 2D portrait, then the still image. No WebGL, a missing or failed GLB, a lost context, or a device that stays slow (drops to 1x pixels once, then gives up) all keep or restore the portrait. `?avatar=2d` forces the portrait.
- **Server:** `.glb` is served as `model/gltf-binary`. The CSP gains `'wasm-unsafe-eval'` in `script-src` only, which the meshopt decoder needs to compile WebAssembly. No `'unsafe-inline'`, no `'unsafe-eval'`.
- **Avatar:** `static/vendor/naradvani.glb` (our own MPFB build, 5 MB, licences in `docs/ASSETS.md`). `?model=mp` loads `vendor/naradvani_mp.glb` for private local testing only; that file is git-ignored because its licence is unresolved.
- **Still to do by hand (no npm in the build sandbox):** run `python3 tools/vendor_three.py` once, then follow `docs/AVATAR_PAGE_VERIFY.md` (real browser check, camera framing, Playwright).
- 23 new tests (`tests/test_v130_pure.py`, with node harnesses for the driver and the hand-over); 83 pure tests pass in total.

# AstroNaradMuni 1.2.0

NaradVani comes alive. The Ask screen now has two modes.

- **Chat (default): silent.** NaradVani only blinks naturally and breathes.
- **Talk:** he greets you, reads his replies in a male Indian-English / Hindi voice (the browser's own speech engine), his lips follow the words, eyebrows lift on questions, and his head nods slightly. A mic button lets you ask by speaking (browser speech recognition, Hindi or English). Tap the mic while he speaks to stop him. Leaving the Ask page silences him.
- **How:** `static/live.js`, no dependencies, CSP-safe. The portrait is drawn on a canvas: eyelids are built from the skin above each eye, and the mouth opens by stretching the mouth interior and moving the lower lip and chin, feathered into the photo. Lip movement comes from the text (vowel openness, lips closed on m/b/p) and is re-synced on every word boundary the browser reports. It is an approximation, not audio-exact.
- **Honest limits:** this is a 2D living portrait, not 3D or Unreal. Voice quality and Hindi voice availability depend on the browser and OS. `docs/AVATAR_ROADMAP.md` lays out the real 3D / TTS / Unreal path with costs and licence cautions.
- The old "read replies aloud" chip is replaced by the Chat | Talk switch. Voice and lip-sync are never on in Chat mode. The "AI-generated character" note stays.
- 12 new tests (`tests/test_v120_pure.py`, including a node harness for the lip-sync logic); 60 pass in total.

# AstroNaradMuni 1.1.3

- **Raja yogas, computed** (`yogas.py`): kendra-trikona links (same sign, facing, or exchanging signs), yogakaraka planet, Dharma-Karmadhipati, and Neecha Bhanga cancellation. Sign-level only; skipped when the Lagna is unreliable.
- **Dasha timing windows** (`timeline.py`): the running dasha is projected forward in Vimshottari order, and sub-periods tied to the topic are shown as activation windows for the next five years ("Apr 2028 to Jun 2031: Venus inside Saturn"). Never an event date. If our timeline disagrees with the engine's own Maha end date, no windows are shown. Appears under "Why this answer?" for every topic, and in the reply when the user asks "when...?" / "kab...?".
- **Expert case library** (`expert.py`, `expert_data/`, `tools/expert_check.py`): a place for real advice from experienced astrologers. Cases are validated (consent required; phone/email, death predictions, guarantees, fear, fees, medical claims and investment instructions are rejected), indexed as a new `expert` retrieval tier, and shown as "An experienced astrologer on our panel often advises..." only when the question shares real content words with a case. Private by default: `expert_data/cases/` is git-ignored. This is retrieval, not model training.
- 15 new tests; 48 pass in total.

# AstroNaradMuni 1.1.2

NaradVani now has a face, and the Ask page is a conversation with someone rather than a form.

- **Split Ask screen.** Desktop: NaradVani's portrait on the left (concentric rings, name, "AI guide" chip, live status "Listening to you" / "NaradVani is typing…" with pulsing rings), chat on the right. Phone: character on top, chat below.
- **Real-image character.** `naradvani.jpg` / `naradvani-avatar.jpg` replace the vector sage. The image was generated with an AI tool; the visible corner sparkle was cropped out. The file still carries the generator's invisible provenance watermark (SynthID), which is not removed, and the UI says plainly that NaradVani is an AI-generated character.
- **Chat details.** Context chips (Lagna, Moon nakshatra, current Maha dasha), a "Did this feel useful? Yes / Not quite" row (kept on-device, not sent anywhere), pill composer, optional "read replies aloud" using the browser's own voice (hi-IN / en-IN).
- **Yogas.** New computed check, `yogas.py`: Gajakesari, Budhaditya, Chandra-Mangal, the five Mahapurusha yogas, and Guru-Chandal (worded gently). Sign-level rules only; Mahapurusha is skipped when only the Moon chart is available. Ask "which yogas do I have?", "mere yog kya hain", "मेरे योग क्या हैं".
- Server now serves `.jpg`; package data includes `static/*.jpg`.
- 12 new tests (`tests/test_v112_pure.py`); 33 pass with the earlier suites.

# AstroNaradMuni 1.1.1

The portal is now **AstroNaradMuni** and the assistant is **NaradVani**. Chatting is free: no timer, no wallet.

- New original NaradVani character (`naradvani.svg`, our own design) shown as an avatar beside every reply, with a "typing" indicator and a friendlier welcome.
- More of what people actually ask: going abroad (study / work / settle), property, Manglik, Kaal Sarp, kundli matching, Panchang and Rahu Kaal.
- Manglik and Kaal Sarp are computed from your chart (`doshas.py`). Manglik is explained as a mild idea, never a bar to marriage. Kaal Sarp is sign-level only, so a planet sharing a sign with Rahu/Ketu is reported as "borderline" instead of a confident yes.
- 30 plain-language reference answers (`kb_faq.py`), written in our own words: doshas, Sade Sati, dashas, nakshatra, retrograde, Navamsa, Panchang, remedies, gemstones, accuracy without birth time and more.
- Remedies never sell: no gemstone, ring or puja is ever suggested for purchase; free traditional practices only.
- Quick suggestion chips and intent patterns widened (breakup, startup, promotion, NEET/JEE/UPSC, visa, flat/plot, Hinglish and Hindi phrasing).

Restart the server after upgrading: `python3 -m aipandit.web --port 8001`.

# AstroMuni 1.1.0

Plain-language release: answers now sound like a person, and the app is simpler to use.

- New conversation layer (`voice.py`): short, personal answers in English, Hinglish or Hindi (language follows how you write). House numbers and lords moved behind "Why this answer?".
- AstroMuni asks one follow-up question and continues from your reply (field of study/work, work status, relationship status, money goal, timing). The chat now remembers the last few messages.
- Dasha explained in plain words ("Right now you are in your Jupiter phase, running till Mar 2027").
- Unknown birth time no longer blocks answers: houses are counted from the Moon sign (Chandra Lagna), shown with low confidence and a note.
- Horoscope: a plain paragraph plus Love, Career, Health and Money meters (transit support, not a prediction). Planet detail is behind "Why this reading?". No lucky numbers or colours: nothing in the engine supports them.
- Onboarding is one question per screen: language, name, gender, date, time (with "I don't know my time of birth"), place with map pin, optional palms.
- Cleaner home (today's reading, ask box, four tools) and a chat-style Ask page with tap-to-reply buttons.
- Fixes carried from v1.0.x: OpenStreetMap tile CSP and Referrer-Policy, vendored Leaflet, noscript CSP class.

Restart the server after upgrading: `python3 -m aipandit.web --port 8001`. Set ANTHROPIC_API_KEY for more natural wording (it only rewrites what the engine found).

# AstroMuni 1.0.0

- New onboarding: language -> birth details (OpenStreetMap/Leaflet pin, Nominatim search) -> optional palm photos (skippable).
- New responsive UI (sidebar / icon rail / bottom tabs), en / Hinglish / Hindi.
- New brain: retrieval (BM25) + rules over chart facts; optional LLM polish via ANTHROPIC_API_KEY.
- Real gochara horoscope, strict Ashtakoota, sunrise-based Abhijit / Rahu Kaal. Fabricated scores and fixed timings removed.
- tools/scrape_kb.py: open / public / restricted-snippet harvester (robots.txt obeyed).
- tools/vendor_assets.py: installs Leaflet (integrity-checked).

Setup: `python3 tools/vendor_assets.py`, optionally `python3 tools/scrape_kb.py`, restart `python3 -m aipandit.web --port 8001`.
