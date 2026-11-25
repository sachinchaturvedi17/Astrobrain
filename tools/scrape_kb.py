#!/usr/bin/env python3
"""AstroMuni knowledge harvester v1.0  ->  knowledge_base/web_corpus.jsonl  (+ knowledge_base/SOURCES.md)

Run this on YOUR machine (it needs internet). Standard library only.

    python3 tools/scrape_kb.py                  # all tiers in tools/scrape_sources.json
    python3 tools/scrape_kb.py --tier open      # only Wikipedia (CC BY-SA) pages
    python3 tools/scrape_kb.py --selftest       # offline check of the parsing/chunking, no network

Tiers (this is the licence policy, enforced in code):
  open        Wikipedia en/hi through the MediaWiki API. Full text is kept in ~110-word passages, licence "CC BY-SA 4.0",
              attribution is written to SOURCES.md. Wikipedia asks bots to identify themselves and go slowly: we do both.
  public      Public-domain / openly licensed texts you list by URL (archive.org full-text, Wikisource, sacred-texts...).
              Full text kept, licence is whatever you declare in the JSON (default "public-domain (declared)").
  restricted  Any other site. robots.txt is obeyed. We NEVER store the page text: only the title, URL, topic tags and a
              <=35-word factual snippet, so answers can link out to the source instead of copying it. Sites whose
              terms forbid scraping should simply not be listed.
Every record keeps source_url, licence, fetched date. Re-running replaces old records from the same URL.
This is retrieval data, not model training: the app retrieves passages and cites them.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base"
OUT = KB / "web_corpus.jsonl"
SRC_MD = KB / "SOURCES.md"
CONFIG = Path(__file__).with_name("scrape_sources.json")
UA = "AstroMuniHarvester/1.0 (open-source Vedic astrology app; https://github.com/sachinchaturvedi17/Astrobrain; polite, 1 req/s)"
DELAY = 1.3
SKIP_SECTIONS = {"references", "external links", "see also", "notes", "further reading", "bibliography", "citations", "sources", "footnotes",
                 "सन्दर्भ", "बाहरी कड़ियाँ", "इन्हें भी देखें", "टीका-टिप्पणी"}
TOPIC_WORDS = {
    "nakshatra": r"nakshatra|नक्षत्र", "graha": r"graha|planet|navagraha|ग्रह", "rashi": r"rashi|zodiac|राशि", "dasha": r"dasha|दशा",
    "yoga": r"yoga|योग", "panchang": r"panchang|tithi|karana|पंचांग|तिथि", "kundli": r"kundli|kundali|horoscope|birth chart|कुंडली|कुण्डली",
    "bhava": r"bhava|house|भाव", "muhurta": r"muhurta|मुहूर्त", "gochara": r"transit|gochar|गोचर", "remedy": r"remedy|upaya|उपाय",
    "career": r"career|profession|10th house|tenth house|karma bhava|dashamsa|livelihood|occupation|नौकरी|करियर|दशम भाव",
    "marriage": r"marriage|spouse|7th house|seventh house|kalatra|navamsa|vivaha|ashtakoota|विवाह|सप्तम भाव|जीवनसाथी",
    "love": r"romance|affection|5th house|fifth house|venus|shukra|attraction|love|प्रेम|पंचम भाव",
    "health": r"vitality|wellbeing|1st house|6th house|sixth house|constitution|tanu bhava|energy|स्वास्थ्य|लग्न भाव|षष्ठ भाव",
    "education": r"education|learning|study|vidya|4th house|5th house|9th house|budha|mercury|शिक्षा|विद्या|पढ़ाई",
    "wealth": r"wealth|prosperity|dhana|2nd house|11th house|second house|eleventh house|gains|income|धन|लाभ भाव|द्वितीय भाव",
}
_last = [0.0]


def fetch(url: str, accept: str = "*/*") -> bytes:
    wait = DELAY - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


# ------------------------------------------------------------------------------------------ text handling
def chunk(text: str, lo: int = 40, hi: int = 130) -> List[str]:
    """Group paragraphs into passages of roughly 40-130 words; never split mid-sentence when avoidable."""
    out, cur = [], []
    for para in re.split(r"\n{1,}", text):
        para = re.sub(r"\s+", " ", para).strip()
        if len(para.split()) < 6:
            continue
        for sent in re.split(r"(?<=[.!?।])\s+", para):
            cur.append(sent)
            if len(" ".join(cur).split()) >= hi:
                out.append(" ".join(cur))
                cur = []
        if len(" ".join(cur).split()) >= lo:
            out.append(" ".join(cur))
            cur = []
    if cur and len(" ".join(cur).split()) >= 25:
        out.append(" ".join(cur))
    return out


def tags_for(text: str, title: str) -> List[str]:
    blob = (title + " " + text).lower()
    return sorted(k for k, pat in TOPIC_WORDS.items() if re.search(pat, blob)) or ["jyotish"]


def drop_sections(extract: str) -> str:
    keep, skipping = [], False
    for ln in extract.splitlines():
        m = re.match(r"^=+\s*(.*?)\s*=+$", ln)
        if m:
            skipping = m.group(1).strip().lower() in SKIP_SECTIONS
            continue
        if not skipping:
            keep.append(ln)
    return "\n".join(keep)


class _Text(HTMLParser):
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "blockquote"}
    SKIP = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self.title, self._in_title, self._skip, self._buf, self.blocks = "", False, 0, [], []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self.BLOCK and self._buf:
            self.blocks.append(html.unescape(" ".join(self._buf)))
            self._buf = []

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip and data.strip():
            self._buf.append(data.strip())


def html_to_text(raw: str) -> Dict[str, str]:
    p = _Text()
    p.feed(raw)
    return {"title": re.sub(r"\s+", " ", p.title).strip(), "text": "\n".join(p.blocks)}


def snippet(text: str, words: int = 35) -> str:
    """The first on-topic sentence, cut to `words`. Deliberately short: a pointer, not a copy."""
    for sent in re.split(r"(?<=[.!?।])\s+", re.sub(r"\s+", " ", text)):
        if any(re.search(p, sent.lower()) for p in TOPIC_WORDS.values()) and len(sent.split()) >= 8:
            return " ".join(sent.split()[:words])
    return ""


def robots_ok(url: str) -> bool:
    u = urllib.parse.urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(f"{u.scheme}://{u.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return False                       # cannot prove permission -> do not fetch


def rec(pid: str, title: str, text: str, url: str, source: str, licence: str, tier: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = {"id": pid, "title": title, "text": text, "tags": tags_for(text, title), "source_title": source, "source_url": url,
         "licence": licence, "tier": "web", "harvest_tier": tier, "fetched": date.today().isoformat()}
    r.update(extra or {})
    return r


# ------------------------------------------------------------------------------------------ tiers
def harvest_open(cfg: Dict[str, Any], log) -> List[Dict[str, Any]]:
    out = []
    for lang, titles in cfg.get("wikipedia", {}).items():
        for t in titles:
            api = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&explaintext=1&exsectionformat=wiki"
                   f"&redirects=1&titles={urllib.parse.quote(t)}")
            try:
                data = json.loads(fetch(api, "application/json"))
                page = next(iter(data["query"]["pages"].values()))
            except Exception as e:
                log(f"  ! {lang}:{t} failed ({e})")
                continue
            if "missing" in page or not page.get("extract"):
                log(f"  - {lang}:{t} not found")
                continue
            url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(page['title'].replace(' ', '_'))}"
            ps = chunk(drop_sections(page["extract"]))
            for i, c in enumerate(ps):
                out.append(rec(f"wp_{lang}_{hashlib.sha1(url.encode()).hexdigest()[:8]}_{i:03d}", page["title"], c, url,
                               f"Wikipedia ({lang}): {page['title']}", "CC BY-SA 4.0", "open"))
            log(f"  + {lang}:{page['title']}  {len(ps)} passages")
    return out


def harvest_public(cfg: Dict[str, Any], log) -> List[Dict[str, Any]]:
    out = []
    for item in cfg.get("public", []):
        if "url" not in item:
            continue
        url, lic = item["url"], item.get("licence", "public-domain (declared)")
        try:
            raw = fetch(url).decode("utf-8", "ignore")
        except Exception as e:
            log(f"  ! {url} failed ({e})")
            continue
        doc = html_to_text(raw) if "<html" in raw[:2000].lower() else {"title": item.get("title", url), "text": raw}
        ps = [c for c in chunk(doc["text"]) if re.search("|".join(TOPIC_WORDS.values()), c.lower())]
        title = item.get("title") or doc["title"] or url
        for i, c in enumerate(ps[: item.get("max_passages", 400)]):
            out.append(rec(f"pd_{hashlib.sha1(url.encode()).hexdigest()[:8]}_{i:04d}", title, c, url, title, lic, "public"))
        log(f"  + {title}  {len(ps)} passages")
    return out


def harvest_restricted(cfg: Dict[str, Any], log) -> List[Dict[str, Any]]:
    out = []
    for item in cfg.get("restricted", []):
        if "url" not in item:
            continue
        url = item["url"]
        if not robots_ok(url):
            log(f"  - {url} skipped (robots.txt does not allow it, or could not be read)")
            continue
        try:
            doc = html_to_text(fetch(url, "text/html").decode("utf-8", "ignore"))
        except Exception as e:
            log(f"  ! {url} failed ({e})")
            continue
        s = snippet(doc["text"])
        if not s:
            log(f"  - {url} no on-topic snippet")
            continue
        out.append(rec(f"rx_{hashlib.sha1(url.encode()).hexdigest()[:10]}", item.get("title") or doc["title"] or url, s + " …", url,
                       item.get("title") or doc["title"] or url, "all rights reserved; snippet + link only", "restricted", {"snippet_only": True}))
        log(f"  + {url}  snippet stored (text not kept)")
    return out


def write_all(new: List[Dict[str, Any]], replace_urls: Iterable[str]) -> int:
    KB.mkdir(parents=True, exist_ok=True)
    keep: List[Dict[str, Any]] = []
    drop = set(replace_urls)
    if OUT.exists():
        for ln in OUT.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("source_url") not in drop:
                keep.append(r)
    allr = keep + new
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in allr) + ("\n" if allr else ""), encoding="utf-8")
    by: Dict[str, Dict[str, Any]] = {}
    for r in allr:
        by.setdefault(r["source_url"], {"t": r["source_title"], "l": r["licence"], "n": 0})["n"] += 1
    lines = ["# Knowledge base sources", "", "Generated by tools/scrape_kb.py. Wikipedia text is CC BY-SA 4.0 (attribution: Wikipedia contributors, see each page's history).", "",
             "| Source | Licence | Passages |", "|---|---|---|"]
    lines += [f"| [{v['t']}]({u}) | {v['l']} | {v['n']} |" for u, v in sorted(by.items())]
    SRC_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(allr)


# ------------------------------------------------------------------------------------------ self test
def selftest() -> int:
    page = "<html><head><title>Nakshatra guide</title></head><body><nav>menu</nav><p>The nakshatra is a lunar mansion of 13 degrees 20 minutes in Vedic astrology and there are twenty seven of them.</p><script>x=1</script><p>Each nakshatra has four padas and a ruling planet that sets the dasha sequence for the Moon placed there.</p></body></html>"
    d = html_to_text(page)
    assert d["title"] == "Nakshatra guide" and "menu" not in d["text"] and "x=1" not in d["text"], d
    s = snippet(d["text"])
    assert s and len(s.split()) <= 35, s
    ex = "Intro paragraph about the Moon and nakshatra that is long enough to keep as a passage of text here.\n== History ==\nMore text about how the nakshatra system developed over centuries in the Vedic period of India.\n== References ==\nShould not appear anywhere in output."
    ps = chunk(drop_sections(ex), lo=5)
    assert ps and not any("Should not appear" in p for p in ps), ps
    assert "nakshatra" in tags_for(ps[0], "x")
    assert chunk("short") == []
    print("selftest ok:", len(ps), "passage(s)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=["open", "public", "restricted", "all"], default="all")
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    log = lambda m: print(m, flush=True)
    new: List[Dict[str, Any]] = []
    for name, fn in (("open", harvest_open), ("public", harvest_public), ("restricted", harvest_restricted)):
        if a.tier in ("all", name):
            log(f"== {name} ==")
            new += fn(cfg, log)
    total = write_all(new, {r["source_url"] for r in new})
    log(f"done: {len(new)} new passages, {total} total in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
