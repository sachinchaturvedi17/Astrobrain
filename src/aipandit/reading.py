"""The reading model: what the Pandit says, as statements that each point at their evidence.

A statement is one of:
  reading  - an interpretation; MUST cite rule ids that actually fired for this chart
  fact     - a computed observation (e.g. the running dasha); MUST cite fact ids present in the store
  framing  - connective text; MUST NOT mention any chart entity (planet, sign, house, yoga ...)
  caveat   - honesty / safety text; same restriction as framing
The gates (gates.py) enforce these rules mechanically on whatever a composer produces.
"""
from __future__ import annotations

from dataclasses import dataclass, field

KINDS = ("reading", "fact", "framing", "caveat")
LENSES = ("", "kundli", "numerology", "both")
LENS_LABEL = {"en": {"kundli": "Kundli", "numerology": "Numerology", "both": "Both lenses"},
              "hg": {"kundli": "Kundli", "numerology": "Numerology", "both": "Dono nazariye"},
              "hi": {"kundli": "कुंडली", "numerology": "अंकशास्त्र", "both": "दोनों नज़रिए"}}
BASIS_WORD = {"en": "Basis", "hg": "Aadhaar", "hi": "आधार"}


@dataclass(frozen=True)
class Statement:
    text: str
    kind: str = "reading"
    rule_ids: tuple = ()
    fact_ids: tuple = ()
    basis: tuple = ()          # human-readable facts behind a reading (system-generated, never LLM-written)
    label: str = ""            # e.g. "provisional", "source-checked"
    lens: str = ""             # "kundli" | "numerology" | "both" (a statement never blends two systems; "both" = a system-made bridge note)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"bad statement kind {self.kind!r}")
        if self.lens not in LENSES:
            raise ValueError(f"bad statement lens {self.lens!r}")


@dataclass
class Reading:
    statements: list = field(default_factory=list)
    composer: str = ""          # which composer actually produced the wording: "template" or "llm"

    def of_kind(self, kind: str) -> list:
        return [s for s in self.statements if s.kind == kind]

    def cited_rule_ids(self) -> set:
        return {r for s in self.statements for r in s.rule_ids}


def render(reading: Reading, lang: str = "en") -> str:
    """Plain-text/markdown rendering of a verified reading. Lens tags appear only when more than one lens is present."""
    lang = lang if lang in LENS_LABEL else "en"
    tag_lens = len({s.lens for s in reading.statements if s.lens}) > 1
    out: list[str] = []
    for s in reading.statements:
        if s.kind == "framing":
            out.append(s.text)
        elif s.kind in ("reading", "fact"):
            tag = f" _({s.label})_" if s.label else ""
            lens = f"**{LENS_LABEL[lang][s.lens]}:** " if tag_lens and s.lens else ""
            line = f"- {lens}{s.text}{tag}"
            if s.basis:
                line += f"\n  {BASIS_WORD[lang]}: " + "; ".join(s.basis) + ("।" if lang == "hi" else ".")
            out.append(line)
        else:
            out.append(f"_{s.text}_")
    return "\n\n".join(p if not p.startswith("- ") else p for p in _join_bullets(out))


def _join_bullets(parts: list[str]) -> list[str]:
    """Keep consecutive bullets together, separate other paragraphs with blank lines."""
    merged: list[str] = []
    for p in parts:
        if p.startswith("- ") and merged and merged[-1].startswith("- "):
            merged[-1] += "\n" + p
        else:
            merged.append(p)
    return merged
