"""Selection of what to say (the DEFAULT for Socket A, the evidence weigher).

This is a deterministic placeholder built only from metadata we hold: review status, provenance,
rarity and the cautionary flag. It is NOT astrologer-derived weighting - that needs real astrologers and
will replace `score` without touching anything else.

Why it exists: a chart fires 13 rules on average and 98% carry a cautionary one. Dumping them all
would tell nearly everyone they have both a Raja yoga and several afflictions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

STATUS_W = {"draft": 1.0, "definition_checked": 2.0, "astrologer_audited": 3.0}
PROV_W = {"classical_text": 1.0, "later_tradition": 0.5, "synthesized": 0.3, "unspecified": 0.0}
RARITY_W = {"rare": 1.0, "uncommon": 0.7, "moderate": 0.4, "common": 0.0, None: 0.0}

# When the winner fires, the weaker entailed rules add nothing and are dropped.
SUPERSEDES = {
    "parashari.yoga.kemadruma": ("parashari.yoga.kemadruma_common",),
    "parashari.yoga.durudhara": ("parashari.yoga.sunapha", "parashari.yoga.anapha"),
    "parashari.yoga.ubhayachari": ("parashari.yoga.vesi", "parashari.yoga.vosi"),
}

FREQUENCY_PHRASE = {
    "common": "This pattern is common (found in over a quarter of charts).",
    "moderate": "This pattern is found in roughly 5-25% of charts.",
    "uncommon": "This pattern is found in about 1-5% of charts.",
    "rare": "This pattern is found in under 1% of charts.",
}


@dataclass(frozen=True)
class SelectionPolicy:
    max_total: int = 6
    max_per_scope: int = 3
    max_adverse_overview: int = 1
    max_adverse_targeted: int = 2
    blocked_scopes: frozenset = frozenset({"health"})     # never surfaced as health claims
    minor_blocked_scopes: frozenset = frozenset({"marriage"})


@dataclass
class Selection:
    chosen: list = field(default_factory=list)
    suppressed: dict = field(default_factory=dict)       # rule_id -> reason
    uncovered_scopes: list = field(default_factory=list)  # asked about, but no rule covers it yet


def score(f) -> float:
    base = STATUS_W[f.review_status] + PROV_W.get(f.provenance, 0.0) + RARITY_W.get(f.rarity, 0.0)
    # Numerology rules all share the same metadata, so their own salience hint (Mulank > Bhagyank > name > year) orders them.
    return base + 0.1 * (f.salience_hint or 0.0) if f.system == "numerology" else base


def select(firings, scopes: frozenset = frozenset(), policy: SelectionPolicy = SelectionPolicy(),
           supported_scopes: frozenset = frozenset(), minor: bool = False) -> Selection:
    sel = Selection()
    fired_ids = {f.rule_id for f in firings}
    dominated = {weak for strong, weaks in SUPERSEDES.items() if strong in fired_ids for weak in weaks}
    targeted = bool(scopes)
    sel.uncovered_scopes = sorted(s for s in scopes if s not in supported_scopes)

    pool = []
    for f in firings:
        fs = set(f.scope)
        if fs <= policy.blocked_scopes:
            sel.suppressed[f.rule_id] = "blocked_scope"
        elif minor and (f.adverse or fs & policy.minor_blocked_scopes):
            sel.suppressed[f.rule_id] = "minor"
        elif f.rule_id in dominated:
            sel.suppressed[f.rule_id] = "superseded"
        elif targeted and not fs & scopes:
            sel.suppressed[f.rule_id] = "off_topic"
        else:
            pool.append(f)

    rank = lambda f: (-score(f), f.rule_id)
    positives = sorted((f for f in pool if not f.adverse), key=rank)
    cautions = sorted((f for f in pool if f.adverse), key=rank)
    cap_adv = policy.max_adverse_targeted if targeted else policy.max_adverse_overview
    adv = cautions[:cap_adv]
    for f in cautions[cap_adv:]:
        sel.suppressed[f.rule_id] = "adverse_cap"

    room = max(policy.max_total - len(adv), 0)
    per_scope: dict = {}
    pos = []
    for f in positives:
        key = f.scope[0]
        if len(pos) < room and per_scope.get(key, 0) < policy.max_per_scope:
            pos.append(f)
            per_scope[key] = per_scope.get(key, 0) + 1
        else:
            sel.suppressed[f.rule_id] = "cap"
    sel.chosen = pos + adv        # positives first; cautionary readings never lead
    return sel
