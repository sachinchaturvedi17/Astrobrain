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
