"""Palmistry (Hastarekha / Samudrika Shastra) facts and traditional rules for Astrobrain.

Kept strictly as its own system ('palm') in FactStore so palm observations never
silently blend into Parashari kundli or numerology facts. Unclear or missing
palm observations are omitted so downstream rules evaluate to UNKNOWN rather than
guessing from blurry photos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .fact_ir import Fact, FactStore
from .predicate import Eq
from .rules import Rule, Source

SYS = "palm"
VERSION = "palm:v1"

PALM_SRC = Source(
    text="Hast Samudrika Shastra & Indian Palmistry Tradition",
    chapter="hastarekha_overview",
    edition="Traditional Indian palmistry synthesis (requires practitioner audit)",
    licence="unspecified",
)


@dataclass(frozen=True)
class PalmObservation:
    """Structured palm features for left/right hand (e.g. from practitioner or vision helper)."""

    active_hand: str = "right"          # "left" | "right"
    life_line: Optional[str] = None     # "long_clear" | "chained" | "short"
    head_line: Optional[str] = None     # "long_straight" | "sloping_creative" | "short"
    heart_line: Optional[str] = None    # "clear_balanced" | "chained" | "short"
    fate_line: Optional[str] = None     # "clear_deep" | "broken_shifting" | "faint"
    dominant_mount: Optional[str] = None  # "jupiter" | "apollo" | "mercury" | "saturn" | "venus" | "moon"


def enrich(store: FactStore, obs: Optional[PalmObservation]) -> FactStore:
    """Return a new frozen store = `store` + verified palm observations."""
    out = FactStore(birth_hash=store.birth_hash)
    for f in store:
        out.add(f)

    if obs is None:
        return out.freeze()

    def put(subject: str, predicate: str, value: object, why: str) -> None:
        if value is not None:
            out.add(Fact(subject, predicate, value, SYS, 0.85, f"{VERSION}|{why}"))

    put("palm", "active_hand", obs.active_hand, "selected hand")
    put("life_line", "pattern", obs.life_line, "observed life line")
    put("head_line", "pattern", obs.head_line, "observed head line")
    put("heart_line", "pattern", obs.heart_line, "observed heart line")
    put("fate_line", "pattern", obs.fate_line, "observed fate line")
    put("mount", "dominant", obs.dominant_mount, "observed prominent palm mount")
    return out.freeze()


def palm_rules() -> list[Rule]:
    """Starter Samudrika Shastra rules in English (non-fatalistic, tendency-based)."""
    raw = [
        (
            "palm.life_long_clear",
            Eq(SYS, "life_line", "pattern", "long_clear"),
            ("character",),
            "In Samudrika Shastra palmistry, a clear, well-marked life line is traditionally read as steady vitality and resilience; this is a traditional observation, not a lifespan or medical statement.",
        ),
        (
            "palm.head_sloping_creative",
            Eq(SYS, "head_line", "pattern", "sloping_creative"),
            ("mind", "career"),
            "In palmistry tradition, a gently sloping head line is associated with imaginative thinking, adaptability and creative problem-solving.",
        ),
        (
            "palm.head_long_straight",
            Eq(SYS, "head_line", "pattern", "long_straight"),
            ("mind", "career"),
            "In palmistry tradition, a long, straight head line is associated with practical logic, focus and structured decision-making.",
        ),
        (
            "palm.heart_clear_balanced",
            Eq(SYS, "heart_line", "pattern", "clear_balanced"),
            ("marriage", "character"),
            "In palmistry tradition, a clear, steady heart line is associated with warm, sincere emotional expression and value for trust in close bonds.",
        ),
        (
            "palm.fate_clear_deep",
            Eq(SYS, "fate_line", "pattern", "clear_deep"),
            ("career", "status"),
            "In palmistry tradition, a distinct fate line is associated with a strong sense of responsibility, self-direction and steady work focus.",
        ),
    ]
    return [
        Rule(
            rule_id=rid,
            system=SYS,
            condition=cond,
            scope=scope,
            interpretation=interp_en,
            source=PALM_SRC,
            review_status="draft",
            provenance="later_tradition",
            adverse=False,
            notes="Requires practitioner audit and Hinglish entry in rulepacks/hinglish.py.",
        )
        for rid, cond, scope, interp_en in raw
    ]
