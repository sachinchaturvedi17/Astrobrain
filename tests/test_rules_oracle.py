"""Independent re-implementation of selected rules from raw Swiss Ephemeris longitudes,
compared chart-by-chart with the production pipeline (derive.py + rulepack + inference).

The definitions here are deliberately written a different way (planet-centric loops, no shared
tables or helpers) so a shared bug cannot hide. Swiss Ephemeris is a dev-only oracle (AGPL)."""
import pytest

swe = pytest.importorskip("swisseph")

from aipandit.derive import enrich                           # noqa: E402
from aipandit.diagnostics import sample_births               # noqa: E402
from aipandit.inference import infer                         # noqa: E402
from aipandit.intake import julian_day_ut, resolve_birth     # noqa: E402
from aipandit.kundli import generate_kundli                  # noqa: E402
from chartkit import RULES                                   # noqa: E402

pytestmark = pytest.mark.oracle
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
IDS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
       "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN}
LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
FIVE = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
M, D = {1, 2, 4, 5, 7, 9, 10, 11}, {6, 8, 12}


def independent(lon, lag_lon):
    sg = {g: int(v // 30) % 12 for g, v in lon.items()}
    lag = int(lag_lon // 30) % 12
    hs = lambda g: (sg[g] - lag) % 12 + 1                              # house from Lagna
    hm = lambda g: (sg[g] - sg["Moon"]) % 12 + 1                       # from Moon
    hsun = lambda g: (sg[g] - sg["Sun"]) % 12 + 1
    owns = {g: {(i - lag) % 12 + 1 for i in range(12) if LORD[i] == g} for g in IDS}
    exch = [(a, b) for a in IDS for b in IDS if a < b and LORD[sg[b]] == a and LORD[sg[a]] == b]

    def planets_flank(h):
        return any(hm(g) == h for g in FIVE)
    out = {
        "yoga.sunapha": planets_flank(2),
        "yoga.anapha": planets_flank(12),
        "yoga.kemadruma_common": not any(hm(g) in (1, 2, 12) for g in FIVE),
        "yoga.kemadruma": not any(hm(g) in (1, 2, 12) for g in FIVE)
                          and not any(hs(g) in (1, 4, 7, 10) for g in FIVE + ["Moon"]),
        "yoga.vesi": any(hsun(g) == 2 for g in FIVE),
        "yoga.vosi": any(hsun(g) == 12 for g in FIVE),
        "yoga.gajakesari": hm("Jupiter") in (1, 4, 7, 10),
        "yoga.budhaditya": sg["Sun"] == sg["Mercury"],
        "yoga.malavya": hs("Venus") in (1, 4, 7, 10) and sg["Venus"] in (1, 6, 11),
        "yoga.hamsa": hs("Jupiter") in (1, 4, 7, 10) and sg["Jupiter"] in (8, 11, 3),
        "dosha.manglik_from_lagna": hs("Mars") in (1, 4, 7, 8, 12),
        "dosha.manglik_from_moon": hm("Mars") in (1, 4, 7, 8, 12),
        "parivartana.maha": any(owns[a] & M and owns[b] & M for a, b in exch),
        "parivartana.dainya": any((owns[a] & D and owns[b] & (M | {3})) or (owns[b] & D and owns[a] & (M | {3}))
                                  for a, b in exch),
        "parivartana.khala": any((3 in owns[a] and owns[b] & M) or (3 in owns[b] and owns[a] & M)
                                 for a, b in exch),
    }
    return out


def near_boundary(vals, arcsec=40.0):
    return any(min(v % 30.0, 30.0 - v % 30.0) * 3600.0 < arcsec for v in vals)


def test_rules_agree_with_independent_swisseph_implementation():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    compared = {}
    disagreements = []
    for b in sample_births(500, seed=99):
        rb = resolve_birth(b)
        jd = julian_day_ut(rb.utc)
        lon = {g: swe.calc_ut(jd, i, FLAGS)[0][0] for g, i in IDS.items()}
        _, asc = swe.houses_ex(jd, rb.latitude, rb.longitude, b"W", swe.FLG_SIDEREAL)
        if near_boundary(list(lon.values()) + [asc[0]]):
            continue                         # production withholds these by design
        store = enrich(generate_kundli(b))
        res = infer(store, RULES)
        fired, undet = res.fired_ids(), {u.rule_id for u in res.undetermined}
        for rid, expect in independent(lon, asc[0]).items():
            full = f"parashari.{rid}"
            if full in undet:
                continue
            compared[rid] = compared.get(rid, 0) + 1
            if (full in fired) != expect:
                disagreements.append((rid, b.date, b.time, expect))
    print({k: v for k, v in sorted(compared.items())})
    assert not disagreements, disagreements[:10]
    assert min(compared.values()) > 400
