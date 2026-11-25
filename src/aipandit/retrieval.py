"""Dependency-free retrieval over the AstroMuni knowledge base (v1.0).

Sources, in trust order:
  core   - curated own-words reference (kb_core)            always loaded
  web    - knowledge_base/web_corpus.jsonl from tools/scrape_kb.py  (open-licence full text, or snippet-only for
           restricted pages; every record keeps source_url + licence)
  shastra- knowledge_base/shastra_corpus.jsonl (older harvest of public-domain classical text; OCR-noisy)

Ranking is BM25 with: title/tag boosts, English/Hinglish/Hindi aliases (shaadi -> marriage, शनि -> saturn),
light stemming, a tier prior (core > web > shastra) and a noise penalty for OCR-garbled passages.
No network, no third-party packages. Returns hits that always carry `source_title`, `source_url`, `licence`.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .kb_core import core_passages

KB_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"
TIER_PRIOR = {"expert": 1.3, "core": 1.25, "web": 1.0, "shastra": 0.7}
STOP = frozenset("a an the of and or to in on for with is are was be it this that what when how why do does my me i you your "
                 "can will about from at by as if so not no yes please tell kya hai hain ka ki ke ko se mein me par aur".split())

# alias -> canonical token(s). Keys are lowercase; Devanagari handled by the same regex tokenizer.
ALIASES: Dict[str, str] = {
    "shaadi": "marriage", "vivah": "marriage", "shadi": "marriage", "wedding": "marriage", "spouse": "marriage",
    "partner": "marriage", "love": "marriage", "relationship": "marriage",
    "naukri": "career", "job": "career", "profession": "career", "business": "career", "work": "career",
    "paisa": "wealth", "dhan": "wealth", "money": "wealth", "finance": "wealth", "income": "wealth",
    "padhai": "education", "study": "education", "exam": "education", "vidya": "education",
    "bachche": "children", "santan": "children", "child": "children", "baby": "children",
    "sehat": "health", "swasthya": "health", "disease": "health",
    "shani": "saturn", "guru": "jupiter", "brihaspati": "jupiter", "mangal": "mars", "kuja": "mars", "budh": "mercury",
    "shukra": "venus", "surya": "sun", "chandra": "moon", "ravi": "sun", "som": "moon",
    "kundali": "kundli", "janampatri": "kundli", "chart": "kundli", "horoscope": "kundli", "rashifal": "horoscope",
    "gochar": "gochara", "transit": "gochara", "sadesati": "sade", "sati": "sade",
    "manglik": "mangal", "milan": "ashtakoota", "gun": "ashtakoota", "matching": "ashtakoota", "compatibility": "ashtakoota",
    "dosh": "dosha", "videsh": "abroad", "pardes": "abroad", "foreign": "abroad", "makaan": "property", "zameen": "property", "pitra": "pitru",
    "kalsarp": "kaal", "sarp": "kaal", "gemstone": "ratna", "pooja": "puja", "upay": "remedy", "upaya": "remedy", "totka": "remedy",
    "शनि": "saturn", "गुरु": "jupiter", "मंगल": "mars", "बुध": "mercury", "शुक्र": "venus", "सूर्य": "sun", "चंद्र": "moon",
    "चन्द्र": "moon", "विवाह": "marriage", "शादी": "marriage", "नौकरी": "career", "करियर": "career", "धन": "wealth",
    "पैसा": "wealth", "कुंडली": "kundli", "कुण्डली": "kundli", "दशा": "dasha", "महादशा": "dasha", "नक्षत्र": "nakshatra",
    "राशि": "rashi", "लग्न": "lagna", "पंचांग": "panchang", "गोचर": "gochara", "साढ़ेसाती": "sade", "उपाय": "remedy",
    "स्वास्थ्य": "health", "शिक्षा": "education", "संतान": "children",
}
_TOKEN = re.compile(r"[\wऀ-ॿ]+", re.UNICODE)


def _stem(w: str) -> str:
    for suf in ("ings", "ing", "edly", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> List[str]:
    out: List[str] = []
    for raw in _TOKEN.findall((text or "").lower()):
        w = ALIASES.get(raw, raw)
        w = ALIASES.get(w, w)
        if w in STOP or len(w) < 2:
            continue
        out.append(_stem(w))
    return out


def noise_ratio(text: str) -> float:
    """Share of 'words' that look like OCR garbage (digits mixed with letters, 1-letter runs, odd casing)."""
    words = text.split()
    if not words:
        return 1.0
    bad = sum(1 for w in words if (re.search(r"\d", w) and re.search(r"[A-Za-z]", w)) or re.search(r"[A-Za-z][A-Z]{2,}", w))
    return bad / len(words)


class Index:
    def __init__(self, docs: Iterable[Dict[str, Any]]):
        self.docs: List[Dict[str, Any]] = []
        self.tf: List[Counter] = []
        self.df: Counter = Counter()
        seen = set()
        for d in docs:
            text = (d.get("text") or "").strip()
            key = re.sub(r"\W+", " ", text.lower())[:160]
            if len(text) < 30 or key in seen:
                continue
            seen.add(key)
            d = dict(d)
            d.setdefault("tier", "shastra")
            d.setdefault("licence", "unspecified")
            d.setdefault("source_title", "Unknown source")
            d.setdefault("source_url", "")
            fields = Counter(tokenize(text))
            for t in tokenize(d.get("title", "") + " " + " ".join(map(str, d.get("tags", [])))):
                fields[t] += 3                      # title/tag boost
            self.docs.append(d)
            self.tf.append(fields)
            for t in fields:
                self.df[t] += 1
        self.n = len(self.docs)
        self.avgdl = (sum(sum(c.values()) for c in self.tf) / self.n) if self.n else 1.0

    def search(self, query: str, k: int = 4, tiers: Optional[Iterable[str]] = None,
               min_score: float = 1.2, exclude_topics: Iterable[str] = ()) -> List[Dict[str, Any]]:
        q = tokenize(query)
        if not q or not self.n:
            return []
        allowed = set(tiers) if tiers else None
        banned = set(exclude_topics)
        k1, b = 1.4, 0.72
        scored = []
        for i, (d, tf) in enumerate(zip(self.docs, self.tf)):
            if (allowed and d["tier"] not in allowed) or d.get("topic") in banned:
                continue
            dl = sum(tf.values()) or 1
            s = 0.0
            for t in set(q):
                f = tf.get(t, 0)
                if not f:
                    continue
                idf = math.log(1 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / self.avgdl))
            if s <= 0:
                continue
            s *= TIER_PRIOR.get(d["tier"], 0.8)
            if d["tier"] == "shastra":
                s *= max(0.2, 1.0 - 2.5 * noise_ratio(d["text"]))
            scored.append((s, i))
        scored.sort(reverse=True)
        hits = []
        for s, i in scored[:k]:
            if s < min_score:
                continue
            d = self.docs[i]
            hits.append({"id": d.get("id"), "title": d.get("title") or d["source_title"], "text": d["text"],
                         "score": round(s, 2), "tier": d["tier"], "source_title": d["source_title"],
                         "source_url": d["source_url"], "licence": d["licence"], "topic": d.get("topic", "")})
        return hits


def _read_jsonl(path: Path, tier: str) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        r.setdefault("tier", tier)
        yield r


_INDEX: Optional[Index] = None


def load_index(kb_dir: Optional[Path] = None, force: bool = False) -> Index:
    global _INDEX
    if _INDEX is not None and not force and kb_dir is None:
        return _INDEX
    base = Path(kb_dir) if kb_dir else KB_DIR
    docs: List[Dict[str, Any]] = list(core_passages())
    docs += list(_read_jsonl(base / "web_corpus.jsonl", "web"))
    docs += list(_read_jsonl(base / "training_6fields.jsonl", "web"))
    docs += list(_read_jsonl(base / "shastra_corpus.jsonl", "shastra"))
    if kb_dir is None:
        from . import expert
        docs += list(expert.passages())
    idx = Index(docs)
    if kb_dir is None:
        _INDEX = idx
    return idx


def search(query: str, k: int = 4, **kw: Any) -> List[Dict[str, Any]]:
    return load_index().search(query, k=k, **kw)
