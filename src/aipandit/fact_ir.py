"""Fact IR: the canonical, append-only memory of computed observations.

Stores observations, never interpretations. One fact per (system, subject,
predicate): the same chart can hold a Parashari Saturn house and a Lal Kitab
Saturn house side by side without them ever blending.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class FactConflict(Exception):
    """A different value was written for an existing fact id (facts are immutable)."""


class StoreFrozen(Exception):
    """The store was frozen (chart complete); no further writes."""


class AmbiguousFact(Exception):
    """subject/predicate exists in several systems and no system was given."""


@dataclass(frozen=True)
class Fact:
    subject: str          # "Saturn" | "lagna" | "heart_line"
    predicate: str        # "house" | "sign" | "nakshatra" | "curvature"
    value: Any
    system: str           # "parashari" | "lal_kitab" | "palm" | "session"
    confidence: float     # 1.0 = computed deterministically
    derivation: str       # e.g. "vedaksha:10.2.0:IndianOfficial|whole_sign|stable+-15min"
    timestamp: str = field(default_factory=_now, compare=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")

    @property
    def fact_id(self) -> str:
        return f"{self.system}:{self.subject}:{self.predicate}"

    def to_dict(self) -> dict:
        return {
            "fact_id": self.fact_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "value": self.value,
            "system": self.system,
            "confidence": self.confidence,
            "derivation": self.derivation,
            "timestamp": self.timestamp,
        }


class FactStore:
    def __init__(self, birth_hash: Optional[str] = None, version: int = 1) -> None:
        self._facts: dict[str, Fact] = {}
        self.birth_hash = birth_hash
        self.version = version      # bumped on birth-time rectification (new store)
        self._frozen = False

    def add(self, fact: Fact) -> Fact:
        if self._frozen:
            raise StoreFrozen(fact.fact_id)
        existing = self._facts.get(fact.fact_id)
        if existing is not None:
            if existing.value == fact.value and existing.confidence == fact.confidence:
                return existing
            raise FactConflict(
                f"{fact.fact_id}: {existing.value!r} already stored, refusing {fact.value!r}"
            )
        self._facts[fact.fact_id] = fact
        return fact

    def freeze(self) -> "FactStore":
        self._frozen = True
        return self

    def get(self, subject: str, predicate: str, system: Optional[str] = None) -> Optional[Fact]:
        if system is not None:
            return self._facts.get(f"{system}:{subject}:{predicate}")
        hits = [f for f in self._facts.values()
                if f.subject == subject and f.predicate == predicate]
        if len(hits) > 1:
            raise AmbiguousFact(f"{subject}.{predicate} exists in {[h.system for h in hits]}")
        return hits[0] if hits else None

    def value(self, subject: str, predicate: str, system: Optional[str] = None, default: Any = None) -> Any:
        f = self.get(subject, predicate, system)
        return f.value if f is not None else default

    def __iter__(self) -> Iterator[Fact]:
        return iter(self._facts.values())

    def __len__(self) -> int:
        return len(self._facts)

    def __contains__(self, fact_id: str) -> bool:
        return fact_id in self._facts

    def to_dicts(self) -> list[dict]:
        return [f.to_dict() for f in self._facts.values()]
