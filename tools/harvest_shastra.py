"""
Astrobrain Classical Knowledge Harvester (Step 1)
Downloads public-domain classical texts across Jyotish, Palmistry, and Vedas/Upanishads,
cleans noise, filters relevant passages, and writes `knowledge_base/shastra_corpus.jsonl`.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import ssl
import time
import urllib.request
from pathlib import Path

OUT_DIR = Path("knowledge_base")
CORPUS_FILE = OUT_DIR / "shastra_corpus.jsonl"
SUMMARY_FILE = OUT_DIR / "CORPUS_SUMMARY.md"

SOURCES = [
    {
        "id": "bphs_vol1",
        "title": "Brihat Parashara Hora Shastra (Vol. 1)",
        "discipline": "jyotish",
        "url": "https://archive.org/stream/BPHSEnglish/BPHS%20-%201%20RSanthanam_djvu.txt",
        "quick": True,
    },
    {
        "id": "bphs_vol2",
        "title": "Brihat Parashara Hora Shastra (Vol. 2)",
        "discipline": "jyotish",
        "url": "https://archive.org/stream/BPHSEnglish/BPHS%20-%202%20RSanthanam_djvu.txt",
        "quick": False,
    },
    {
        "id": "hast_samudrika",
        "title": "Hast Samudrika Shastra (Indian Science of Hand Reading)",
        "discipline": "palmistry",
        "url": "https://archive.org/stream/in.ernet.dli.2015.125592/2015.125592.Hast-Samudrika-Shastra_djvu.txt",
        "quick": True,
    },
    {
        "id": "upanishads_sbe15",
        "title": "The Principal Upanishads (Sacred Books of the East Vol. 15)",
        "discipline": "vedas_upanishads",
        "url": "https://sacred-texts.com/hin/sbe15/sbe15104.htm",
        "quick": True,
    },
    {
        "id": "upanishads_chandogya",
        "title": "Chandogya Upanishad (Sacred Books of the East Vol. 1)",
        "discipline": "vedas_upanishads",
        "url": "https://sacred-texts.com/hin/sbe01/sbe01017.htm",
        "quick": True,
    },
    {
        "id": "rigveda_cosmic_hymn",
        "title": "Rig-Veda Book 1 Hymn 164 (Cosmic Wheel of Time & Year)",
        "discipline": "vedas_upanishads",
        "url": "https://sacred-texts.com/hin/rigveda/rv01164.htm",
        "quick": True,
    },
    {
        "id": "rigveda_agni_hymn",
        "title": "Rig-Veda Book 1 Hymn 14 (Vedic Invocation)",
        "discipline": "vedas_upanishads",
        "url": "https://sacred-texts.com/hin/rigveda/rv01014.htm",
        "quick": False,
    },
]

KEYWORDS_BY_DISCIPLINE = {
    "jyotish": {
        "lagna", "ascendant", "rashi", "bhava", "house", "graha", "planet",
        "nakshatra", "dasha", "vimshottari", "yoga", "raja yoga", "dhana",
        "navamsa", "dasamsa", "gochara", "transit", "surya", "chandra",
        "mangala", "budha", "guru", "shukra", "shani", "rahu", "ketu",
        "exalted", "debilitated", "aspect", "lord", "kendra", "trikona",
    },
    "vedas_upanishads": {
        "brahman", "atman", "karma", "dharma", "veda", "upanishad", "rta",
        "surya", "agni", "soma", "indra", "prana", "mind", "wisdom", "truth",
        "self", "knowledge", "action", "duty", "peace", "mantra", "year",
    },
    "palmistry": {
        "palm", "hand", "line", "mount", "finger", "thumb", "life line",
        "head line", "heart line", "fate line", "sun line", "mercury",
        "jupiter", "saturn", "apollo", "venus", "mars", "moon", "luna",
        "samudrika", "hasta", "sign", "cross", "star", "triangle", "phalanx",
    },
    "vedas_upanads": {
        "brahman", "atman", "karma", "dharma", "veda", "upanishad", "rta",
        "surya", "agni", "soma", "indra", "prana", "mind", "wisdom", "truth",
        "self", "knowledge", "action", "duty", "peace", "mantra", "year",
        "wheel", "twelve", "spokes", "immortal", "meditation", "discipline",
    },
}


def _fetch_url_bytes(url: str, headers: dict[str, str]) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
                return resp.read()
        raise


def clean_raw_page(raw_html: str) -> str:
    pre = re.search(r"<pre[^>]*>(.*?)</pre>", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = pre.group(1) if pre else raw_html
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html.unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def filter_passages(clean_text: str, source: dict, seen_hashes: set[str]) -> list[dict]:
    discipline = source["discipline"]
    vocab = KEYWORDS_BY_DISCIPLINE[discipline]
    blocks = [b.strip() for b in clean_text.split("\n\n") if 140 <= len(b.strip()) <= 2500]
    kept = []

    for idx, block in enumerate(blocks):
        lower = block.lower()
        if "internet archive" in lower or "sacred-texts.com" in lower or "buy books" in lower:
            continue
        hits = sorted([kw for kw in vocab if kw in lower])
        if len(hits) < 2:
            continue
        digest = hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        kept.append(
            {
                "id": f"{source['id']}_{idx:05d}",
                "discipline": discipline,
                "source_title": source["title"],
                "source_url": source["url"],
                "tags": hits[:10],
                "text": block,
            }
        )
    return kept


def run_harvest(quick_only: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "AstrobrainCorpusBuilder/1.0 (Classical Indian Knowledge Research)"}
    seen_hashes: set[str] = set()
    all_records: list[dict] = []
    counts_by_discipline: dict[str, int] = {}

    selected = [s for s in SOURCES if not quick_only or s["quick"]]
    print(f"Starting Astrobrain Scripture Harvester ({len(selected)} sources)...\n")

    for src in selected:
        print(f"-> Downloading: {src['title']}")
        try:
            raw = _fetch_url_bytes(src["url"], headers).decode("utf-8", errors="ignore")
        except Exception as exc:
            print(f"   [Warning] Could not reach {src['id']}: {exc}")
            continue

        cleaned = clean_raw_page(raw)
        records = filter_passages(cleaned, src, seen_hashes)
        all_records.extend(records)
        counts_by_discipline[src["discipline"]] = counts_by_discipline.get(src["discipline"], 0) + len(records)
        print(f"   [OK] Filtered & kept {len(records)} clean passages.")
        time.sleep(1.5)

    with CORPUS_FILE.open("w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    lines = [
        "# Astrobrain Classical Knowledge Base Summary",
        "",
        f"Total clean passages collected: **{len(all_records)}**",
        "",
        "| Discipline | Filtered Passages |",
        "| :--- | :--- |",
    ]
    for disc, cnt in sorted(counts_by_discipline.items()):
        lines.append(f"| {disc} | {cnt} |")
    SUMMARY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nDone! Saved {len(all_records)} passages to {CORPUS_FILE}")
    print(f"Summary written to {SUMMARY_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run a fast starter download")
    args = parser.parse_args()
    run_harvest(quick_only=args.quick)
