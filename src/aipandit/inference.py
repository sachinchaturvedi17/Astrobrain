"""Rule evaluation with provenance and honest 'cannot tell' reporting.

Single pass over the rules. The plan calls this a forward-chaining engine; no
rule in the current base derives new facts from other rules (all derivation is
in derive.py), so chaining would be dead code. It will be added when a rule
needs it - not before.

For every rule the outcome is exactly one of:
  fired        condition TRUE   -> Firing (with the fact ids that made it true)
  undetermined condition UNKNOWN-> Undetermined (with the facts that are missing)
  not fired    condition FALSE  -> counted only; absence of a yoga is not reported
                                   as a finding
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .fact_ir import FactStore
from .predicate import Truth
from .rules import REVIEW_STATUSES, Rule, Source


@dataclass(frozen=True)
class Firing:
    rule_id: str
    system: str
    scope: tuple
    interpretation: str
    fact_ids: tuple           # the facts that made the condition true (provenance)
    confidence: float
    review_status: str
    provenance: str
    adverse: bool
    source: Source
    salience_hint: Optional[float] = None
    rarity: Optional[str] = None


@dataclass(frozen=True)
class Undetermined:
    rule_id: str
    missing: tuple            # fact ids the rule needs that were withheld/not derivable


@dataclass
class Inference:
    firings: list = field(default_factory=list)
    undetermined: list = field(default_factory=list)
    not_fired: int = 0
    out_of_scope: int = 0     # skipped for gender/partnership scope or review threshold

    def by_scope(self) -> dict:
        out: dict = {}
        for f in self.firings:
            for s in f.scope:
                out.setdefault(s, []).append(f)
        return out

    def fired_ids(self) -> set:
        return {f.rule_id for f in self.firings}


def infer(store: FactStore, rules, *, gender: Optional[str] = None,
          partnership: Optional[str] = None, min_status: str = "draft",
          systems: Optional[tuple] = None) -> Inference:
    """Evaluate `rules` over `store`.

    gender / partnership: if a rule is scoped (not "all"/"neutral") and the value
    is not supplied or does not match, the rule is skipped (counted in out_of_scope).
    min_status: skip rules reviewed less than this ("draft" < "definition_checked" < "astrologer_audited").
    systems: restrict to these systems (default: all). Systems are never merged here.
    """
    floor = REVIEW_STATUSES.index(min_status)
    res = Inference()
    for r in rules:
        if systems is not None and r.system not in systems:
            res.out_of_scope += 1
            continue
        if REVIEW_STATUSES.index(r.review_status) < floor:
            res.out_of_scope += 1
            continue
        if r.gender_scope not in ("all", "neutral") and r.gender_scope != gender:
            res.out_of_scope += 1
            continue
        if r.partnership_scope != "all" and r.partnership_scope != partnership:
            res.out_of_scope += 1
            continue

        m = r.condition.evaluate(store)
        if m.truth is Truth.TRUE:
            res.firings.append(Firing(
                rule_id=r.rule_id, system=r.system, scope=r.scope,
                interpretation=r.interpretation, fact_ids=m.fact_ids, confidence=m.confidence,
                review_status=r.review_status, provenance=r.provenance, adverse=r.adverse,
                source=r.source, salience_hint=r.salience_hint, rarity=r.rarity))
        elif m.truth is Truth.UNKNOWN:
            missing = tuple(dict.fromkeys(
                f"{a.system}:{a.subject}:{a.predicate}" for a in r.condition.atoms()
                if store.get(a.subject, a.predicate, system=a.system) is None))
            res.undetermined.append(Undetermined(r.rule_id, missing))
        else:
            res.not_fired += 1

    res.firings.sort(key=lambda f: (-(f.salience_hint or 0.0), f.rule_id))
    return res
