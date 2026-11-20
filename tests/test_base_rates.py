"""Measured firing frequency over random charts vs each rule's declared rarity band."""
import pytest

from aipandit.diagnostics import band_violations, measure
from chartkit import RULES
from test_witness import WITNESS

N = 3000


@pytest.fixture(scope="module")
def stats():
    return measure(RULES, N)


def test_no_rule_is_unreachable(stats):
    never = [r.rule_id for r in RULES if stats[r.rule_id]["fired"] == 0
             and r.rule_id.replace("parashari.", "") not in WITNESS]
    assert not never, f"never fired in {N} random charts and no witness chart: {never}"


def test_declared_rarity_matches_measured_frequency(stats):
    bad = band_violations(RULES, stats)
    assert not bad, "declared rarity disagrees with measurement:\n" + "\n".join(
        f"  {rid}: declared {rar}, observed {p*100:.1f}% over {n} charts" for rid, rar, p, n in bad)


def test_exact_time_charts_are_always_decidable(stats):
    # random samples all have exact times; only engine-precision boundary cases may be undetermined
    worst = max(s["undetermined"] for s in stats.values())
    assert worst / N < 0.01, worst
