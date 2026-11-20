"""Rule schema with provenance, enforced at construction time.

Schema-level guarantees (so a bad rule cannot even be loaded):
  * A Parashari / Lal Kitab / palm rule may only read facts from its own system
    (plus "session" config facts). Systems are never blended inside one rule.
  * Cross-system rules use system="concordance" and carry no interpretation
    text; they can only produce a labelled note.
  * Every rule names its source (text + chapter).
  * Lal Kitab rules must state translation_confidence explicitly.
  * A rule that carries a remedy must name the licence of its source text.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .predicate import Predicate, from_dict

BASE_SYSTEMS = ("parashari", "lal_kitab", "palm", "numerology", "gochara")
SYSTEMS = BASE_SYSTEMS + ("concordance",)
GENDER_SCOPES = ("male", "female", "neutral", "all")
PARTNERSHIP_SCOPES = ("heterosexual", "same_sex", "all")
LICENCE_UNSPECIFIED = "unspecified"
UNPINNED = "unpinned"

# How far a rule has been checked. Ordered: later statuses imply earlier ones.
REVIEW_STATUSES = ("draft", "definition_checked", "astrologer_audited")
#   draft               - written, tested for reachability/frequency; source not pinned or not compared
#   definition_checked  - the defining conditions were compared against the named chapter of a named edition
#   astrologer_audited  - a practising astrologer signed off (none yet)
PROVENANCES = ("classical_text", "later_tradition", "synthesized", "unspecified")
#   classical_text   - the yoga/condition is defined in a pinned classical source
#   later_tradition  - widely used, but not pinned to a primary text here
#   synthesized      - interpretation derived from standard significations, not a verse
# Observed frequency bands over random charts; a rule's declared rarity must match (tests/test_base_rates.py)
RARITY_BANDS = {"common": (0.25, 1.0), "moderate": (0.05, 0.25),
                "uncommon": (0.01, 0.05), "rare": (0.0, 0.01)}


class RuleError(ValueError):
    pass


@dataclass(frozen=True)
class Source:
    text: str                       # e.g. "BPHS"
    chapter: str                    # e.g. "34"
    verse: Optional[str] = None
    translator: Optional[str] = None
    edition: Optional[str] = None
    licence: str = LICENCE_UNSPECIFIED   # licence of the text the wording derives from

    def __post_init__(self) -> None:
        if not self.text or not self.chapter:
            raise RuleError("source needs at least text and chapter")


@dataclass(frozen=True)
class Rule:
    rule_id: str
    system: str
    condition: Predicate
    scope: tuple
    interpretation: str
    source: Source
    gender_scope: str = "all"
    partnership_scope: str = "all"
    remedy: Optional[dict] = None
    translation_confidence: Optional[float] = None
    salience_hint: Optional[float] = None       # feeds Socket A
    review_status: str = "draft"
    provenance: str = "unspecified"
    adverse: bool = False        # interpretation is a cautionary/negative reading -> Safety gate framing
    rarity: Optional[str] = None  # declared frequency band; None = not declared
    notes: str = ""              # variants, assumptions, caveats for the astrologer auditing the rule

    def __post_init__(self) -> None:
        if not self.rule_id or " " in self.rule_id:
            raise RuleError(f"bad rule_id {self.rule_id!r}")
        if self.system not in SYSTEMS:
            raise RuleError(f"{self.rule_id}: unknown system {self.system!r}")
        if self.gender_scope not in GENDER_SCOPES:
            raise RuleError(f"{self.rule_id}: bad gender_scope {self.gender_scope!r}")
        if self.partnership_scope not in PARTNERSHIP_SCOPES:
            raise RuleError(f"{self.rule_id}: bad partnership_scope {self.partnership_scope!r}")
        if not self.scope:
            raise RuleError(f"{self.rule_id}: scope must name at least one life domain")

        used = set(self.condition.systems()) - {"session"}
        if self.system in BASE_SYSTEMS:
            foreign = used - {self.system}
            if foreign:
                raise RuleError(
                    f"{self.rule_id}: {self.system} rule reads facts from {sorted(foreign)}; "
                    "systems are never blended"
                )
            if not self.interpretation.strip():
                raise RuleError(f"{self.rule_id}: interpretation is empty")
        else:  # concordance
            if len(used) < 2:
                raise RuleError(f"{self.rule_id}: concordance rule must span two systems")
            if self.interpretation.strip() or self.remedy:
                raise RuleError(f"{self.rule_id}: concordance rules carry no interpretation or remedy")

        if self.system == "lal_kitab" and self.translation_confidence is None:
            raise RuleError(f"{self.rule_id}: lal_kitab rules need an explicit translation_confidence")
        if self.translation_confidence is not None and not 0.0 <= self.translation_confidence <= 1.0:
            raise RuleError(f"{self.rule_id}: translation_confidence out of range")
        if self.remedy and self.source.licence == LICENCE_UNSPECIFIED:
            raise RuleError(f"{self.rule_id}: remedy text requires a declared source licence")

        if self.review_status not in REVIEW_STATUSES:
            raise RuleError(f"{self.rule_id}: bad review_status {self.review_status!r}")
        if self.provenance not in PROVENANCES:
            raise RuleError(f"{self.rule_id}: bad provenance {self.provenance!r}")
        if self.rarity is not None and self.rarity not in RARITY_BANDS:
            raise RuleError(f"{self.rule_id}: bad rarity {self.rarity!r}")
        pinned = self.source.chapter != UNPINNED
        if self.provenance == "classical_text" and not pinned:
            raise RuleError(f"{self.rule_id}: a classical_text rule must pin its chapter")
        if self.review_status != "draft" and not (pinned and self.source.edition):
            raise RuleError(f"{self.rule_id}: {self.review_status} requires a pinned chapter and a named edition")

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "system": self.system,
            "condition": self.condition.to_dict(),
            "scope": list(self.scope),
            "gender_scope": self.gender_scope,
            "partnership_scope": self.partnership_scope,
            "interpretation": self.interpretation,
            "remedy": self.remedy,
            "source": self.source.__dict__.copy(),
            "translation_confidence": self.translation_confidence,
            "salience_hint": self.salience_hint,
            "review_status": self.review_status,
            "provenance": self.provenance,
            "adverse": self.adverse,
            "rarity": self.rarity,
            "notes": self.notes,
        }


def rule_from_dict(d: dict) -> Rule:
    return Rule(
        rule_id=d["rule_id"],
        system=d["system"],
        condition=from_dict(d["condition"]),
        scope=tuple(d["scope"]),
        interpretation=d.get("interpretation", ""),
        source=Source(**d["source"]),
        gender_scope=d.get("gender_scope", "all"),
        partnership_scope=d.get("partnership_scope", "all"),
        remedy=d.get("remedy"),
        translation_confidence=d.get("translation_confidence"),
        salience_hint=d.get("salience_hint"),
        review_status=d.get("review_status", "draft"),
        provenance=d.get("provenance", "unspecified"),
        adverse=d.get("adverse", False),
        rarity=d.get("rarity"),
        notes=d.get("notes", ""),
    )


def load_rules(path: str | Path) -> list[Rule]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = [rule_from_dict(d) for d in data]
    ids = [r.rule_id for r in rules]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise RuleError(f"duplicate rule ids: {sorted(dupes)}")
    return rules


def dump_rules(rules: list, path: str | Path) -> None:
    """Write rules as JSON for astrologer audit (the Python rule packs stay the source of truth)."""
    Path(path).write_text(json.dumps([r.to_dict() for r in rules], indent=2, ensure_ascii=False),
                          encoding="utf-8")
