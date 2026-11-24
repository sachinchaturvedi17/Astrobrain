"""Expert case library (v1.1.3): real advice from experienced astrologers, kept as data the assistant can retrieve.

This is NOT model training. Cases are indexed for retrieval and, when a user's question closely matches a case, the
advice is shown alongside the chart-based answer, clearly attributed to a practising astrologer. Nothing here
changes the chart maths.

A case is one JSON object per line in expert_data/cases/*.jsonl (files starting with "_" are ignored):

  required: id, lang (en|hg|hi), topic, problem, advice, expert, consent (true)
  optional: situation, remedies (list or ";"-separated text), cautions, tags (list), added (YYYY-MM-DD)

Every case passes lint() before it is loaded. Errors keep a case out; warnings are reported but allowed.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
TOPICS_OK = {"career", "wealth", "marriage", "education", "children", "health", "family", "foreign", "property", "dasha",
             "remedy", "general", "manglik", "kaalsarp", "transit", "sade_sati", "concept"}
LANGS = {"en", "hg", "hi"}
REQUIRED = ("id", "lang", "topic", "problem", "advice", "expert", "consent")

# Hard stops: content we will not show to users, however experienced the source.
ERR = [
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "contains an email address"),
    (r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)", "contains a phone number"),
    (r"will die|death will|going to die|maut|mrityu ?yog|marne wale|मृत्यु|मौत|मर जा", "predicts death"),
    (r"guarantee|100 ?%|definitely will|pakka (hoga|milega)|zaroor (hoga|milega)|गारंटी|पक्का (होगा|मिलेगा)", "promises a guaranteed outcome"),
    (r"curse|shraap|doomed|barbad ho|ruin your|श्राप|बर्बाद हो", "uses fear or curses"),
    (r"₹ ?\d|rs\.? ?\d|rupees|\bfees?\b|dakshina of|pay (me|us|the)|payment|book (a )?(puja|pooja)", "mentions payment or booking a service"),
    (r"stop (taking )?(your )?(medicine|medication|treatment)|cure[sd]? (cancer|diabetes|tumou?r)|ilaj ho jayega|दवा बंद", "makes a medical claim"),
    (r"invest in|buy (shares|stocks|crypto|bitcoin|property now)|sell your (shares|stocks)", "gives investment instructions"),
]
WARN = [
    (r"(?i:\b(gem ?stone|ratna|ring|neelam|pukhraj|moonga|panna|manik)\b)|रत्न", "mentions a gemstone: say it only comes after a full chart check and a trial, never as a must-buy"),
    (r"(?i:\b(mr|mrs|ms|shri|smt|sri)\.?) [A-Z][a-z]+", "may contain a person's name: anonymise it"),
    (r"(?i:\b(must|has to|have to|compulsory|mandatory)\b)", "uses absolute wording: prefer 'often', 'tends to'"),
]


def _remedies(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").split(";") if x.strip()]


def lint(case: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors, warnings = [], []
    for f in REQUIRED:
        if case.get(f) in (None, "", []):
            errors.append(f"missing field: {f}")
    if errors:
        return errors, warnings
    if case["consent"] is not True:
        errors.append("consent must be true (the expert agreed to this being used)")
    if case["lang"] not in LANGS:
        errors.append("lang must be en, hg or hi")
    if case["topic"] not in TOPICS_OK:
        errors.append("topic must be one of: " + ", ".join(sorted(TOPICS_OK)))
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,60}", str(case["id"])):
        errors.append("id must be 3-60 letters, digits, _ . -")
    if len(str(case["advice"]).strip()) < 40:
        errors.append("advice is too short to help (40+ characters)")
    if len(str(case["problem"]).strip()) < 12:
        errors.append("problem is too short")
    blob = " ".join(str(case.get(k, "")) for k in ("problem", "situation", "advice", "cautions")) + " " + " ".join(_remedies(case.get("remedies")))
    for pat, why in ERR:
        if re.search(pat, blob, re.I):
            errors.append(why)
    for pat, why in WARN:
        if re.search(pat, blob):
            warnings.append(why)
    return errors, warnings


def passage(case: Dict[str, Any]) -> Dict[str, Any]:
    rem = _remedies(case.get("remedies"))
    parts = []
    if case.get("situation"):
        parts.append("Situation: " + str(case["situation"]).strip())
    parts.append("Problem: " + str(case["problem"]).strip())
    parts.append("What an experienced astrologer advises: " + str(case["advice"]).strip())
    if rem:
        parts.append("Simple practices: " + "; ".join(rem))
    if case.get("cautions"):
        parts.append("Caution: " + str(case["cautions"]).strip())
    return {"id": "expert_" + str(case["id"]), "title": str(case["problem"]).strip()[:90], "topic": case["topic"],
            "tags": list(case.get("tags") or []) + [case["topic"], case["lang"]], "text": "\n".join(parts), "tier": "expert",
            "source_title": "Practising astrologer on the NaradVani panel (" + str(case["expert"]).strip() + ")",
            "source_url": "", "licence": "contributed with the expert's consent", "confidence": "practitioner", "lang": case["lang"]}


def case_dir() -> Path:
    return Path(os.environ.get("ASTRONARAD_EXPERT_DIR") or ROOT / "expert_data" / "cases")


_CACHE: Dict[str, Any] = {}


def load_cases(d: Optional[Path] = None, force: bool = False) -> Dict[str, Dict[str, Any]]:
    d = Path(d) if d else case_dir()
    key = str(d)
    if key in _CACHE and not force:
        return _CACHE[key]["cases"]
    cases: Dict[str, Dict[str, Any]] = {}
    report: List[str] = []
    if d.exists():
        for f in sorted(d.glob("*.jsonl")):
            if f.name.startswith("_"):
                continue
            for n, ln in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if not ln.strip():
                    continue
                try:
                    c = json.loads(ln)
                except json.JSONDecodeError:
                    report.append(f"{f.name}:{n} not valid JSON")
                    continue
                errs, warns = lint(c)
                if errs:
                    report.append(f"{f.name}:{n} skipped: " + "; ".join(errs))
                    continue
                if c["id"] in cases:
                    report.append(f"{f.name}:{n} skipped: duplicate id {c['id']}")
                    continue
                cases[c["id"]] = c
                report += [f"{f.name}:{n} note: {w}" for w in warns]
    _CACHE[key] = {"cases": cases, "report": report}
    return cases


def last_report(d: Optional[Path] = None) -> List[str]:
    load_cases(d)
    return _CACHE[str(Path(d) if d else case_dir())]["report"]


def passages(d: Optional[Path] = None) -> Iterable[Dict[str, Any]]:
    for c in load_cases(d).values():
        yield passage(c)


def get(passage_id: str) -> Optional[Dict[str, Any]]:
    return load_cases().get(str(passage_id).replace("expert_", "", 1))
