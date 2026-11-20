"""aipandit-chat: talk to the Pandit in a terminal."""
from __future__ import annotations

import argparse

from .intake import BirthInput, IntakeRefusal
from .orchestrator import Pandit
from . import phrasebook as P


def build_llm():
    try:
        from .composer import AnthropicClient
        return AnthropicClient()
    except Exception:                       # no SDK / no key: the template composer still works
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aipandit-chat")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--time", help="HH:MM local civil time")
    ap.add_argument("--certainty", default="exact", choices=("exact", "approx_15min", "part_of_day", "unknown"))
    ap.add_argument("--place", default="")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--tz", required=True)
    ap.add_argument("--adult", action="store_true", help="confirm the person is 18 or over")
    ap.add_argument("--llm", action="store_true", help="use the LLM composer (needs `pip install .[llm]` and ANTHROPIC_API_KEY)")
    a = ap.parse_args(argv)
    if not a.adult:
        print("Please confirm the chart is for someone 18 or over with --adult (minors need guardian consent).")
        return 2
    b = BirthInput(name="", date=a.date, time=a.time, time_certainty=a.certainty, place_name=a.place,
                   latitude=a.lat, longitude=a.lon, tz_name=a.tz, subject_is_minor=False)
    llm = build_llm() if a.llm else None
    if a.llm and llm is None:
        print("(LLM composer unavailable; using the template composer.)")
    pandit = Pandit(llm=llm)
    try:
        sess = pandit.start(b)
    except IntakeRefusal as e:
        print(f"I cannot build this chart: {e.reason}")
        for alt in e.alternatives:
            print(f"  - {alt}")
        return 2
    print("AstroMuni (preview). Ask about your chart; blank line to quit.\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        print("\n" + pandit.ask(sess, q).text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
