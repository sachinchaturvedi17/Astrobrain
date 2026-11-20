"""Intake & Resolver (Module 1): turn raw birth input into a validated, resolved birth.

Principles: never trust a city string, never guess, refuse with alternatives.
Timezone offsets come from the IANA tz database for the *birth date* (so India's
1942-45 war-time offset or a US DST change is applied correctly). Coordinates are
supplied by the caller (geocoding is a separate service).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIME_CERTAINTIES = ("exact", "approx_15min", "part_of_day", "unknown")
# +/- minutes around the nominal birth time within which a fact must stay
# unchanged to be asserted.
WINDOW_MINUTES = {"exact": 0, "approx_15min": 15, "part_of_day": 360, "unknown": 720}

J2000_JD = 2451545.0
GREGORIAN_START = date(1582, 10, 15)


class IntakeRefusal(Exception):
    """Inputs are insufficient or inconsistent; compute nothing, offer alternatives."""

    def __init__(self, reason: str, alternatives: tuple = ()) -> None:
        super().__init__(reason)
        self.reason = reason
        self.alternatives = alternatives


@dataclass(frozen=True)
class BirthInput:
    name: str
    date: str                      # "YYYY-MM-DD"
    time: Optional[str]            # "HH:MM[:SS]" local civil time, or None
    time_certainty: str
    place_name: str
    latitude: float
    longitude: float               # east positive
    tz_name: str                   # IANA zone in force at the birthplace, e.g. "Asia/Kolkata"
    gender: str = "prefer_not_to_say"        # male | female | other | prefer_not_to_say
    gender_rule_mode: str = "neutral"        # binary | neutral
    partnership_type: Optional[str] = None
    consent_store_birth_data: bool = False
    subject_is_minor: Optional[bool] = None
    guardian_consent: bool = False           # verifiable parental/guardian consent (DPDP)


@dataclass(frozen=True)
class ResolvedBirth:
    local_nominal: str
    tz_name: str
    utc: datetime
    utc_offset_hours: float
    jd_ut: float
    window_minutes: int
    time_certainty: str
    latitude: float
    longitude: float
    dst_ambiguous: bool
    warnings: tuple
    storage_allowed: bool


def julian_day_ut(dt_utc: datetime) -> float:
    """Julian Day of a UTC datetime (proleptic Gregorian, Meeus ch.7).

    UTC is used as UT1; the difference is < 0.9 s (about 0.0004 deg for the Moon,
    ~0.2 arcsec for the ascendant), well inside the engine's accuracy.
    """
    dt = dt_utc.astimezone(timezone.utc)
    y, m = dt.year, dt.month
    day = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600 + dt.microsecond / 3.6e9) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day + b - 1524.5


def jd_to_utc(jd: float) -> datetime:
    return datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=jd - J2000_JD)


def _parse_time(s: str):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise IntakeRefusal(f"time {s!r} is not HH:MM or HH:MM:SS")


def resolve_birth(b: BirthInput, today: Optional[date] = None) -> ResolvedBirth:
    today = today or date.today()
    warnings: list[str] = []

    if b.time_certainty not in TIME_CERTAINTIES:
        raise IntakeRefusal(f"time_certainty must be one of {TIME_CERTAINTIES}")
    if not (-90.0 <= b.latitude <= 90.0 and -180.0 <= b.longitude <= 180.0):
        raise IntakeRefusal("latitude/longitude out of range",
                            ("Re-enter the birthplace; coordinates must be degrees, east positive",))
    if b.latitude == 0.0 and b.longitude == 0.0:
        raise IntakeRefusal("coordinates are exactly 0,0 - almost always a failed geocode",
                            ("Pick the birthplace again from the place search",))

    try:
        d = datetime.strptime(b.date, "%Y-%m-%d").date()
    except ValueError:
        raise IntakeRefusal(f"date {b.date!r} is not YYYY-MM-DD")
    if d > today:
        raise IntakeRefusal("birth date is in the future")
    if d < GREGORIAN_START:
        raise IntakeRefusal("dates before 1582-10-15 need Julian-calendar handling (not supported)")

    try:
        tz = ZoneInfo(b.tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise IntakeRefusal(f"unknown timezone {b.tz_name!r}",
                            ("Use an IANA zone name such as Asia/Kolkata",))

    if b.time_certainty == "unknown":
        t = datetime.strptime("12:00", "%H:%M").time()      # nominal; ignored for lagna facts
    elif b.time is None:
        raise IntakeRefusal(
            f"time_certainty is {b.time_certainty!r} but no time was given",
            ("Give a best-estimate time, or set time_certainty to 'unknown'",),
        )
    else:
        t = _parse_time(b.time)

    naive = datetime.combine(d, t)
    first = naive.replace(tzinfo=tz, fold=0)
    second = naive.replace(tzinfo=tz, fold=1)
    roundtrip = first.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
    if roundtrip != naive:
        raise IntakeRefusal(
            f"{naive.isoformat()} does not exist in {b.tz_name} (clock jumped forward)",
            ("Check the birth record: the real time is before or after the skipped hour",),
        )
    ambiguous = first.utcoffset() != second.utcoffset()
    if ambiguous:
        warnings.append(
            "local time occurred twice (clocks went back); the earlier occurrence was used - "
            "ask which one the birth record means"
        )
        if b.time_certainty == "exact":
            raise IntakeRefusal(
                f"{naive.isoformat()} is ambiguous in {b.tz_name} (DST overlap)",
                ("Confirm whether the birth was before or after the clocks went back",),
            )

    offset_h = first.utcoffset().total_seconds() / 3600.0
    utc = first.astimezone(timezone.utc)
    if d.year < 1970:
        warnings.append("pre-1970 offsets come from tzdata on a best-effort basis; verify against the birth record")
    if abs(offset_h - b.longitude / 15.0) > 3.5:
        warnings.append(f"UTC offset {offset_h:+.2f}h is far from the longitude's solar offset; check tz_name")

    minor = b.subject_is_minor
    if minor is None:
        warnings.append("age group not declared; assume guardian consent may be required before storing data")
    storage_allowed = bool(b.consent_store_birth_data and (minor is False or b.guardian_consent))

    return ResolvedBirth(
        local_nominal=naive.isoformat(),
        tz_name=b.tz_name,
        utc=utc,
        utc_offset_hours=offset_h,
        jd_ut=julian_day_ut(utc),
        window_minutes=WINDOW_MINUTES[b.time_certainty],
        time_certainty=b.time_certainty,
        latitude=b.latitude,
        longitude=b.longitude,
        dst_ambiguous=ambiguous,
        warnings=tuple(warnings),
        storage_allowed=storage_allowed,
    )


def birth_hash(rb: ResolvedBirth, *, ayanamsa: str, node_mode: str,
               house_system: str, engine_id: str) -> str:
    """Cache key for a computed chart. Excludes name; still personal data under DPDP."""
    payload = {
        "utc": rb.utc.isoformat(timespec="seconds"),
        "lat": round(rb.latitude, 5),
        "lon": round(rb.longitude, 5),
        "time_certainty": rb.time_certainty,
        "ayanamsa": ayanamsa,
        "node_mode": node_mode,
        "house_system": house_system,
        "engine": engine_id,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()
