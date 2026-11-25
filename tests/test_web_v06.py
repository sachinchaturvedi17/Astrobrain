"""v0.6: palm photos, /api/horoscope, /api/pandit-request, /api/resume."""
import base64
import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pytest

from aipandit.orchestrator import Pandit
from aipandit.web.server import make_server

BODY = {"name": "Sachin Chaturvedi", "date": "1990-05-15", "time": "14:30", "certainty": "exact", "place": "Bhopal",
        "lat": 23.2599, "lon": 77.4126, "tz": "Asia/Kolkata", "gender": "male", "consent": False}
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 2000).decode()


@pytest.fixture()
def srv(tmp_path):
    s = make_server(Pandit(now=lambda: datetime(2026, 11, 20, tzinfo=timezone.utc)), port=0, log_dir=str(tmp_path))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}", tmp_path
    s.shutdown()
    s.server_close()


def post(url, path, body, raw=None):
    data = raw if raw is not None else json.dumps(body).encode()
    req = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        finally:
            e.close()


def start(url, **kw):
    code, j = post(url, "/api/start", {**BODY, **kw})
    assert code == 200, j
    return j


def test_start_returns_profile_and_chart_extras(srv):
    u, _ = srv
    j = start(u, palms={"left": JPEG, "right": JPEG})
    assert j["profile"] == {"first_name": "Sachin", "full_name": "Sachin Chaturvedi", "has_palms": True, "minor": False}
    c = j["chart"]
    assert c["moon"]["sign"] and c["sun_sign"] and any(m["current"] for m in c["timeline"])
    assert start(u)["profile"]["has_palms"] is False


@pytest.mark.parametrize("palms", [
    {"left": JPEG},                                                       # one side missing
    {"left": JPEG, "right": "!!!not base64!!!"},
    {"left": JPEG, "right": base64.b64encode(b"GIF89a" + b"0" * 100).decode()},   # not a JPEG
    {"left": JPEG, "right": base64.b64encode(b"\xff\xd8\xff" + b"0" * (601 * 1024)).decode()},   # over the cap
])
def test_bad_palm_photos_are_refused(srv, palms):
    u, _ = srv
    code, j = post(u, "/api/start", {**BODY, "palms": palms})
    assert code == 400 and "palm" in j["error"]


def test_start_body_limit_is_larger_than_other_routes(srv):
    u, _ = srv
    assert post(u, "/api/start", {**BODY, "palms": {"left": JPEG, "right": JPEG}})[0] == 200
    assert post(u, "/api/chat", None, raw=b"x" * 9000)[0] == 413
    assert post(u, "/api/horoscope", None, raw=b"x" * 9000)[0] == 413


def test_horoscope_shape_and_honesty(srv):
    u, _ = srv
    sid = start(u)["session"]
    code, h = post(u, "/api/horoscope", {"session": sid, "lang": "en"})
    assert code == 200 and h["sections"]
    keys = [s["key"] for s in h["sections"]]
    assert "career" in keys and len(keys) == len(set(keys))
    for s in h["sections"]:
        assert s["answer_id"] and s["statements"] and all(st["kind"] in ("reading", "fact") for st in s["statements"])
    assert set(h["uncovered"]) <= {"education", "children", "family"}      # areas with no rules are listed, never invented
    assert not set(keys) & set(h["uncovered"])


def test_horoscope_for_a_minor_has_no_marriage_or_children(srv):
    u, _ = srv
    sid = start(u, date="2012-05-15", who="minor_with_guardian")["session"]
    code, h = post(u, "/api/horoscope", {"session": sid, "lang": "en"})
    assert code == 200
    assert not {"marriage", "children"} & {s["key"] for s in h["sections"]}


def test_horoscope_unknown_session_and_bad_lang(srv):
    u, _ = srv
    assert post(u, "/api/horoscope", {"session": "nope", "lang": "en"})[0] == 404
    sid = start(u)["session"]
    code, h = post(u, "/api/horoscope", {"session": sid, "lang": "hi"})
    assert code == 200 and h["lang_fallback"] in ("en", None, False, "")


def test_resume_returns_the_same_chart(srv):
    u, _ = srv
    j = start(u)
    code, r = post(u, "/api/resume", {"session": j["session"]})
    assert code == 200 and r["session"] == j["session"] and r["chart"]["lagna_sign"] == j["chart"]["lagna_sign"]
    assert post(u, "/api/resume", {"session": "nope"})[0] == 404


def _req(sid, **kw):
    return {"session": sid, "phone": "+91 98765-43210", "slot": "evening", "topic": "career", "note": "hello", "share_details": True, **kw}


def test_pandit_request_validation(srv):
    u, d = srv
    sid = start(u)["session"]
    assert post(u, "/api/pandit-request", _req(sid, phone="12345"))[0] == 400
    assert post(u, "/api/pandit-request", _req(sid, share_details=False))[0] == 400
    assert post(u, "/api/pandit-request", _req(sid, slot="midnight"))[0] == 400
    assert post(u, "/api/pandit-request", _req(sid, topic="lottery"))[0] == 400
    assert post(u, "/api/pandit-request", _req("nope"))[0] == 404
    assert not (d / "pandit_requests.jsonl").exists()


def test_pandit_request_is_saved_and_palms_only_with_consent(srv):
    u, d = srv
    sid = start(u, palms={"left": JPEG, "right": JPEG})["session"]
    code, r = post(u, "/api/pandit-request", _req(sid))                       # details yes, palms not offered
    assert code == 200 and r["ok"] and r["ref"]
    rec = json.loads((d / "pandit_requests.jsonl").read_text().splitlines()[-1])
    assert rec["phone"] == "+919876543210" and rec["name"] == "Sachin Chaturvedi" and rec["birth"]["date"] == "1990-05-15"
    assert rec["palms"] is None and not list(d.glob("pandit_requests/*.jpg"))
    code, r2 = post(u, "/api/pandit-request", _req(sid, share_palms=True))
    assert code == 200
    rec2 = json.loads((d / "pandit_requests.jsonl").read_text().splitlines()[-1])
    assert set(rec2["palms"]) == {"left", "right"} and len(list(d.glob("pandit_requests/*.jpg"))) == 2


def test_palms_are_never_in_feedback_or_chat_payloads(srv):
    u, d = srv
    sid = start(u, palms={"left": JPEG, "right": JPEG})["session"]
    code, a = post(u, "/api/chat", {"session": sid, "question": "career?"})
    assert JPEG not in json.dumps(a)
    post(u, "/api/feedback", {"session": sid, "kind": "answer", "answer_id": a["answer_id"], "rating": "up"})
    fb = d / "feedback.jsonl"
    assert not fb.exists() or JPEG not in fb.read_text()
    assert not (d / "pandit_requests.jsonl").exists()                         # nothing about the user is saved until they ask a pandit


def test_csp_allows_blob_images_only_for_previews(srv):
    u, _ = srv
    with urllib.request.urlopen(u + "/") as r:
        csp = r.headers["Content-Security-Policy"]
    assert "img-src 'self' data: blob:" in csp and "'unsafe-inline'" not in csp
