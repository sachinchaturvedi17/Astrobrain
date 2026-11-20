"""Summarise tester feedback. Usage: python tools/feedback_summary.py [aipandit-feedback/feedback.jsonl]
Prints thumbs per language / lens / composer, the rules behind thumbs-down answers, and every written comment."""
import json
import sys
from collections import Counter, defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "aipandit-feedback/feedback.jsonl"
recs = [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
ans = [r for r in recs if r["kind"] == "answer"]
print(f"{len(recs)} records from {len({r['tester'] for r in recs})} tester(s); {len(ans)} rated answers")
for key in ("lang", "composer"):
    c = defaultdict(Counter)
    for r in ans:
        c[r.get(key)][r["rating"]] += 1
    print(f"\nby {key}:", {k: dict(v) for k, v in c.items()})
lens = defaultdict(Counter)
for r in ans:
    for l in (r.get("lenses") or ["none"]):
        lens[l][r["rating"]] += 1
print("\nby lens:", {k: dict(v) for k, v in lens.items()})
bad = Counter(rid for r in ans if r["rating"] == "down" for rid in r.get("rule_ids", []))
good = Counter(rid for r in ans if r["rating"] == "up" for rid in r.get("rule_ids", []))
print("\nrules in thumbs-down answers (down / up):")
for rid, n in bad.most_common(15):
    print(f"  {rid}: {n} / {good.get(rid, 0)}")
print("\nsession ratings:", [r["rating"] for r in recs if r["kind"] == "session" and r.get("rating")])
print("\ncomments:")
for r in recs:
    if r.get("comment"):
        q = f"  [Q: {r['question']}]" if r.get("question") else ""
        print(f"- ({r['kind']}, {r.get('lang', '-')}, {r.get('rating', '')}) {r['comment']}{q}")
