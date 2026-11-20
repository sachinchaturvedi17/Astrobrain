"""Export every rule (Parashari + numerology) as JSON for an astrologer / numerologist audit.
Usage: python tools/export_rules.py > docs/rules_all.json
Each entry has the English wording, the Hinglish wording, status, provenance, source and the auditor notes."""
import json

from aipandit.rulepacks import all_rules
from aipandit.rulepacks.hinglish import HINGLISH_ALL

out = []
for r in all_rules():
    out.append({"rule_id": r.rule_id, "system": r.system, "scope": list(r.scope), "adverse": r.adverse,
                "review_status": r.review_status, "provenance": r.provenance, "rarity": r.rarity,
                "interpretation_en": r.interpretation, "interpretation_hinglish": HINGLISH_ALL.get(r.rule_id),
                "condition": repr(r.condition), "source": str(r.source), "notes": r.notes})
print(json.dumps(out, ensure_ascii=False, indent=1))
