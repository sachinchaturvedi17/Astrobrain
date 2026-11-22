# AstroMuni 1.0.0

- New onboarding: language -> birth details (OpenStreetMap/Leaflet pin, Nominatim search) -> optional palm photos (skippable).
- New responsive UI (sidebar / icon rail / bottom tabs), en / Hinglish / Hindi.
- New brain: retrieval (BM25) + rules over chart facts; optional LLM polish via ANTHROPIC_API_KEY.
- Real gochara horoscope, strict Ashtakoota, sunrise-based Abhijit / Rahu Kaal. Fabricated scores and fixed timings removed.
- tools/scrape_kb.py: open / public / restricted-snippet harvester (robots.txt obeyed).
- tools/vendor_assets.py: installs Leaflet (integrity-checked).

Setup: `python3 tools/vendor_assets.py`, optionally `python3 tools/scrape_kb.py`, restart `python3 -m aipandit.web --port 8001`.
