"""aipandit-kundli: generate a kundli's facts from the command line."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .intake import BirthInput, IntakeRefusal
from .jyotish import GRAHAS
from .kundli import KundliConfig, dasha_at, generate_kundli


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aipandit-kundli")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--time", help="HH:MM[:SS] local civil time")
    ap.add_argument("--certainty", default="exact",
                    choices=("exact", "approx_15min", "part_of_day", "unknown"))
    ap.add_argument("--place", default="")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True, help="east positive")
    ap.add_argument("--tz", required=True, help="IANA zone, e.g. Asia/Kolkata")
    ap.add_argument("--ayanamsa", default="lahiri")
    ap.add_argument("--node-mode", default="mean", choices=("mean", "true"))
    ap.add_argument("--json", action="store_true", help="print the full Fact IR as JSON")
    ap.add_argument("--yogas", action="store_true",
                    help="evaluate the Parashari rule base and list what fires, what cannot be decided, and why")
    ap.add_argument("--min-status", default="draft", choices=("draft", "definition_checked"),
                    help="with --yogas: only rules whose definition was checked against a source")
    a = ap.parse_args(argv)

    b = BirthInput(name="", date=a.date, time=a.time, time_certainty=a.certainty,
                   place_name=a.place, latitude=a.lat, longitude=a.lon, tz_name=a.tz)
    try:
        k = generate_kundli(b, KundliConfig(ayanamsa=a.ayanamsa, node_mode=a.node_mode))
    except IntakeRefusal as e:
        print(f"REFUSED: {e.reason}")
        for alt in e.alternatives:
            print(f"  - {alt}")
        return 2

    if a.json:
        print(json.dumps({
            "birth_hash": k.birth_hash,
            "facts": k.facts.to_dicts(),
            "withheld": [w.__dict__ for w in k.withheld],
            "warnings": k.warnings,
        }, indent=2, ensure_ascii=False))
        return 0

    f = k.facts
    lag = f.value("lagna", "sign", "parashari")
    print(f"Lagna: {lag if lag else 'withheld (needs exact birth time)'}")
    print(f"{'Graha':8s} {'Sign':11s} {'Nakshatra':18s} {'Pada':4s} {'House':5s} Retro")
    for g in GRAHAS:
        v = lambda p: f.value(g, p, "parashari", "-")
        print(f"{g:8s} {str(v('sign')):11s} {str(v('nakshatra')):18s} {str(v('pada')):4s} "
              f"{str(v('house')):5s} {v('retrograde')}")
    if k.dasha:
        now = datetime.now(timezone.utc)
        d = dasha_at(k, now)
        print(f"Dasha now: {d['maha']} / {d['antar']} (maha until {d['maha_end']}, antar until {d['antar_end']})")
    if k.withheld:
        print(f"\nWithheld ({len(k.withheld)}): " + ", ".join(sorted({f'{w.subject}.{w.predicate}' for w in k.withheld})[:12]) + " ...")
    for w in k.warnings:
        print(f"! {w}")
    if a.yogas:
        _print_yogas(k, a.min_status)
    return 0


def _print_yogas(k, min_status: str) -> None:
    from .derive import enrich
    from .inference import infer
    from .rulepacks import parashari_rules
    rules = parashari_rules()
    res = infer(enrich(k, as_of=datetime.now(timezone.utc) if k.dasha else None), rules, min_status=min_status)
    tag = {"draft": "draft", "definition_checked": "checked", "astrologer_audited": "audited"}
    print(f"\n== Parashari rules: {len(res.firings)} fire, {len(res.undetermined)} cannot be decided "
          f"(withheld facts), {res.not_fired} do not apply ==")
    print("Readings are traditional statements, not predictions. [checked] = defining conditions compared "
          "with a named source; [draft] = not yet.\n")
    primary: dict = {}
    for f in res.firings:                       # list each rule once, under its primary life area
        primary.setdefault(f.scope[0], []).append(f)
    for scope, items in sorted(primary.items()):
        print(f"{scope.upper()}")
        for f in items:
            flags = f"[{tag[f.review_status]}{', cautionary' if f.adverse else ''}]"
            print(f"  - {f.rule_id.replace('parashari.', '')} {flags}\n    {f.interpretation}")
    if res.undetermined:
        miss = sorted({m for u in res.undetermined for m in u.missing})
        print(f"\nCannot decide {len(res.undetermined)} rules; missing facts include: " + ", ".join(miss[:6])
              + (" ..." if len(miss) > 6 else ""))


if __name__ == "__main__":
    raise SystemExit(main())
