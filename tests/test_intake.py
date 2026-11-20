from datetime import date, datetime, timezone

import pytest

from aipandit.intake import (BirthInput, IntakeRefusal, birth_hash, jd_to_utc,
                             julian_day_ut, resolve_birth)

TODAY = date(2026, 11, 20)


def mk(**kw):
    base = dict(name="t", date="1990-05-15", time="14:30", time_certainty="exact",
                place_name="Bhopal", latitude=23.2599, longitude=77.4126, tz_name="Asia/Kolkata")
    base.update(kw)
    return BirthInput(**base)


def test_julian_day_reference_values():
    assert julian_day_ut(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)) == 2451545.0   # J2000
    assert julian_day_ut(datetime(1987, 1, 27, 0, tzinfo=timezone.utc)) == 2446822.5   # Meeus ex. 7.a
    assert jd_to_utc(2451545.0) == datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


def test_ist_offset_and_utc():
    rb = resolve_birth(mk(), TODAY)
    assert rb.utc_offset_hours == 5.5
    assert rb.utc == datetime(1990, 5, 15, 9, 0, tzinfo=timezone.utc)
    assert rb.window_minutes == 0 and not rb.dst_ambiguous


def test_historical_offset_is_used_not_current_one():
    # tzdata records India's war-time clock; the offset must differ from today's +5:30
    rb = resolve_birth(mk(date="1943-06-15", time="12:00"), TODAY)
    assert rb.utc_offset_hours != 5.5
    assert any("pre-1970" in w for w in rb.warnings)


def test_dst_overlap_and_gap():
    amb = dict(tz_name="America/New_York", latitude=40.7, longitude=-74.0)
    with pytest.raises(IntakeRefusal, match="ambiguous"):
        resolve_birth(mk(date="2023-11-05", time="01:30", **amb), TODAY)
    rb = resolve_birth(mk(date="2023-11-05", time="01:30", time_certainty="approx_15min", **amb), TODAY)
    assert rb.dst_ambiguous and any("twice" in w for w in rb.warnings)
    with pytest.raises(IntakeRefusal, match="does not exist"):
        resolve_birth(mk(date="2023-03-12", time="02:30", **amb), TODAY)


@pytest.mark.parametrize("kw,msg", [
    (dict(latitude=95.0), "out of range"),
    (dict(latitude=0.0, longitude=0.0), "failed geocode"),
    (dict(tz_name="Mars/Olympus"), "unknown timezone"),
    (dict(date="2031-01-01"), "future"),
    (dict(date="1500-01-01"), "1582"),
    (dict(time=None), "no time was given"),
    (dict(time="25:99"), "not HH:MM"),
    (dict(time_certainty="sort_of"), "time_certainty"),
])
def test_refusals(kw, msg):
    with pytest.raises(IntakeRefusal, match=msg):
        resolve_birth(mk(**kw), TODAY)


def test_unknown_time_is_allowed_without_a_time():
    rb = resolve_birth(mk(time=None, time_certainty="unknown"), TODAY)
    assert rb.window_minutes == 720


def test_storage_requires_consent_and_guardian_for_minors():
    assert not resolve_birth(mk(), TODAY).storage_allowed
    assert resolve_birth(mk(consent_store_birth_data=True, subject_is_minor=False), TODAY).storage_allowed
    assert not resolve_birth(mk(consent_store_birth_data=True, subject_is_minor=True), TODAY).storage_allowed
    assert resolve_birth(mk(consent_store_birth_data=True, subject_is_minor=True,
                            guardian_consent=True), TODAY).storage_allowed


def test_birth_hash_is_stable_and_config_sensitive():
    rb = resolve_birth(mk(), TODAY)
    kw = dict(ayanamsa="lahiri", node_mode="mean", house_system="whole_sign", engine_id="e:1")
    assert birth_hash(rb, **kw) == birth_hash(rb, **kw)
    assert birth_hash(rb, **{**kw, "node_mode": "true"}) != birth_hash(rb, **kw)
    assert birth_hash(rb, **{**kw, "ayanamsa": "raman"}) != birth_hash(rb, **kw)
    rb2 = resolve_birth(mk(name="someone else"), TODAY)
    assert birth_hash(rb2, **kw) == birth_hash(rb, **kw)       # name is not part of the key
