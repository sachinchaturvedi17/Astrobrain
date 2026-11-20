"""Print the rule frequency table (markdown). Usage: python tools/base_rates.py [N]"""
import sys
from aipandit.diagnostics import band_violations, measure
from aipandit.rulepacks import parashari_rules

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
rules = parashari_rules()
stats = measure(rules, n)
bad = {b[0] for b in band_violations(rules, stats)}
print(f"| rule | status | declared | observed ({n} charts) | undetermined | band check |")
print("|---|---|---|---|---|---|")
for r in rules:
    s = stats[r.rule_id]
    print(f"| {r.rule_id} | {r.review_status} | {r.rarity} | {s['rate']*100:.1f}% | {s['undetermined']} | "
          f"{'MISMATCH' if r.rule_id in bad else 'ok'} |")
