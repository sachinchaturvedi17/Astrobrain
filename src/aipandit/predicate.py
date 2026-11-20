"""Machine-evaluable rule conditions over the Fact IR.

Evaluation is three-valued (Kleene logic): TRUE, FALSE, UNKNOWN.
A fact that was withheld (unknown birth time, unreadable palm line) makes an
atom UNKNOWN, never FALSE. An UNKNOWN rule cannot fire and cannot be used to
make a negative statement. This is how "refuse to guess" survives inside the
inference engine instead of only at intake.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from .fact_ir import FactStore


class PredicateError(Exception):
    pass


class Truth(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Match:
    truth: Truth
    fact_ids: tuple = ()        # populated only when truth is TRUE
    confidence: float = 1.0     # min confidence of the facts that made it TRUE

    @property
    def matched(self) -> bool:
        return self.truth is Truth.TRUE

    @property
    def undetermined(self) -> bool:
        return self.truth is Truth.UNKNOWN


def _unique(seq) -> tuple:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)


class Predicate:
    op: ClassVar[str] = ""

    def evaluate(self, store: FactStore) -> Match:  # pragma: no cover
        raise NotImplementedError

    def systems(self) -> frozenset:  # pragma: no cover
        raise NotImplementedError

    def to_dict(self) -> dict:  # pragma: no cover
        raise NotImplementedError

    def atoms(self):  # pragma: no cover
        """Yield every leaf atom (used to report which facts a rule is missing)."""
        raise NotImplementedError


@dataclass(frozen=True)
class _Atom(Predicate):
    system: str
    subject: str
    predicate: str

    def _test(self, value: Any) -> bool:  # pragma: no cover
        raise NotImplementedError

    def evaluate(self, store: FactStore) -> Match:
        fact = store.get(self.subject, self.predicate, system=self.system)
        if fact is None:
            return Match(Truth.UNKNOWN)
        ok = self._test(fact.value)
        if ok:
            return Match(Truth.TRUE, (fact.fact_id,), fact.confidence)
        return Match(Truth.FALSE)

    def systems(self) -> frozenset:
        return frozenset({self.system})

    def atoms(self):
        yield self

    def _base(self) -> dict:
        return {"op": self.op, "system": self.system,
                "subject": self.subject, "predicate": self.predicate}


def _need_number(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise PredicateError(f"numeric comparison against non-numeric fact value {v!r}")
    return v


@dataclass(frozen=True)
class Eq(_Atom):
    value: Any
    op: ClassVar[str] = "eq"

    def _test(self, value: Any) -> bool:
        return value == self.value

    def to_dict(self) -> dict:
        return {**self._base(), "value": self.value}


@dataclass(frozen=True)
class Gte(_Atom):
    value: float
    op: ClassVar[str] = "gte"

    def _test(self, value: Any) -> bool:
        return _need_number(value) >= self.value

    def to_dict(self) -> dict:
        return {**self._base(), "value": self.value}


@dataclass(frozen=True)
class Lte(_Atom):
    value: float
    op: ClassVar[str] = "lte"

    def _test(self, value: Any) -> bool:
        return _need_number(value) <= self.value

    def to_dict(self) -> dict:
        return {**self._base(), "value": self.value}


@dataclass(frozen=True)
class In(_Atom):
    values: tuple
    op: ClassVar[str] = "in"

    def _test(self, value: Any) -> bool:
        return value in self.values

    def to_dict(self) -> dict:
        return {**self._base(), "values": list(self.values)}


@dataclass(frozen=True)
class Exists(_Atom):
    """True if the fact is present, False if absent (withheld facts count as absent)."""
    op: ClassVar[str] = "exists"

    def evaluate(self, store: FactStore) -> Match:
        fact = store.get(self.subject, self.predicate, system=self.system)
        if fact is None:
            return Match(Truth.FALSE)
        return Match(Truth.TRUE, (fact.fact_id,), fact.confidence)

    def to_dict(self) -> dict:
        return self._base()


@dataclass(frozen=True)
class And(Predicate):
    args: tuple
    op: ClassVar[str] = "and"

    def __post_init__(self) -> None:
        if not self.args:
            raise PredicateError("And() needs at least one argument")

    def evaluate(self, store: FactStore) -> Match:
        results = [a.evaluate(store) for a in self.args]
        if any(r.truth is Truth.FALSE for r in results):
            return Match(Truth.FALSE)
        if any(r.truth is Truth.UNKNOWN for r in results):
            return Match(Truth.UNKNOWN)
        return Match(Truth.TRUE,
                     _unique(i for r in results for i in r.fact_ids),
                     min(r.confidence for r in results))

    def systems(self) -> frozenset:
        return frozenset().union(*(a.systems() for a in self.args))

    def atoms(self):
        for a in self.args:
            yield from a.atoms()

    def to_dict(self) -> dict:
        return {"op": self.op, "args": [a.to_dict() for a in self.args]}


@dataclass(frozen=True)
class Or(Predicate):
    args: tuple
    op: ClassVar[str] = "or"

    def __post_init__(self) -> None:
        if not self.args:
            raise PredicateError("Or() needs at least one argument")

    def evaluate(self, store: FactStore) -> Match:
        results = [a.evaluate(store) for a in self.args]
        true = [r for r in results if r.truth is Truth.TRUE]
        if true:
            return Match(Truth.TRUE,
                         _unique(i for r in true for i in r.fact_ids),
                         max(r.confidence for r in true))
        if any(r.truth is Truth.UNKNOWN for r in results):
            return Match(Truth.UNKNOWN)
        return Match(Truth.FALSE)

    def systems(self) -> frozenset:
        return frozenset().union(*(a.systems() for a in self.args))

    def atoms(self):
        for a in self.args:
            yield from a.atoms()

    def to_dict(self) -> dict:
        return {"op": self.op, "args": [a.to_dict() for a in self.args]}


@dataclass(frozen=True)
class Not(Predicate):
    arg: Predicate
    op: ClassVar[str] = "not"

    def evaluate(self, store: FactStore) -> Match:
        r = self.arg.evaluate(store)
        if r.truth is Truth.UNKNOWN:
            return Match(Truth.UNKNOWN)       # no closed-world assumption
        if r.truth is Truth.TRUE:
            return Match(Truth.FALSE)
        # FALSE -> TRUE, but there are no matched facts to cite for an absence.
        return Match(Truth.TRUE, (), 1.0)

    def systems(self) -> frozenset:
        return self.arg.systems()

    def atoms(self):
        yield from self.arg.atoms()

    def to_dict(self) -> dict:
        return {"op": self.op, "arg": self.arg.to_dict()}


def all_of(*args: Predicate) -> And:
    return And(tuple(args))


def any_of(*args: Predicate) -> Or:
    return Or(tuple(args))


_ATOMS = {c.op: c for c in (Eq, Gte, Lte, In, Exists)}


def from_dict(d: dict) -> Predicate:
    op = d.get("op")
    if op in _ATOMS:
        base = dict(system=d["system"], subject=d["subject"], predicate=d["predicate"])
        if op == "in":
            return In(**base, values=tuple(d["values"]))
        if op == "exists":
            return Exists(**base)
        return _ATOMS[op](**base, value=d["value"])
    if op == "and":
        return And(tuple(from_dict(a) for a in d["args"]))
    if op == "or":
        return Or(tuple(from_dict(a) for a in d["args"]))
    if op == "not":
        return Not(from_dict(d["arg"]))
    raise PredicateError(f"unknown predicate op: {op!r}")
