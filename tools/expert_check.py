#!/usr/bin/env python3
"""Check, and optionally import, expert cases.

  python3 tools/expert_check.py                      # lint every file in expert_data/cases
  python3 tools/expert_check.py --import sheet.csv   # turn a spreadsheet export into expert_data/cases/<name>.jsonl

CSV columns: id,lang,topic,problem,advice,expert,consent,situation,remedies,cautions,tags
(remedies and tags separated by ";", consent = yes/true). Nothing is loaded into the app unless it passes the lint.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aipandit import expert  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="imp", help="CSV file to convert")
    ap.add_argument("--dir", help="cases directory (default expert_data/cases)")
    a = ap.parse_args()
    d = Path(a.dir) if a.dir else expert.case_dir()
    d.mkdir(parents=True, exist_ok=True)
    if a.imp:
        src = Path(a.imp)
        out = d / (src.stem + ".jsonl")
        n = 0
        with src.open(encoding="utf-8-sig", newline="") as fh, out.open("w", encoding="utf-8") as o:
            for row in csv.DictReader(fh):
                row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                row["consent"] = row.get("consent", "").lower() in ("yes", "y", "true", "1")
                row["remedies"] = [x.strip() for x in row.get("remedies", "").split(";") if x.strip()]
                row["tags"] = [x.strip() for x in row.get("tags", "").split(";") if x.strip()]
                o.write(json.dumps({k: v for k, v in row.items() if v not in ("", [])}, ensure_ascii=False) + "\n")
                n += 1
        print(f"wrote {n} rows to {out}")
    cases = expert.load_cases(d, force=True)
    rep = expert.last_report(d)
    print(f"{len(cases)} usable case(s) in {d}")
    for line in rep:
        print("  " + line)
    return 1 if any("skipped" in x or "not valid" in x for x in rep) else 0


if __name__ == "__main__":
    raise SystemExit(main())
