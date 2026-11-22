"""Sunrise / sunset and the day-segment timings of the Panchang (v1.0). Pure functions (NOAA solar position approximation,
within a few minutes at normal latitudes). Replaces the fixed 'Abhijit 11:52-12:38' and weekday table of Rahu Kaal.

Abhijit Muhurta = the 8th of 15 equal daytime muhurtas (sunrise + 7/15 of the day to sunrise + 8/15).
Rahu Kaal       = one of 8 equal daytime segments chosen by weekday: Sun 8, Mon 2, Tue 7, Wed 5, Thu 6, Fri 4, Sat 3.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Dict, Optional

RAHU_SEGMENT = {6: 8, 0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3}      # Python weekday(): Mon=0 ... Sun=6


def sun_times(d: date, lat: float, lon: float, tz_hours: float) -> Optional[Dict[str, float]]:
    """Local sunrise/sunset in minutes after local midnight, or None in polar day/night."""
    doy = d.timetuple().tm_yday
    g = 2 * math.pi / 365.0 * (doy - 1 + 0.0)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    c = (math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(dec))) - math.tan(la) * math.tan(dec)
    if not -1.0 <= c <= 1.0:
        return None
    ha = math.degrees(math.acos(c))
    rise_utc, set_utc = 720 - 4 * (lon + ha) - eq, 720 - 4 * (lon - ha) - eq
    return {"sunrise": rise_utc + tz_hours * 60, "sunset": set_utc + tz_hours * 60}


def _hm(minutes: float) -> str:
    m = int(round(minutes)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def day_timings(d: date, lat: float, lon: float, tz_hours: float) -> Optional[Dict[str, object]]:
    st = sun_times(d, lat, lon, tz_hours)
    if not st:
        return None
    rise, sset = st["sunrise"], st["sunset"]
    day = sset - rise
    seg = day / 8.0
    k = RAHU_SEGMENT[d.weekday()]
    rk0 = rise + seg * (k - 1)
    mu = day / 15.0
    return {"sunrise": _hm(rise), "sunset": _hm(sset), "abhijit": f"{_hm(rise + 7 * mu)} - {_hm(rise + 8 * mu)}",
            "rahu_kaal": f"{_hm(rk0)} - {_hm(rk0 + seg)}", "day_minutes": round(day)}
