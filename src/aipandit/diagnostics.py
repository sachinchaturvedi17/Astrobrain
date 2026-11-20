"""Measurement tools for the rule base: sample random charts and report how often each
rule fires. Used by tests/test_base_rates.py and tools/base_rates.py.

A rule that fires for 60% of charts while claiming to be 'rare' is a bug in the rule or its
claim; this is how that gets caught before the Composer ever sees it.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from .derive import enrich
from .inference import infer
from .intake import BirthInput
from .kundli import generate_kundli
from .rules import RARITY_BANDS


def sample_births(n: int, seed: int = 20261120):
    rnd = random.Random(seed)
    start = datetime(1930, 1, 1, tzinfo=timezone.utc)
    span = int((datetime(2025, 12, 31, tzinfo=timezone.utc) - start).total_seconds())
    for i in range(n):
        t = start + timedelta(seconds=rnd.randrange(span))
        yield BirthInput(name=f"s{i}", date=t.strftime("%Y-%m-%d"), time=t.strftime("%H:%M"),
                         time_certainty="exact", place_name="synthetic",
                         latitude=rnd.uniform(-45, 60), longitude=rnd.uniform(-180, 180),
                         tz_name="UTC", subject_is_minor=False)


def measure(rules, n: int = 3000, seed: int = 20261120, engine=None):
    """Return {rule_id: dict(fired, determined, undetermined, rate)} over n random charts."""
    from .engines.vedaksha_engine import VedakshaEngine
    engine = engine or VedakshaEngine()
    stats = {r.rule_id: {"fired": 0, "determined": 0, "undetermined": 0} for r in rules}
    for b in sample_births(n, seed):
        store = enrich(generate_kundli(b, engine=engine))
        res = infer(store, rules)
        fired = res.fired_ids()
        undet = {u.rule_id for u in res.undetermined}
        for rid, s in stats.items():
            if rid in undet:
                s["undetermined"] += 1
            else:
                s["determined"] += 1
                s["fired"] += rid in fired
    for s in stats.values():
        s["rate"] = s["fired"] / s["determined"] if s["determined"] else float("nan")
    return stats


def band_violations(rules, stats, z: float = 3.0):
    """Rules whose observed rate is outside the declared band by more than z binomial sigmas."""
    bad = []
    for r in rules:
        s = stats[r.rule_id]
        lo, hi = RARITY_BANDS[r.rarity]
        p, n = s["rate"], s["determined"]
        sigma = math.sqrt(max(p * (1 - p), 1.0 / n) / n)
        if p < lo - z * sigma or p > hi + z * sigma:
            bad.append((r.rule_id, r.rarity, p, n))
    return bad
